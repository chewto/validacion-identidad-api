# validacion-identidad-api

Microservicio Flask de validacion de identidad (eKYC). Se conecta a una base
MariaDB `pki_validacion` en `identidad.efirmaplus.com` a traves de dos endpoints
separados por pais, ambos con **mTLS**.

| Origen    | Puerto | Variable      | Usuario             |
|-----------|--------|---------------|---------------------|
| COLOMBIA  | 3300   | `DB_COL_URI`  | `administrador_ssl` |
| HONDURAS  | 3310   | `DB_HON_URI`  | `administrador`     |

## Conexion TLS / mTLS

El formato de la variable de entorno es:

```
mysql://<user>:<pass>@<host>:<port>/<database>
  ?ssl=true
  &ssl_ca=/ssl/ca.pem
  &ssl_cert=/ssl/client-cert.pem
  &ssl_key=/ssl/client-key.pem
  &ssl_verify_cert=true
  &tls_version=TLSv1.2,TLSv1.3
```

`ssl=true` **no es opcional**. Sin el, el driver no exige TLS y negocia en
claro en silencio cuando algo falla. Si la password contiene `@ / ? #` hay que
percent-encodearla (`%40` `%2F` `%3F` `%23`); un `.env` mal escrito no tumba el
arranque, se reporta como error en tiempo de request.

### Montaje de los certificados

Los tres PEM viven en un directorio del host y se montan de **solo lectura**
dentro del contenedor. Nunca se copian al build context ni al `Dockerfile`:

```yaml
services:
  api:
    build: .
    ports:
      - "4000:4000"
    environment:
      DB_COL_URI: "mysql://...?ssl=true&ssl_ca=/ssl/ca.pem&..."
      DB_HON_URI: "mysql://...?ssl=true&ssl_ca=/ssl/ca.pem&..."
    volumes:
      - /ruta/real/del/host/ssl:/ssl:ro   # <- CA + certificado y clave de cliente
      - /ruta/real/del/host/logs:/Logs/ekyc
```

Dentro del contenedor se validan antes de abrir el socket: si un PEM falta, la
ruta es relativa, o el proceso no puede leerlo, la conexion falla con
`DbConnectionError` en espanol diciendo que archivo falta. **Nunca** degrada a
texto plano.

## Limitacion conocida: NO se verifica el hostname del servidor

`mariadb==1.1.12` (MariaDB Connector/Python sobre Connector/C 3.4.4) **no puede
validar el SAN/hostname** del certificado del servidor. No existe el flag
`ssl_verify_identity` en este driver. Lo unico que hace `ssl_verify_cert=true` es
verificar que la cadena de confianza sea valida contra `ssl_ca`.

Consecuencia: el cifrado esta garantizado y la CA esta verificada, pero **no se
puede probar que el servidor sea realmente `identidad.efirmaplus.com`**. Quien
herede este codigo debe saber que esa garantia falta.

Mitigaciones, en orden de preferencia:

1. **Firewall abierto solo por IP de origen del servidor**, nunca por rango.
   Es la unica que compensa de verdad el problema.
2. **`tls_version=TLSv1.2,TLSv1.3` pineado** en la URI, para que no se negocie
   una version vieja.
3. Este README, para que la limitacion no se pierda.

No hay parche casero de verificacion de hostname sobre el driver en C. Si
alguna vez hace falta esa garantia, la via es un proxy TLS (HAProxy, stunnel) o
migrar el driver.

## Diagnostico

`GET /db-status?country=COL` es el unico endpoint que expone el error real de
conexion; las demas rutas devuelven `()` / `{}` ante fallo, por diseno.

Dentro del contenedor:

```bash
ls -l /ssl/                          # los tres PEM, legibles por el usuario del proceso
openssl x509 -in /ssl/ca.pem -noout -subject -issuer -dates
openssl rsa  -in /ssl/client-key.pem -noout -check
openssl s_client -connect identidad.efirmaplus.com:3300 -starttls mysql -showcerts 2>/dev/null \
  | openssl x509 -noout -text | grep -A1 "Subject Alternative Name"
```

En el servidor MariaDB, `SHOW STATUS LIKE 'Ssl_%'` debe traer `ssl_cipher` no
vacio, y `ssl_type` debe incluir `CERTIFICATE` si el usuario exige `REQUIRE X509`
(mTLSAssertion).

## Respuesta de `/ocr/anverso` y `/ocr/reverso`

Ademas de `messages`, ambas rutas devuelven los datos que no coinciden con el
documento para que el frontend pueda mostrar un mensaje por campo:

```json
{
  "mismatches": [
    {
      "field": "name",
      "label": "nombre",
      "source": "ocr",
      "message": "Su nombre no coincide con los datos legibles del documento.",
      "percentage": 35,
      "threshold": 50
    }
  ],
  "hasMismatch": true
}
```

- `field`: `name`, `lastName` o `ID`.
- `source`: `ocr` o `mrz`.
- `threshold`: 50 para OCR y 51 para MRZ.
- `hasMismatch`: `true` si `mismatches` tiene al menos un dato discrepante.

`mismatches` siempre viene en la respuesta (`[]` si no hay discrepancias). Los
fallos de lectura se informan en `messages` como "No se pudo leer ..." y no se
cuentan como mismatch. En el reverso, la comparacion por MRZ solo se hace si el
tipo de documento tiene MRZ en ese lado y el MRZ extraido alcanza
`valid_score >= 51`; si el MRZ es opcional, el aviso se muestra igual pero
`validSide` conserva la regla actual. El frontend debe mostrar `mismatches` (o
`messages`) aunque `validSide` sea `true`.

## Pruebas

```bash
pytest tests/test_db_tls.py     # contrato de la conexion TLS
```

`tests/` esta en `.gitignore`, asi que la suite no viaja en el repo ni corre en
CI. Si tocás la conexion, corré estos tests antes de desplegar.

## Desarrollo

```bash
python main.py                  # desarrollo, puerto 4000
gunicorn -c gunicorn_config.py main:app
```

Timeouts de conexion configurables por variable de entorno, para no colgarse si
el firewall dropea el SYN en los puertos no estandar:

| Variable             | Default |
|----------------------|---------|
| `DB_CONNECT_TIMEOUT` | `10`    |
| `DB_READ_TIMEOUT`    | `30`    |
| `DB_WRITE_TIMEOUT`   | `30`    |

## Prueba de vida (`/anti-spoof`): frames configurables

`POST /anti-spoof` extrae frames del video con `getFrames()` (`reconocimiento.py`),
que toma **1 frame cada `interval_ms` milisegundos** (no usa un contador de frames).
En máquinas con poca CPU/RAM, leer y analizar menos frames reduce mucho el costo
(`faceDetection`, anti-spoofing con DeepFace y detección de documento).

| Variable                       | Default | Descripción |
|--------------------------------|---------|-------------|
| `ANTI_SPOOF_FRAME_INTERVAL_MS` | `333`   | Milisegundos entre frames muestreados (~3 fps). Mayor = menos frames leídos. Mínimo efectivo: `50`. |

Ejemplo para un servidor limitado (≈ 1 fps):

```bash
ANTI_SPOOF_FRAME_INTERVAL_MS=1000 python main.py
```

Notas:

- La variable se lee **al arrancar el proceso**; requiere reinicio para aplicarse.
- Valores vacíos, no numéricos o `<= 0` caen al default (`333`) con una advertencia;
  valores por debajo de `50` se elevan a `50`.
- La respuesta incluye `frameIntervalMs` y `framesCount` (frames realmente
  procesados) para verificar la configuración.
- Intervalos muy altos degradan la prueba de vida: con pocos frames
  `movementDetection` puede fallar ("No se pudo validar el movimiento facial").
  Rango recomendado: `333`–`2000`.
- Si el intervalo es tan alto (o el video tan corto) que no se extrae ningún frame,
  el endpoint responde `400 {"error": "No se pudieron extraer frames del video."}`.

## Progreso en tiempo real (WebSocket)

`utilities/ws_server.py` levanta un servidor WebSocket en un hilo daemon del
mismo proceso Flask y `notify_progress(...)` (usado por `blueprints/ocr_bp.py`)
publica los pasos del procesamiento:

- URL: `ws://<host>:4001/<efirma_id>` (o `ws://<host>:4001/ws/<efirma_id>`).
- Suscripción por mensaje: `{"action": "subscribe", "id": "<efirma_id>"}`;
  también `unsubscribe`/`leave` y `ping`.
- Payload emitido (sin cambios respecto al cliente actual):
  `{"efirma_id", "step", "message", "status", "timestamp", "extra"}`.

Variables de entorno:

| Variable           | Default   | Descripción |
|--------------------|-----------|-------------|
| `WS_ENABLED`       | `auto`    | `1`/`0` fuerza/niega. `auto` arranca salvo bajo gunicorn (ver abajo). |
| `WS_HOST`          | `0.0.0.0` | Interfaz de escucha. |
| `WS_PORT`          | `4001`    | Puerto del contrato con el frontend. |
| `WS_PORT_FALLBACK` | `0`       | Puertos extra a probar si el pedido está ocupado. Si se usa, **cambia la URL** y el frontend debe apuntar al puerto nuevo. |
| `WS_START_TIMEOUT` | `5`       | Segundos de espera al bind cuando se arranca con `wait=True`. |

### Un solo proceso, no varios

El estado de suscripciones vive en memoria del proceso: si corren varios
workers (por ejemplo `workers = 3` en `gunicorn_config.py`), el progreso emitido
en un worker no llega al cliente suscrito en otro. Por eso `WS_ENABLED=auto`
**desactiva** el WS bajo gunicorn; el frontend debe usar el progreso persistido:

- `POST /validation/progress?idUsuario=<id>` guarda el paso (`validation_bp.py`).
- `GET /validation/progress?idUsuario=<id>` lo devuelve.

Con un único proceso (`python main.py`, o gunicorn con `workers = 1` y
`WS_ENABLED=1`) el WS funciona completo.

### Diagnóstico

`GET /ws-status` devuelve `{enabled, running, host, port, rooms, subscribers}`.
Si el puerto 4001 ya está tomado por otro proceso, el arranque registra **un**
error indicando el PID/proceso dueño (vía `psutil`) y la app sigue funcionando
sin WS. Para liberarlo en Windows:

```powershell
Get-NetTCPConnection -LocalPort 4001 -State Listen | Select-Object OwningProcess
Stop-Process -Id <PID>
```

El arranque es idempotente: `start_ws_server()` puede llamarse varias veces sin
abrir un segundo puerto.

