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

## Validacion de ubicacion y politica anti-VPN

`GET /validation/document-config?hash=<standalone>|efirmaId=<embebido>&country=<XX>`
(autenticado con el JWT de sesion) devuelve a la SPA dos flags por documento:

- `require_location_validation`: el body de firma debe traer `location`
  (`{latitude, longitude, accuracy}` en WGS84 y metros) y el punto debe quedar
  dentro del radio y del centro configurados.
- `block_on_vpn`: se resuelve la IP publica del firmante y se consulta el
  proveedor de inteligencia. **Si el proveedor falla no se bloquea**
  (fail-open) y el incidente queda en el log.

La configuracion son **cinco columnas de `usuarios.entidades`**, una fila por
entidad, junto al resto de parametros de validacion que ya viven ahi
(`validacion_vida`, `porcentaje_acierto`, `intentos_documentos`,
`intentos_deteccion`, `intentos_rostro`). No hay tabla nueva: el documento se
resuelve a su entidad con los mismos joins que usa `/validation-params`.

| Columna | Tipo | Default | Que hace |
|---------|------|---------|----------|
| `validar_ubicacion` | `TINYINT(1)` | `0` | Exige `location` en la firma. |
| `bloquear_vpn` | `TINYINT(1)` | `0` | Bloquea VPN / proxy / Tor / datacenter. |
| `radio_ubicacion_m` | `INT` NULL | `NULL` | Radio en metros. `NULL` = `LOCATION_DEFAULT_RADIUS_METERS`. |
| `ubicacion_lat` | `DECIMAL(10,7)` NULL | `NULL` | Centro permitido (WGS84). |
| `ubicacion_lng` | `DECIMAL(10,7)` NULL | `NULL` | Centro permitido (WGS84). |

`usuarios.entidades` es del schema `usuarios`, compartido con los apps de firma
y portal, asi que el alta la hace el DBA de ese schema **por pais** (COL y
HND). Con los defaults `0/NULL` ninguna entidad cambia de comportamiento: si
las columnas no estan, la consulta falla y el guard queda en fail-open
(`false/false`) con aviso en el log.

Para activarlo en una entidad:

```sql
UPDATE usuarios.entidades
SET validar_ubicacion = 1, radio_ubicacion_m = 500,
    ubicacion_lat = 4.7110000, ubicacion_lng = -74.0721000
WHERE entity_id = 7;
```

Con `validar_ubicacion = 1` y las coordenadas en `NULL` el chequeo queda solo
por precision (`accuracy <= radio`), sin exigir un centro.

| Variable | Default | Descripcion |
|----------|---------|-------------|
| `IP_INTEL_PROVIDER` | `ipapi.is` | Proveedor de inteligencia de IP (hoy solo `ipapi.is`). |
| `IP_INTEL_API_KEY` | — | **Obligatoria** para que `block_on_vpn` bloquee de verdad. Sin ella el chequeo queda en fail-open silencioso (solo log). |
| `IP_INTEL_TIMEOUT` | `3` | Timeout HTTP al proveedor, en segundos. |
| `IP_INTEL_CACHE_TTL` | `300` | TTL de la cache de veredictos (por worker de gunicorn). Los fallos se cachean 30 s como maximo. |
| `IP_INTEL_BLOCK_FLAGS` | `is_vpn,is_proxy,is_tor,is_datacenter` | Flags que disparan el rechazo. `is_proxy` responde `PROXY_DETECTED`; el resto responden `VPN_DETECTED`. |
| `LOCATION_DEFAULT_RADIUS_METERS` | `500` | Radio efectivo cuando la entidad no define `radio_ubicacion_m`. |
| `TRUST_XFF` | `true` | Con `true`, la IP autoritativa es el primer hop de `X-Forwarded-For`; si no, `remote_addr`. `info.ip` del body es solo el ultimo respaldo. |

Los errores nuevos usan siempre el shape `{"error": {"code", "message"}}`:

| `code` | HTTP |
|--------|------|
| `LOCATION_REQUIRED` | 400 |
| `LOCATION_MISMATCH` | 403 |
| `LOCATION_UNAVAILABLE` | 403 |
| `VPN_DETECTED` | 403 |
| `PROXY_DETECTED` | 403 |

El veredicto de cada firma queda como clave `location_security` dentro de
`checks_json` de `evidencias_adicionales` (con `entity_id` y `result`), ademas
de en el log.

### Pruebas de esta feature

```bash
python -m unittest discover -s tests -v
python -m compileall blueprints utilities
```
