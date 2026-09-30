# Prompt de trabajo: conectar correctamente a MariaDB con SSL (mTLS)

> Copiar todo el bloque "## PROMPT" hacia abajo en el agente que trabaja sobre
> `validacion-identidad-api`. Los apartados anteriores son contexto para una
> persona y pueden eliminarse.

---

## PROMPT

### Contexto

Tenemos dos microservicios que se conectan a la **misma** base de datos MariaDB
`pki_validacion` en `identidad.efirmaplus.com`, con dos endpoints distintos:

| Origen | Puerto | Variable | Usuario |
|---|---|---|---|
| COLOMBIA | 3300 | `DB_COL_URI` | `administrador_ssl` |
| HONDURAS / HONDUCERT | 3310 | `DB_HON_URI` | `administrador` |

Ambos usan **mTLS** (CA + certificado de cliente + clave de cliente). El
certificado del servidor está emitido con el **SAN correcto**
(`identidad.efirmaplus.com`). Los tres archivos PEM ya existen en el servidor de
destino, en un directorio del host, y hay que **montarlos** dentro del contenedor
(NO copiarlos al build context).

El formato de conexión acordado es una URI:

```
mysql://<user>:<pass>@<host>:<port>/<database>
  ?ssl=true
  &ssl_ca=/ssl/ca.pem
  &ssl_cert=/ssl/client-cert.pem
  &ssl_key=/ssl/client-key.pem
  &ssl_verify_cert=true
  &tls_version=TLSv1.2,TLSv1.3
```

### El proyecto que funciona (referencia)

`app-python-unico` ya se conecta con éxito. Usa **PyMySQL 1.1.1** y su lógica de
TLS vive en `parse_db_uri()` (`main.py:29-56`) y `pymysql.connect(**conn_params)`
(`main.py:99-111`). **No copies su implementación tal cual** — ver abajo por qué.

### El proyecto que falla (este)

`validacion-identidad-api` usa el **MariaDB Connector/Python 1.1.12**
(Connector/C **3.4.4**), driver nativo en C, declarado como `mariadb==1.1.12` en
`requirements.txt:61`. Su lógica está en `request/controlador_db.py`.

### Causa raíz: los drivers no son intercambiables

Ambas apps parsean la **misma** variable `DB_*_URI`, pero los dos drivers
exponen conjuntos de parámetros distintos para el mismo concepto de TLS:

| Parámetro | PyMySQL 1.1.1 (funciona) | MariaDB Connector 1.1.12 (falla) |
|---|---|---|
| `ssl_ca` | hay que mapearlo a la clave `ca` de un dict | `ssl_ca` directo |
| `ssl_cert` / `ssl_key` | claves `cert` / `key` del dict | `ssl_cert` / `ssl_key` directos |
| `ssl` (forzar TLS) | la presencia del dict activa `CLIENT.SSL` | **`ssl=True` ⇒ "The connection must use TLS security or it will fail"** |
| `ssl_verify_cert` | **no existe**; el proyecto lo usa como alias de `check_hostname` | parámetro real: "Enables server certificate verification" |
| **verificación de hostname** | sí, vía `check_hostname` + `wrap_socket(server_hostname=...)` | **NO EXISTE en 1.1.12** (verificado: la cadena `ssl_verify_identity` no aparece en `_mariadb.cp311-win_amd64.pyd`) |
| timeouts | `connect_timeout` | `connect_timeout`, `read_timeout`, `write_timeout` |
| `tls_version` | no soportado | string CSV: `"TLSv1.2,TLSv1.3"` (módulo `mariadb`, añadido en 1.1.7) |

Dos consecuencias que debes internalizar:

1. `ssl_verify_cert=true` **significa cosas distintas** en cada driver. En PyMySQL
   terminaba activando la verificación de hostname. En el Connector solo
   verifica la cadena del certificado. **Nadie puede pedir verificación de
   identidad en este driver.** Como el server sí tiene el SAN correcto, esa
   garantía no está disponible aquí y hay que compensarla por otros medios
   (ver "Compensaciones", más abajo).
2. Semántica del silencio: PyMySQL, si no le pasas nada de SSL, **degrada a
   texto plano sin avisar**. El Connector, si pasas `ssl=True`, **falla**. El
   proyecto que funciona es justamente el peligroso; el que falla es el que
   tiene el comportamiento correcto. **No "arregles" este proyecto copia el
   patrón del otro.**

Parámetros TLS reales aceptados por `mariadb.connect()` en 1.1.12: `ssl`,
`ssl_ca`, `ssl_capath`, `ssl_cert`, `ssl_key`, `ssl_crlpath`, `ssl_cipher`,
`ssl_verify_cert`, `tls_version`, `connect_timeout`, `read_timeout`,
`write_timeout`. Los `Connection.tls_cipher` y `Connection.tls_version`
(`mariadb/connections.py:590` y `:599`) permiten verificar **después** de
conectar qué se negoció realmente.

### Fuente de verdad que ya existe en el repo

`tests/test_db_tls.py` (294 líneas) es la **especificación completa** de la
solución, escrita pero **nunca implementada**. Hoy la suite falla en el import
porque `request/controlador_db.py` no exporta `_validar_tls`, `_as_bool` ni
`DbConnectionError`. Lo que esa spec exige, textual:

- `_parse_db_uri()` devuelve un `dict` con las claves exactas que acepta
  `mariadb.connect()`, incluyendo `ssl: True` cuando hay parámetros TLS.
- `_parse_db_uri()` **nunca lanza**. Ante una URI mal formada devuelve el dict con
  una clave `_parse_error` descriptiva, y el import del módulo sigue funcionando.
  Invariante explícita en `test_db_tls.py:88-94`: *"un `.env` mal escrito no puede
  tumbar el arranque de gunicorn (eso se manifestaba como HTTP 502 sin log
  legible)"*.
- El password se percent-decodifica (`test_db_tls.py:111-122`) y se **detecta y
  reporta** cuando trae un `@ / ? #` sin codificar, en vez de truncar en
  silencio.
- Los paths de certificado se **preservan tal cual** en el parseo (el parseo es
  puro, sin I/O) y la existencia en disco se valida ** aparte**, en `_validar_tls()`.
- `_validar_tls(config, origen)` exige **ruta absoluta** y **archivo existente**,
  y lanza `DbConnectionError` si falta. Emite **un solo warning** si
  `ssl_verify_cert` está apagado, usando un set `_TLS_WARNED`, y ese warning
  nunca debe romper la escritura de logs.
- `DbConnectionError` **hereda de `mariadb.Error`**, para que los `except
  mariadb.Error` que ya hay en las ~20 funciones de `controlador_db.py`
  sigan capturándola.
- `get_db()` propaga `DbConnectionError` con un mensaje que incluya origen, host,
  puerto, base, si TLS está activo y la causa raíz.
- Un fallo de conexión sigue devolviendo `()` / `{}` en `selectData`, `getUser`,
  etc. (no cambiar ese comportamiento público).
- El import del módulo **no escribe nada en disco**.
- Se ignoran parámetros desconocidos (ej. `charset`).

**Usa ese archivo como contrato. Antes de escribir código, ejecuta la suite para
ver exactamente qué falla; después, haz que pase. No reescribas los tests para
hacerlos pasar.**

### Los 5 defectos a corregir

1. **`request/controlador_db.py:13-32` — falta `ssl`.** `_parse_db_uri()` nunca
   setea `ssl`. Sin `ssl=True` el TLS no es obligatorio: si algo falla, el
   connector negocia sin TLS en lugar de fallar.
2. **`Dockerfile` — `/ssl` no existe.** No hay `RUN mkdir /ssl`, ni `VOLUME`, ni
   montaje. Los `.pem` que apunta la URI no están dentro del contenedor. La URI
   apunta a rutas absolutas de contenedor, luego hace falta un **bind mount de
   solo lectura** desde el host, definido en el `docker-compose.yml` que hoy
   **no existe en el repo** (sí lo invoca `.github/workflows/deploy.yaml:28,65`
   con `docker compose up -d --build`).
3. **`request/controlador_db.py:62` — sin timeouts.** `mariadb.connect(**config)`
   sin `connect_timeout` ni `read_timeout`. Los puertos 3300/3310 no son estándar:
   si el firewall los dropea en silencio, la petición **se cuelga indefinidamente**
   en vez de devolver un error.
4. **`request/controlador_db.py:34-37` — parseo en import time.** `DB_CONFIGS` se
   construye al importar el módulo, después de `load_dotenv()`. Un `.env`
   mal escrito tumba el arranque de gunicorn y se manifiesta como HTTP 502 sin
   log legible. Diferir o hacer el parseo totalmente tolerante a errores.
5. **`request/controlador_db.py:53-63` — no se verifica lo negociado.** `get_db()`
   no comprueba que la conexión resultante realmente usó TLS. Conecta y trusts.

### Requisitos duros

- **Nunca degradar a texto plano.** Si la URI declara TLS, o hay TLS o hay error.
  Nunca una tercera vía silenciosa.
- **Nunca copiar la clave privada al build context ni al `Dockerfile`.** Solo
  bind mount de solo lectura (`/ssl:ro`).
- **No loguear ni incluir en respuestas** passwords, URIs completas ni contenido
  de los PEM. Si un mensaje de error necesita contexto, incluye origen, host,
  puerto, nombre de base y si TLS está activo — nunca las credenciales.
- **Preservar el comportamiento público** de `selectData`, `selectValidations`,
  `getUser`, `insertTabla`, `comprobarProceso`, etc.: devuelven `()` / `{}` / `0`
  ante error. Solo cambia *qué* se reporta, no *que* se devuelve.
- No cambiar el enrutado por país: `get_country_code()` sigue leyendo
  `country` → `X-Country-Code` → `DEFAULT_COUNTRY = "COL"`, y las claves de
  `DB_CONFIGS` siguen siendo `COL` / `HND`.
- Respetar que las consultas existentes usan **bases distintas** de la de
  conexión (`pki_firma_electronica.*`, `usuarios.*`): son privilegios del usuario
  en el servidor, no un defecto del cliente. No las toques.

### Compensaciones por la falta de verificación de hostname

Como el driver no puede validar el SAN, y dado que el SAN sí es correcto, mitiga
el riesgo de spoofing con estas tres, en este orden de preferencia:

1. **Permitir el tráfico en el firewall solo por IP de origen del servidor**, no
   por rango abierto. Documenta la IP en el compose/README.
2. **Pinear `tls_version=TLSv1.2,TLSv1.3`** para evitar que se negocie una versión vieja.
3. Documentar explícitamente la limitación en el README del proyecto, para que
   quien herede el código sepa qué garantía falta y por qué.

No inventes un parche casero de verificación de hostname sobre el driver C.

### Criterios de aceptación (verificables)

- [ ] `pytest tests/test_db_tls.py` pasa completo, sin modificar el archivo de tests.
- [ ] Dentro del contenedor, `ls -l /ssl/` muestra los tres PEM, legibles por el
      usuario del proceso, y **no** aparecen en la imagen (`docker history` /
      `docker run --rm <img> ls /app` no los lista).
- [ ] Con los tres PEM presentes, la conexión reporta un `tls_cipher()` **no
      vacío** y un `tls_version()` dentro de la lista permitida.
- [ ] Con cualquiera de los tres PEM ausente o con ruta relativa, la conexión
      **falla con `DbConnectionError` en español legible** que diga qué archivo
      falta — no degrada, no conecta en claro.
- [ ] Con el PEM de clave corrupto o con contraseña cifrada, el error menciona el
      formato/ruta, no un error genérico de autenticación.
- [ ] Con el `ca.pem` que **no** firma al certificado del servidor, el error dice
      que la verificación falló (fallo de cadena), no "access denied".
- [ ] Borrando la variable `DB_COL_URI` del entorno, el import del módulo sigue
      funcionando y el error aparece **al conectar**, no al arrancar.
- [ ] Con una URI deliberadamente malformada (password con `/` o `#` sin
      codificar), gunicorn arranca igual, el warning queda en el log **una sola
      vez**, y la petición que use esa configuración falla de forma explícita.
- [ ] Con el puerto 3300 bloqueado, la petición falla en menos de
      `connect_timeout + 2` segundos con un error de timeout, no se queda colgada.
- [ ] `docker compose up -d --build` levanta el servicio **con el compose que
      escribas** (no hay uno hoy) y `curl localhost:4000/health` responde 200.
- [ ] El servicio **no** escribe nada en disco al importarse.

### Orden de trabajo sugerido

1. Corre el servidor y lee `tests/test_db_tls.py` entero. Ejecuta la suite y
   captura el fallo base. No escribas código antes de ver el fallo.
2. Ejecuta el bloque **Diagnóstico en el servidor** de más abajo y pega los
   resultados. Si el handshake falla ahí, el problema es de despliegue
   (montaje/permisos) y hay que arreglarlo **antes** que el código.
3. Verifica los `GRANT ... REQUIRE SSL` del usuario en MariaDB, y que la CA que
   emitió `/ssl/client-cert.pem` sea la misma que está en `/ssl/ca.pem`. Un
   desajuste CA cliente/servidor es la causa más frecuente de mTLS que "no
   funciona en ningún lado".
4. Solo entonces implementa `_as_bool`, `_parse_db_uri` tolerante, `_validar_tls`
   y `DbConnectionError` hasta que la suite pase.5. Añade `connect_timeout` / `read_timeout` / `write_timeout` y la verificación
   post-conexión de `tls_cipher()`.
6. Escribe el `docker-compose.yml` con el bind mount `/ssl:ro` y las variables.
7. Revisa que no quede ninguna ruta de código capaz de conectar sin TLS.
8. Ejecuta la checklist de criterios de aceptación de arriba, una por una, y
   reporta el resultado real de cada una — incluidas las que fallen.

### Diagnóstico en el servidor

Ejecuta esto **primero**, antes de tocar código, y pega la salida. Aísla si el
problema es de despliegue o de aplicación.

```bash
# 0) ¿Dónde están los PEM en el host?
sudo ls -l /ruta/real/del/host/ssl/
sudo openssl x509 -in /ruta/real/ca.pem -noout -subject -issuer -dates
sudo openssl x509 -in /ruta/real/client-cert.pem -noout -subject -issuer -dates
#    -> subject != issuer => el cert de cliente está bien; si coincide, es una CA
#       autofirmada mal encadenada.
sudo openssl x509 -in /ruta/real/client-key.pem -noout -checkend 0
sudo openssl rsa -in /ruta/real/client-key.pem -noout -check   # debe decir OK

# 1) ¿El certificado del servidor tiene el SAN correcto?
openssl s_client -connect identidad.efirmaplus.com:3300 -starttls mysql -showcerts 2>/dev/null \
  | openssl x509 -noout -text | grep -A1 "Subject Alternative Name"
#    Si no aparece 'identidad.efirmaplus.com', la verificación de identidad
#    fallaría en cualquier cliente que la pida.

# 2) ¿La CA del host es la misma que firma al servidor?
openssl s_client -connect identidad.efirmaplus.com:3300 -starttls mysql 2>/dev/null \
  | openssl x509 -noout -issuer
#    Compara con el `issuer` del paso 0. Deben coincidir.

# 3) Dentro del contenedor: ¿existe /ssl y el proceso puede leerlo?
docker exec <contenedor> ls -l /ssl/
docker exec <contenedor> id
docker exec <contenedor> sh -c 'test -r /ssl/client-key.pem && echo legible || echo NO LEGIBLE'

# 4) Prueba de conexión aislada, con TLS obligatorio y timeouts.
#    Esto es la prueba de verdad. Pégala en un .py de una línea y ajústala.
docker exec <contenedor> python - <<'PY'
import os, mariadb
from urllib.parse import urlparse, parse_qs
u = urlparse(os.environ["DB_COL_URI"]); q = parse_qs(u.query)
for k in ("ssl_ca", "ssl_cert", "ssl_key"):
    p = q.get(k, [None])[0]
    print(f"{k}: {p} -> {'OK' if p and os.path.isfile(p) else 'FALTA'}", flush=True)
c = mariadb.connect(
    host=u.hostname, port=u.port, user=u.username, password=u.password,
    database=u.path.lstrip("/"),
    ssl=True,                                   # obligatorio: falla si no hay TLS
    ssl_ca=q["ssl_ca"][0], ssl_cert=q["ssl_cert"][0], ssl_key=q["ssl_key"][0],
    ssl_verify_cert=True,
    tls_version="TLSv1.2,TLSv1.3",
    connect_timeout=8, read_timeout=8,
)
print("CIPHER   :", repr(c.tls_cipher()))        # vacío == degradó a texto plano
print("VERSION  :", c.tls_version())
cur = c.cursor(); cur.execute("SHOW STATUS LIKE 'Ssl_%'")
for r in cur.fetchall(): print("  ", r)
PY

# 5) Lado servidor: qué ve realmente MariaDB
mysql -h identidad.efirmaplus.com -P 3300 -u <user> -p -e "
  SHOW STATUS LIKE 'Ssl_%';
  SHOW STATUS LIKE 'Ssl_version';
  SELECT user, host, ssl_type, ssl_cipher, x509_issuer FROM mysql.user
   WHERE user IN ('administrador_ssl','administrador');"
#    ssl_cipher debe venir no vacío. ssl_type debe incluir 'CERTIFICATE' si el
#    usuario exige certificado de cliente (mTLS).

# 6) Logs del servicio: qué se reportó realmente
docker logs <contenedor> --tail 200 | grep -iE 'ssl|tls|cert|1045|2003|2002'
```

### Matriz error → causa → arreglo

| Error observado | Causa | Arreglo |
|---|---|---|
| `unable to get local issuer certificate` | `/ssl/ca.pem` no es la CA que firmó al servidor, o al cert de cliente | Paso 0 y 2 de diagnóstico. Re-emitir desde la CA correcta |
| `certificate verify failed` | cadena rota, o cert de cliente expirado / no emitido por la CA del servidor | Comparar `issuer` de ambos lados. Revisar `notAfter` |
| `host not found in certificate` / `hostname mismatch` | SAN ausente o distinto. **No debería ocurrir**: el server sí tiene SAN. Si aparece, el driver no es el que crees | `python -c "import mariadb; print(mariadb.__version__)"`. Ojo a `_mariadb*.pyd` desactualizado |
| `Access denied for user` con TLS activo | mTLSAssertion: el usuario no exige `REQUIRE X509`, o la clave no corresponde al cert cargado, o la clave tiene passphrase que no se puede leer | `SHOW CREATE USER`; `GRANT ... REQUIRE SSL, X509`; regenerar la key sin passphrase o implementar su carga |
| `SSL not supported by this build` | `mariadb` (paquete Python) compilado contra un Connector/C distinto al del sistema, o falta `pkg-config`/`libssl-dev` en el build | En la imagen: `libmariadb-dev-compat` + `libmariadb-dev` + `pkg-config`. Verificar `mariadb.mariadbapi_version` (esperado 3.4.x) |
| `Can't connect to MySQL server` / timeout en 3300/3310 | firewall, o el puerto no expone TLS porque el server no tiene `ssl` habilitado | `mysql --ssl-mode=REQUIRED -h ... -P 3300`. Revisar `ssl` en el `my.cnf` del server |
| `Can't connect ...` inmediato, sin timeout | no se pasó `connect_timeout`, el SYN se pierde | Defecto 3. Añadir los tres timeouts |
| `No such file or directory: /ssl/...` | el bind mount no está, o apunta a una ruta del host equivocada | Defecto 2. `docker inspect` para verificar los montajes |
| `Cannot load CA file` / `error:1408F10B` | PEM corrupto, o key con passphrase, o permisos de lectura | `openssl x509 -noout -in ...`, `openssl rsa -check`, y `chmod` / usuario no root |
| Conecta pero `tls_cipher()` vacío | degradó a texto plano | Localiza el `if` que descarta el bloque SSL y elimínalo. Verificar `ssl=True` presente en el dict que se pasa a `connect()` |
| `Can't load plugin auth_gssapi_client` | el server ofrece un plugin de auth no disponible en el build | No es TLS. Ajustar el plugin de auth del usuario |

### Fuera de alcance

No toques en esta pasada: OCR/deepface/easyocr, GCS, la lógica de los
endpoints, el pool de conexiones, ni la colisión de puerto con
`app-python-unico` (ambos usan `0.0.0.0:4000`) salvo que estorbe para probar. El
objetivo es una conexión TLS correcta, verificable y a prueba de degradación
silenciosa.

### Formato del reporte final

1. Salida del diagnóstico (paso 0 a 6) **antes** de cualquier cambio.
2. Causa raíz confirmada, con el error exacto que la evidencia.
3. Archivos y líneas modificados, con el diff.
4. Checklist de criterios de aceptación, con PASS/FAIL real de cada punto.
5. Lo que sigue pendiente, explícito.
