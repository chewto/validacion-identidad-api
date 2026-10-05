"""Resolucion de la IP del firmante y deteccion de VPN/proxy.

Politica (acordada con el frontend):
  * La IP autoritativa es la del servidor: primer hop de `X-Forwarded-For`
    (si `TRUST_XFF` esta activo), luego `remote_addr`, y solo si ninguno es
    una IP publica se cae a la que declara el cliente en `info.ip`.
  * Si no se puede obtener una IP publica -> LOCATION_UNAVAILABLE (403).
  * Si el proveedor de inteligencia falla (timeout, 5xx, sin API key) se
    devuelve un veredicto `available=False` y **no se bloquea** (fail-open),
    registrando el incidente en el log.
"""
import ipaddress
import os
import threading
import time
from dataclasses import dataclass
from typing import Optional

import requests
from flask import request

import utilities.logs as logs

DEFAULT_PROVIDER = "ipapi.is"
DEFAULT_BLOCK_FLAGS = "is_vpn,is_proxy,is_tor,is_datacenter"

_cache = {}
_cache_lock = threading.Lock()


@dataclass
class IpVerdict:
    ip: str = ""
    available: bool = False
    is_vpn: bool = False
    is_proxy: bool = False
    is_tor: bool = False
    is_datacenter: bool = False
    provider: str = ""
    error: str = ""
    country: str = ""
    geo_lat: Optional[float] = None
    geo_lon: Optional[float] = None


def _log(message):
    try:
        logs.addLog(logs.checkLogsFile(), message)
    except Exception:
        pass


def _env(name, default):
    value = os.getenv(name)
    return value if value not in (None, "") else default


def _timeout():
    try:
        return float(_env("IP_INTEL_TIMEOUT", "3"))
    except (TypeError, ValueError):
        return 3.0


def _cache_ttl(failed=False):
    try:
        ttl = float(_env("IP_INTEL_CACHE_TTL", "300"))
    except (TypeError, ValueError):
        ttl = 300.0
    if failed:
        return min(ttl, 30.0)
    return ttl


def trust_xff() -> bool:
    return _env("TRUST_XFF", "true").strip().lower() not in ("0", "false", "no", "off")


def provider_name() -> str:
    return _env("IP_INTEL_PROVIDER", DEFAULT_PROVIDER).strip().lower()


def api_key() -> str:
    return os.getenv("IP_INTEL_API_KEY", "").strip()


def blocked_flags():
    raw = _env("IP_INTEL_BLOCK_FLAGS", DEFAULT_BLOCK_FLAGS)
    return {flag.strip().lower() for flag in raw.split(",") if flag.strip()}


def _is_public(value) -> bool:
    if not value:
        return False
    try:
        return ipaddress.ip_address(str(value).strip()).is_global
    except ValueError:
        return False


def _candidates(fallback_ip=None):
    """IPs candidatas en orden de autoridad."""
    if trust_xff():
        forwarded = request.headers.get("X-Forwarded-For", "")
        if forwarded:
            yield forwarded.split(",")[0].strip(), "x-forwarded-for"
    try:
        remote = request.remote_addr
    except RuntimeError:
        remote = None
    if remote:
        yield remote, "remote_addr"
    if fallback_ip:
        yield str(fallback_ip).strip(), "payload"


def client_ip(fallback_ip=None) -> Optional[str]:
    """IP publica autoritativa del firmante, o None si no hay ninguna utilizable."""
    descartadas = []
    for candidate, origin in _candidates(fallback_ip):
        if _is_public(candidate):
            return candidate
        descartadas.append(f"{origin}={candidate or ''}")

    _log(
        "ip_intel: no se obtuvo una IP publica utilizable "
        f"(descartadas: {', '.join(descartadas) or 'ninguna'})"
    )
    return None


def _cache_get(ip):
    with _cache_lock:
        entry = _cache.get(ip)
        if not entry:
            return None
        verdict, expires = entry
        if expires < time.time():
            _cache.pop(ip, None)
            return None
        return verdict


def _cache_put(ip, verdict):
    expires = time.time() + _cache_ttl(failed=not verdict.available)
    with _cache_lock:
        _cache[ip] = (verdict, expires)


def clear_cache():
    with _cache_lock:
        _cache.clear()


def _ipapi_is(ip, key) -> IpVerdict:
    response = requests.get(
        "https://api.ipapi.is/",
        params={"q": ip, "key": key},
        timeout=_timeout(),
    )
    if response.status_code != 200:
        return IpVerdict(ip=ip, provider="ipapi.is", error=f"http_{response.status_code}")

    try:
        data = response.json()
    except ValueError:
        return IpVerdict(ip=ip, provider="ipapi.is", error="respuesta_no_json")

    if not isinstance(data, dict) or "is_vpn" not in data:
        return IpVerdict(ip=ip, provider="ipapi.is", error="respuesta_invalida")

    lat, lon = data.get("lat"), data.get("lon")
    return IpVerdict(
        ip=ip,
        available=True,
        provider="ipapi.is",
        is_vpn=bool(data.get("is_vpn")),
        is_proxy=bool(data.get("is_proxy")),
        is_tor=bool(data.get("is_tor")),
        is_datacenter=bool(data.get("is_datacenter")),
        country=str(data.get("country") or ""),
        geo_lat=float(lat) if isinstance(lat, (int, float)) else None,
        geo_lon=float(lon) if isinstance(lon, (int, float)) else None,
    )


_PROVIDERS = {
    "ipapi.is": _ipapi_is,
}


def check_ip(ip) -> IpVerdict:
    """Veredicto anti-VPN para una IP. Nunca lanza: cualquier fallo es fail-open."""
    if not ip:
        return IpVerdict(error="ip_vacia")

    provider = provider_name()
    key = api_key()
    if not key:
        _log("ip_intel: IP_INTEL_API_KEY sin configurar; chequeo anti-VPN en fail-open")
        return IpVerdict(ip=ip, provider=provider, error="sin_api_key")

    cached = _cache_get(ip)
    if cached is not None:
        return cached

    handler = _PROVIDERS.get(provider)
    if handler is None:
        _log(f"ip_intel: proveedor desconocido '{provider}'; anti-VPN en fail-open")
        return IpVerdict(ip=ip, provider=provider, error="proveedor_desconocido")

    try:
        verdict = handler(ip, key)
    except requests.RequestException as e:
        verdict = IpVerdict(ip=ip, provider=provider, error=f"red: {e.__class__.__name__}")
    except Exception as e:
        verdict = IpVerdict(ip=ip, provider=provider, error=str(e))

    _cache_put(ip, verdict)

    if not verdict.available:
        _log(
            f"ip_intel: fallo consultando {provider} para {ip} "
            f"({verdict.error}); anti-VPN en fail-open"
        )
    return verdict


def blocked_kind(verdict: IpVerdict) -> Optional[str]:
    """'proxy' | 'vpn' | None segun `IP_INTEL_BLOCK_FLAGS`.

    El orden es el del plan: primero proxy (mensaje mas especifico para el
    usuario), despues cualquier otra flag activa (vpn/tor/datacenter).
    """
    if not verdict.available:
        return None

    flags = blocked_flags()
    if verdict.is_proxy and "is_proxy" in flags:
        return "proxy"
    if verdict.is_vpn and "is_vpn" in flags:
        return "vpn"
    if verdict.is_tor and "is_tor" in flags:
        return "vpn"
    if verdict.is_datacenter and "is_datacenter" in flags:
        return "vpn"
    return None
