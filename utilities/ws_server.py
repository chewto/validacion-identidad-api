import asyncio
import atexit
import errno
import json
import logging
import os
import sys
import threading
import time
from typing import Any, Dict, Optional, Set, Tuple

from websockets.asyncio.server import serve, Server

logger = logging.getLogger(__name__)

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 4001
SEND_TIMEOUT = 2.0
MAX_MESSAGE_SIZE = 4 * 1024 * 1024

_ADDR_IN_USE = {errno.EADDRINUSE, getattr(errno, "WSAEADDRINUSE", 10048), 10048}

_TRUTHY = {"1", "true", "yes", "on"}
_FALSY = {"0", "false", "no", "off"}

# Diccionario de suscriptores: { target_id: set(websocket) }
_subscribers: Dict[str, Set[Any]] = {}
_subscribers_lock = threading.Lock()

# Estado del servidor. `_state_lock` protege las variables del ciclo de vida,
# `_start_lock` serializa los intentos de arranque/parada.
_state_lock = threading.Lock()
_start_lock = threading.Lock()

_loop: Optional[asyncio.AbstractEventLoop] = None
_server: Optional[Server] = None
_thread: Optional[threading.Thread] = None
_address: Optional[Tuple[str, int]] = None
_ready = threading.Event()
_start_error: Optional[BaseException] = None
_atexit_registered = False
_disabled_logged = False
_console_logging_ready = False


def _ensure_console_logging() -> None:
    """La app no configura `logging`, y el handler de último recurso sólo
    muestra WARNING+. Sin esto, el arranque/deshabilitado del WS no se vería
    en consola."""
    global _console_logging_ready
    if _console_logging_ready:
        return
    _console_logging_ready = True

    if logger.handlers or logging.getLogger().handlers:
        return

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


# ─── Configuración ────────────────────────────────────────────────────────────

def _running_under_gunicorn() -> bool:
    """Detecta si el proceso actual es un worker de gunicorn.

    `SERVER_SOFTWARE` cubre las invocaciones normales y `sys.modules` cubre
    cualquier otra forma de arranque en la que gunicorn ya esté importado.
    """
    if os.environ.get("SERVER_SOFTWARE", "").lower().startswith("gunicorn"):
        return True
    return "gunicorn" in sys.modules


def is_ws_enabled() -> bool:
    """Resuelve `WS_ENABLED`: `1`/`0` explícitos; `auto` (default) desactiva
    el WS in-process bajo gunicorn, donde varios workers no compartirían el
    estado de suscripciones y el puerto sólo puede tomarlo uno."""
    raw = os.environ.get("WS_ENABLED")
    value = (raw or "auto").strip().lower()

    if value in _FALSY:
        return False
    if value in _TRUTHY:
        return True

    return not _running_under_gunicorn()


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        logger.warning("[WebSocket] %s=%r no es un entero; se usa %s.", name, raw, default)
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        return float(str(raw).strip())
    except (TypeError, ValueError):
        logger.warning("[WebSocket] %s=%r no es un número; se usa %s.", name, raw, default)
        return default


def _errno_of(exc: BaseException) -> Optional[int]:
    errno_value = getattr(exc, "errno", None)
    if isinstance(errno_value, int):
        return errno_value
    winerror = getattr(exc, "winerror", None)
    if isinstance(winerror, int):
        return winerror
    return None


def _describe_port_owner(port: int) -> str:
    """Describe el proceso que ya está escuchando en `port`, si psutil puede."""
    try:
        import psutil
    except Exception:
        return "no se pudo identificar el proceso (psutil no disponible)"

    try:
        for conn in psutil.net_connections(kind="inet"):
            laddr = getattr(conn, "laddr", None)
            if not laddr or getattr(laddr, "port", None) != port:
                continue
            if conn.status != psutil.CONN_LISTEN:
                continue
            pid = conn.pid
            if not pid:
                continue
            try:
                return f"PID {pid} ({psutil.Process(pid).name()})"
            except Exception:
                return f"PID {pid}"
    except Exception as exc:
        return f"no se pudo identificar el proceso ({exc})"

    return "proceso desconocido"


def _log_start_failure(host: str, port: int, exc: BaseException) -> None:
    if _errno_of(exc) in _ADDR_IN_USE:
        logger.error(
            "[WebSocket] No se pudo escuchar en ws://%s:%s: el puerto ya está en uso (%s). "
            "Se desactiva el progreso en tiempo real; el frontend puede seguir usando GET /progress. "
            "Cierra el proceso que ocupa el puerto o define WS_PORT / WS_PORT_FALLBACK.",
            host, port, _describe_port_owner(port),
        )
    else:
        logger.error(
            "[WebSocket] El servidor no pudo iniciarse en ws://%s:%s: %s",
            host, port, exc,
        )


# ─── Conexiones y suscripciones ───────────────────────────────────────────────

def _parse_room(websocket) -> Optional[str]:
    """Extrae el id de sala de la URL (`/ws/<id>`, `/<id>`), ignorando el query."""
    try:
        request = getattr(websocket, "request", None)
        path = request.path if request is not None else "/"
    except Exception:
        return None

    cleaned = (path or "/").split("?", 1)[0].strip("/")
    parts = [part for part in cleaned.split("/") if part]

    if not parts or parts[-1] == "ws":
        return None

    return parts[-1]


async def _handle_connection(websocket):
    """Maneja la conexión de un cliente WebSocket."""
    initial_id = _parse_room(websocket)
    current_ids: Set[str] = set()

    def add_subscription(sub_id: str):
        sub_id = str(sub_id).strip()
        if not sub_id:
            return
        with _subscribers_lock:
            _subscribers.setdefault(sub_id, set()).add(websocket)
        current_ids.add(sub_id)

    def remove_subscription(sub_id: str):
        with _subscribers_lock:
            sockets = _subscribers.get(sub_id)
            if sockets is not None:
                sockets.discard(websocket)
                if not sockets:
                    del _subscribers[sub_id]
        current_ids.discard(sub_id)

    logger.debug("[WebSocket] Cliente conectado (sala inicial: %s).", initial_id)

    if initial_id:
        add_subscription(initial_id)
        try:
            await websocket.send(json.dumps({
                "type": "subscribed",
                "id": initial_id,
                "message": f"Conectado a sala {initial_id}"
            }))
        except Exception:
            pass

    try:
        async for raw_message in websocket:
            try:
                data = json.loads(raw_message)
                action = data.get("action") or data.get("type")
                target_id = data.get("id") or data.get("efirma_id")

                if action in ("subscribe", "join") and target_id:
                    add_subscription(str(target_id))
                    await websocket.send(json.dumps({
                        "type": "subscribed",
                        "id": str(target_id),
                        "message": f"Suscrito a sala {target_id}"
                    }))
                elif action in ("unsubscribe", "leave") and target_id:
                    remove_subscription(str(target_id))
                    await websocket.send(json.dumps({
                        "type": "unsubscribed",
                        "id": str(target_id)
                    }))
                elif action == "ping":
                    await websocket.send(json.dumps({"type": "pong"}))
            except json.JSONDecodeError:
                pass
    except Exception as e:
        logger.debug("[WebSocket] Cliente desconectado: %s", e)
    finally:
        for sid in list(current_ids):
            remove_subscription(sid)


def _purge_sockets(sockets) -> None:
    with _subscribers_lock:
        for socket in sockets:
            for sid in list(_subscribers.keys()):
                room = _subscribers.get(sid)
                if room is None:
                    continue
                room.discard(socket)
                if not room:
                    del _subscribers[sid]


async def _send_to_sockets(sockets: list, payload_str: str):
    """Envía el payload a los websockets indicados, con timeout por socket
    para que un cliente lento no bloquee al resto."""
    dead = []
    for ws in sockets:
        try:
            await asyncio.wait_for(ws.send(payload_str), timeout=SEND_TIMEOUT)
        except Exception:
            dead.append(ws)
    if dead:
        _purge_sockets(dead)


def notify_progress(
    efirma_id: Any,
    step: str,
    message: str,
    status: str = "processing",
    extra: Optional[Dict[str, Any]] = None
):
    """
    Emite un mensaje de progreso en tiempo real al cliente suscrito al efirma_id.
    Es thread-safe y no bloquea ni rompe la ejecución de Flask: si el servidor
    WS no está disponible, el mensaje simplemente se descarta.
    """
    if not efirma_id:
        return

    sid = str(efirma_id).strip()
    if not sid:
        return

    with _subscribers_lock:
        sockets = list(_subscribers.get(sid, ()))

    if not sockets:
        return

    with _state_lock:
        loop = _loop

    if loop is None or loop.is_closed() or not loop.is_running():
        return

    payload = {
        "efirma_id": sid,
        "step": step,
        "message": message,
        "status": status,
        "timestamp": time.time(),
        "extra": extra or {}
    }

    try:
        payload_str = json.dumps(payload, default=str)
        future = asyncio.run_coroutine_threadsafe(
            _send_to_sockets(sockets, payload_str),
            loop
        )
    except (RuntimeError, asyncio.InvalidStateError) as exc:
        # El loop se cerró entre el chequeo y el envío (shutdown/reloader).
        logger.debug("[WebSocket] No se pudo programar el envío de '%s': %s", step, exc)
        return

    future.add_done_callback(_log_send_result)


def _log_send_result(future) -> None:
    try:
        future.result()
    except Exception as exc:
        logger.debug("[WebSocket] Error enviando progreso: %s", exc)


# ─── Ciclo de vida del servidor ───────────────────────────────────────────────

async def _serve_with_fallback(host: str, port: int, fallback: int) -> Tuple[Server, int]:
    last_error: Optional[BaseException] = None

    for offset in range(0, fallback + 1):
        candidate = port + offset
        try:
            server = await serve(
                _handle_connection,
                host,
                candidate,
                ping_interval=20,
                ping_timeout=20,
                close_timeout=5,
                max_size=MAX_MESSAGE_SIZE,
            )
        except OSError as exc:
            if _errno_of(exc) not in _ADDR_IN_USE or offset >= fallback:
                raise
            last_error = exc
            logger.warning("[WebSocket] Puerto %s ocupado; probando %s.", candidate, candidate + 1)
            continue

        if offset:
            logger.warning(
                "[WebSocket] Se usa el puerto %s en lugar de %s (WS_PORT_FALLBACK=%s); "
                "la URL del frontend debe coincidir.",
                candidate, port, fallback,
            )

        return server, candidate

    raise last_error if last_error is not None else OSError("No se pudo abrir el socket WebSocket")


def _run_server_loop(host: str, port: int, fallback: int) -> None:
    global _loop, _server, _address, _start_error

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    with _state_lock:
        _loop = loop

    try:
        server, bound_port = loop.run_until_complete(_serve_with_fallback(host, port, fallback))

        with _state_lock:
            _server = server
            _address = (host, bound_port)

        logger.info("[WebSocket] Servidor activo escuchando en ws://%s:%s", host, bound_port)
        _ready.set()

        loop.run_until_complete(server.wait_closed())
    except BaseException as exc:  # noqa: BLE001 - el hilo no debe tumbar el proceso
        with _state_lock:
            _server = None
            _address = None
            _start_error = exc
        _log_start_failure(host, port, exc)
        _ready.set()
    finally:
        with _state_lock:
            _server = None
            _address = None
            if _loop is loop:
                _loop = None

        if not loop.is_closed():
            try:
                loop.run_until_complete(loop.shutdown_asyncgens())
            except Exception:
                pass
            loop.close()


def _register_atexit() -> None:
    global _atexit_registered
    if _atexit_registered:
        return
    _atexit_registered = True
    atexit.register(stop_ws_server)


def start_ws_server(
    host: Optional[str] = None,
    port: Optional[int] = None,
    wait: bool = False
) -> Optional[Tuple[str, int]]:
    """Inicia el servidor de WebSockets en un hilo secundario daemon.

    Idempotente: si ya está corriendo devuelve la dirección bindeada. Con
    `wait=True` espera (acotado por `WS_START_TIMEOUT`) a que el bind termine
    y devuelve `None` si no fue posible. Nunca lanza por un fallo de bind.
    """
    global _thread, _start_error, _disabled_logged

    _ensure_console_logging()

    if not is_ws_enabled():
        if not _disabled_logged:
            _disabled_logged = True
            logger.info(
                "[WebSocket] Servidor deshabilitado (WS_ENABLED=0, o WS_ENABLED=auto con gunicorn). "
                "El progreso sigue disponible por GET /progress."
            )
        return None

    ws_host = (host or os.environ.get("WS_HOST") or DEFAULT_HOST).strip() or DEFAULT_HOST
    ws_port = int(port) if port is not None else _env_int("WS_PORT", DEFAULT_PORT)
    fallback = max(0, _env_int("WS_PORT_FALLBACK", 0))
    start_timeout = max(0.0, _env_float("WS_START_TIMEOUT", 5.0))

    with _start_lock:
        if _thread is not None and _thread.is_alive():
            with _state_lock:
                address = _address
            if address is not None:
                if port is not None and address[1] != ws_port:
                    logger.warning(
                        "[WebSocket] El servidor ya escucha en ws://%s:%s; se ignora el puerto %s.",
                        address[0], address[1], ws_port,
                    )
                return address
        else:
            _ready.clear()
            _start_error = None
            thread = threading.Thread(
                target=_run_server_loop,
                args=(ws_host, ws_port, fallback),
                daemon=True,
                name="WebSocketServerThread",
            )
            _thread = thread
            _register_atexit()
            thread.start()

    if wait:
        if not _ready.wait(start_timeout):
            logger.warning(
                "[WebSocket] El servidor no confirmó el bind en %.1fs (ws://%s:%s).",
                start_timeout, ws_host, ws_port,
            )
        elif _start_error is not None:
            return None

    return get_ws_address()


def stop_ws_server(timeout: float = 5.0) -> None:
    """Detiene el servidor WS y libera el puerto. Idempotente."""
    global _thread, _server, _address

    with _start_lock:
        thread = _thread
        server = _server
        loop = _loop
        _thread = None
        _server = None
        _address = None

    if thread is None:
        return

    if server is not None and loop is not None and loop.is_running():
        try:
            loop.call_soon_threadsafe(server.close)
        except Exception as exc:
            logger.debug("[WebSocket] No se pudo solicitar el cierre del servidor: %s", exc)

    if thread.is_alive():
        thread.join(timeout=timeout)

    if thread.is_alive():
        logger.debug("[WebSocket] El hilo del servidor no terminó en %.1fs; se fuerza la parada.", timeout)
        if loop is not None and not loop.is_closed():
            try:
                loop.call_soon_threadsafe(loop.stop)
            except Exception:
                pass
        thread.join(timeout=1.0)


def get_ws_address() -> Optional[Tuple[str, int]]:
    """Devuelve `(host, puerto)` bindeados o `None` si no está corriendo."""
    with _state_lock:
        return _address


def is_ws_running() -> bool:
    with _state_lock:
        server = _server
        address = _address
        loop = _loop
    return bool(
        server is not None
        and address is not None
        and loop is not None
        and not loop.is_closed()
        and loop.is_running()
    )


def stats() -> Dict[str, Any]:
    """Estado agregado para diagnóstico HTTP (sin datos de usuarios)."""
    with _subscribers_lock:
        rooms = len(_subscribers)
        sockets = sum(len(subscribers) for subscribers in _subscribers.values())

    address = get_ws_address()

    return {
        "enabled": is_ws_enabled(),
        "running": is_ws_running(),
        "host": address[0] if address else None,
        "port": address[1] if address else None,
        "rooms": rooms,
        "subscribers": sockets,
    }
