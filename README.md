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
