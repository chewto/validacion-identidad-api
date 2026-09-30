import mariadb
import base64
import socket
import requests
import utilities.logs as logs
import os
from urllib.parse import urlparse, parse_qsl, unquote
from flask import g, request as flask_request
from dotenv import load_dotenv

load_dotenv()

# Parametros TLS que mariadb.connect() acepta tal cual en MariaDB
# Connector/Python 1.1.12 (Connector/C 3.4.4). Cualquier otro parametro de la
# URI se ignora, para que agregar un flag en el .env no rompa el arranque.
_SSL_BOOL_PARAMS = ("ssl", "ssl_verify_cert")
_SSL_PATH_PARAMS = ("ssl_ca", "ssl_capath", "ssl_cert", "ssl_key", "ssl_crlpath")
_SSL_STR_PARAMS = ("tls_version",)

# Los puertos 3300/3310 no son estandar. Sin timeouts, un firewall que dropee el
# SYN deja la peticion colgada indefinidamente en vez de devolver un error.
DB_CONNECT_TIMEOUT = int(os.getenv("DB_CONNECT_TIMEOUT", "10"))
DB_READ_TIMEOUT = int(os.getenv("DB_READ_TIMEOUT", "30"))
DB_WRITE_TIMEOUT = int(os.getenv("DB_WRITE_TIMEOUT", "30"))

class DbConnectionError(mariadb.Error):
  """Fallo al abrir una conexion a la base de datos.

  Hereda de mariadb.Error a proposito: los `except mariadb.Error` que ya hay en
  las ~20 funciones de este modulo siguen capturandola, asi que el comportamiento
  publico de selectData, getUser, insertTabla, etc. no cambia. Solo cambia que
  se reporta, no que se devuelve."""

_TLS_WARNED = set()

def _as_bool(value):
  """Normaliza un flag booleano de la URI. Devuelve el singleton bool real y no
  un truthy, porque el contrato de tests/test_db_tls.py compara con `is`."""
  return str(value).strip().lower() in ("1", "true", "yes", "on")

def _parse_db_uri(uri):
  """Convierte la URI de conexion en kwargs de mariadb.connect().

  NUNCA levanta excepciones: un .env mal escrito no puede impedir que gunicorn
  arranque, porque eso se manifestaba como HTTP 502 sin log legible. Es una
  funcion pura, sin validacion de disco; toda comprobacion ocurre despues, en
  _validar_tls(), ya en tiempo de request. Un error de formato se devuelve en la
  clave privada `_parse_error` para que el resto del modulo siga funcionando.
  """
  try:
    return _build_db_config(uri)
  except Exception as e:
    return {
      "host": None, "port": 3306, "user": None, "password": None, "database": "",
      "_parse_error": f"URI de base de datos mal formada: no se pudo interpretar ({e})",
    }

def _build_db_config(uri):
  parsed = urlparse(uri)
  problemas = []

  # parsed.port lanza ValueError cuando el "host:puerto" no esta limpio, y eso
  # pasa cuando la password trae un '@', '/', '?' o '#' sin percent-encodear:
  # urlparse corta el netloc en el primer caracter raro y el resto se pierde.
  try:
    port = parsed.port or 3306
  except ValueError:
    port = 3306
    problemas.append(
      "el puerto no es un numero entero; la password parece traer un caracter "
      "sin escapar (@ / ? #)"
    )

  # '#' abre fragmento: todo lo que sigue se descarta, incluida la parte de la
  # conexion, y urlparse se queda sin usuario ni password.
  if parsed.fragment:
    problemas.append(
      f"se tranco en el fragmento '{parsed.fragment[:40]}': la password parece "
      "contener un '#' sin escapar, codificalo con %23"
    )

  # '/' sin escapar empuja el resto de la URI hacia el path.
  if "@" in parsed.path:
    problemas.append(
      f"ruta de base de datos invalida '{parsed.path[:40]}': la password parece "
      "contener un '/' sin escapar, codificalo con %2F"
    )

  config = {
    "host": parsed.hostname,
    "port": port,
    "user": unquote(parsed.username) if parsed.username else parsed.username,
    "password": unquote(parsed.password) if parsed.password else parsed.password,
    "database": parsed.path.lstrip("/"),
  }

  if problemas:
    config["_parse_error"] = "URI de base de datos mal formada: " + "; ".join(problemas)

  tls = {}
  for key, value in parse_qsl(parsed.query):
    if key in _SSL_BOOL_PARAMS:
      tls[key] = _as_bool(value)
    elif key in _SSL_PATH_PARAMS or key in _SSL_STR_PARAMS:
      tls[key] = value

  if tls:
    # ssl=True es lo que hace obligatorio el handshake TLS. Sin el, el connector
    # negocia en claro en silencio cuando algo falla, y no hay forma de notarlo.
    # ssl_verify_cert verifica la cadena del certificado del servidor; ojo, en
    # este driver NO verifica el hostname/SAN (ver README).
    tls.setdefault("ssl", True)
    tls.setdefault("ssl_verify_cert", False)
    config.update(tls)

  return config

def _validar_tls(config, pais):
  """Comprueba la config TLS antes de abrir el socket.

  Levanta DbConnectionError para que el fallo llegue como error legible en vez de
  degradar a texto plano. El parseo preserva las rutas tal cual; que existan de
  verdad en el contenedor se comprueba aqui.
  """
  if config.get("_parse_error"):
    raise DbConnectionError(
      f"URI de base de datos mal formada [{pais}]: {config['_parse_error']}"
    )

  if not config.get("ssl"):
    return

  problemas = []
  for key in _SSL_PATH_PARAMS:
    value = config.get(key)
    if not value:
      continue
    if not os.path.isabs(value):
      problemas.append(f"{key} debe ser una ruta absoluta, se recibio: {value}")
    elif not os.path.isfile(value):
      problemas.append(
        f"{key} no existe o no es un archivo: {value} "
        "(revisa el bind mount de /ssl dentro del contenedor)"
      )

  if problemas:
    raise DbConnectionError(f"Config TLS invalida [{pais}]: " + "; ".join(problemas))

  if config.get("ssl_verify_cert"):
    return

  # Cifrado activo, identidad no validada: se avisa una sola vez por pais para no
  # inundar el log en cada request.
  if pais in _TLS_WARNED:
    return
  _TLS_WARNED.add(pais)
  try:
    logs.addLog(
      logs.checkLogsFile(),
      f"AVISO TLS: {config.get('host')} se conecta cifrado pero SIN verificar el "
      "certificado del servidor (ssl_verify_cert=False). MariaDB Connector 1.1.12 "
      "no puede validar el hostname/SAN del servidor; compense con firewall por "
      "IP de origen y tls_version pineado."
    )
  except Exception as e:
    # Un log que no se puede escribir jamas debe tumbar la conexion.
    print(f"No se pudo escribir el aviso TLS en el log: {e}")

def _tls_negociada(conn):
  """Devuelve el cifrado y la version TLS realmente negociados, o "" si la
  conexion es de texto plano. En Connector/Python 1.1.12 tls_cipher y
  tls_version son @property, no metodos; se toleran ambas formas."""
  negotiated = []
  for atributo in ("tls_cipher", "tls_version"):
    valor = getattr(conn, atributo, None)
    if callable(valor):
      try:
        valor = valor()
      except Exception:
        valor = None
    if valor:
      negotiated.append(f"{atributo}={valor}")
  return " ".join(negotiated)

DB_CONFIGS = {
    "COL": _parse_db_uri(os.getenv("DB_COL_URI", "")),
    "HND": _parse_db_uri(os.getenv("DB_HON_URI", "")),
}

DEFAULT_COUNTRY = "COL"

def get_country_code():
  try:
    country = (
      flask_request.args.get("country")
      or flask_request.form.get("country")
      or flask_request.headers.get("X-Country-Code")
      or DEFAULT_COUNTRY
    )
    return country.upper()
  except RuntimeError:
    return DEFAULT_COUNTRY

def get_db(pais=None):
  if pais is None:
    pais = get_country_code()
  key = f"db_{pais}"
  g_dict = vars(g)
  if key not in g_dict:
    config = DB_CONFIGS.get(pais)
    if not config:
      raise ValueError(f"País no soportado: {pais}")
    _validar_tls(config, pais)

    # Las claves que empiezan con "_" son diagnostico interno, no argumentos
    # validos de mariadb.connect().
    kwargs = {k: v for k, v in config.items() if not k.startswith("_")}
    kwargs.setdefault("connect_timeout", DB_CONNECT_TIMEOUT)
    kwargs.setdefault("read_timeout", DB_READ_TIMEOUT)
    kwargs.setdefault("write_timeout", DB_WRITE_TIMEOUT)

    tls_requerido = bool(config.get("ssl"))
    try:
      conn = mariadb.connect(**kwargs)
    except mariadb.Error as e:
      raise DbConnectionError(
        f"Fallo de conexion a {config.get('host')}:{config.get('port')}/"
        f"{config.get('database')} [{pais}, {'TLS' if tls_requerido else 'SIN TLS'}]: {e}"
      ) from e

    # Conectar y confiar no es verificar. Si la URI pedia TLS, se comprueba que la
    # conexion realmente lo haya negociado antes de entregarla: si no, se cierra
    # para no mandar credenciales ni datos en texto plano.
    if tls_requerido and not _tls_negociada(conn):
      try:
        conn.close()
      except Exception:
        pass
      raise DbConnectionError(
        f"Degradacion de seguridad en {config.get('host')}:{config.get('port')}/"
        f"{config.get('database')} [{pais}, TLS]: la conexion se abrio pero no "
        "negocio TLS. Se cierra para no enviar credenciales en texto plano."
      )

    g_dict[key] = conn
  return g_dict[key]

def close_db_connections(exception=None):
  g_dict = vars(g)
  for key in [k for k in g_dict if k.startswith("db_")]:
    conn = g_dict.pop(key)
    try:
      conn.close()
    except Exception:
      pass

def obtenerIpPrivada():
  hostname = socket.gethostname()
  direccionIp = socket.gethostbyname(hostname)
  return direccionIp

def obtenerIpPublica():
  ip = requests.get('https://api.ipify.org').text
  return ip

def selectData(query, *values, pais=None):
  try:
    conn = get_db(pais)
    cursor = conn.cursor()
    cursor.execute(query, values)
    data = cursor.fetchone()
    return data
  except mariadb.Error as e:
    print(e)
    return ()

def selectValidations(query, *values, pais=None):
  try:
    conn = get_db(pais)
    cursor = conn.cursor()
    cursor.execute(query, values)
    data = cursor.fetchall()
    return data
  except mariadb.Error as e:
    print(e)
    return ()

def getUser(tabla, id, pais=None):
  try:
    conn = get_db(pais)
    cursor = conn.cursor()
    cursor.execute(f'SELECT * FROM {tabla} WHERE id = {id}')
    usuario = cursor.fetchone()
    usuarioDiccionario = {
      'nombre': usuario[1],
      'apellido': usuario[2],
      'correo': usuario[5],
      'documento': usuario[3]
    }
    cursor.close()
    return usuarioDiccionario
  except mariadb.Error as e:
    print(e)
    return {}

def insertTabla(columns: tuple, table: str, values: tuple, pais=None):
    conn = None
    try:
        conn = get_db(pais)
        with conn.cursor() as cursor:
            columnasStr = ','.join(columns)
            placeHolderStr = ','.join(['?' for _ in columns])
            query = f"INSERT INTO {table} ({columnasStr}) VALUES ({placeHolderStr})"
            cursor.execute(query, values)
            documentoUsuarioID = cursor.lastrowid
            conn.commit()
            return documentoUsuarioID
    except mariadb.Error as e:
        if conn:
            conn.rollback()
        print(f"Error en base de datos: {e}")
        logsPath = logs.checkLogsFile()
        logs.writeLogs(logsPath, f"Error en tabla {table}: {e}")
        return 0

def comprobarProceso(id, pais=None):
  try:
    conn = get_db(pais)
    cursor = conn.cursor()
    queryInfo = f'SELECT count(ea.estado_verificacion), ea.estado_verificacion FROM documento_usuario as du INNER JOIN evidencias_adicionales ea ON ea.id=du.id_evidencias_adicionales WHERE (ea.estado_verificacion="verificado" OR ea.estado_verificacion="Iniciando segunda validación" OR ea.estado_verificacion="Procesando segunda validación" OR ea.estado_verificacion="se requiere nueva validación") and id_usuario_efirma = {id}'
    cursor.execute(queryInfo)
    comprobacion = cursor.fetchone()
    if(comprobacion):
      return {
        "validaciones": comprobacion[0],
        "estado": comprobacion[1]
      }
    else:
      return {
        "validaciones": 0,
        "estado": ''
      }
  except mariadb.Error as e:
    print("error =", e)
    return {"validaciones": 0, "estado": ''}

def checkValidation(query, pais=None):
  try:
    conn = get_db(pais)
    cursor = conn.cursor()
    cursor.execute(query)
    comprobacion = cursor.fetchone()
    if(comprobacion):
      return {
        "id": comprobacion[0],
        "estado": comprobacion[1]
      }
    else:
      return {
        "id": 0,
        "estado": ''
      }
  except mariadb.Error as e:
    print("error =", e)
    return {
        "id": 0,
        "estado": ''
      }

def obtenerEntidad(query, pais=None):
  try:
    conn = get_db(pais)
    cursor = conn.cursor()
    cursor.execute(query)
    entidad = cursor.fetchone()
    if(entidad):
      return entidad[0], entidad[1]
    else:
      return 0, 0
  except mariadb.Error as e:
    print(e)
    return 0, 0

def obtenerEntidadHash(hash, pais=None):
  try:
    conn = get_db(pais)
    cursor = conn.cursor()
    query = """SELECT id FROM pki_validacion.parametros_validacion AS pv
    WHERE pv.parametros_hash = ?"""
    cursor.execute(query,(hash,))
    entidad = cursor.fetchone()
    if(entidad):
      return entidad[0]
    else:
      return 0
  except mariadb.Error as e:
    print(e)
    return 0

def selectProvider(id, pais=None):
  try:
    conn = get_db(pais)
    cursor = conn.cursor()
    queryInfo = "SELECT ent.nombre_entidad, ent.validacion FROM pki_firma_electronica.firmador_pki fir INNER JOIN pki_firma_electronica.firma_electronica_pki AS fe ON fe.id = fir.firma_electronica_id INNER JOIN usuarios.usuarios AS usu ON usu.id = fe.usuario_id INNER JOIN usuarios.entidades AS ent ON ent.entity_id = usu.entity_id WHERE fir.id = ?"
    cursor.execute(queryInfo, (id,))
    entidad = cursor.fetchone()
    if(entidad != None):
      if(entidad[1] == None or len(entidad[1]) <= 0):
        return 'EFIRMA'
      return entidad[1]
    else:
      return 'EFIRMA'
  except mariadb.Error as e:
    print(e)
    return 'EFIRMA'

def selectValidationParams(id, query, pais=None):
  try:
    conn = get_db(pais)
    cursor = conn.cursor()
    cursor.execute(query, (id,))
    entidad = cursor.fetchone()
    return entidad if(entidad != None) else (None, None, None)
  except mariadb.Error as e:
    return (None, None, None)

def selectCallback(id, query, pais=None):
  try:
    conn = get_db(pais)
    cursor = conn.cursor()
    cursor.execute(query, (id,))
    callbackData = cursor.fetchone()
    return callbackData if(callbackData != None) else (None, None, None)
  except mariadb.Error as e:
    print(e)
    return (None, None, None)

def selectAPIKey(id, pais=None):
  try:
    conn = get_db(pais)
    cursor = conn.cursor()
    queryInfo = """
      SELECT usu.clave_api FROM usuarios.usuarios AS usu WHERE usu.id = ?
    """
    cursor.execute(queryInfo, (id,))
    callbackData = cursor.fetchone()
    print(callbackData)
    return callbackData if(callbackData != None) else (None)
  except mariadb.Error as e:
    print(e)
    return (None)

def selectUserData(id, pais=None):
  try:
    conn = get_db(pais)
    cursor = conn.cursor()
    queryInfo = """
      SELECT params.id_usuario, params.nombre, params.apellido, params.documento, params.tipo_documento, params.email, params.tipo_validacion, params.callback, params.redireccion, ent.validacion_vida, params.uso_modelo FROM pki_validacion.parametros_validacion AS params 
      INNER JOIN usuarios.usuarios AS usu ON usu.id = params.id_usuario
      INNER JOIN usuarios.entidades AS ent ON usu.entity_id = ent.entity_id 
      WHERE params.parametros_hash = ?
    """
    cursor.execute(queryInfo, (id,))
    callbackData = cursor.fetchone()
    return callbackData if(callbackData != None) else None
  except mariadb.Error as e:
    return None

def setIDs(idEvidencias, idEvidenciasAdicionales, tipoDocumento, idValidacion, pais=None):
  try:
    conn = get_db(pais)
    cursor = conn.cursor()
    queryInfo = """UPDATE pki_validacion.documento_usuario AS du
      SET du.id_evidencias = ?,
      du.id_evidencias_adicionales = ?,
      du.tipo_documento = ?
      WHERE du.id = ?"""
    cursor.execute(queryInfo, (idEvidencias, idEvidenciasAdicionales, tipoDocumento, idValidacion,))
    conn.commit()
    return 'success'
  except mariadb.Error as e:
    print(e)
    return 'error'

def select_time_logs(id_firmador: str, pais=None):
    try:
      conn = get_db(pais)
      cursor = conn.cursor()
      query = """
        SELECT id, id_firmador
        FROM pki_validacion.log_tiempos
        WHERE id_firmador = ?
        ORDER BY inicio_fecha DESC
      """
      cursor.execute(query, (id_firmador,))
      data = cursor.fetchall()
      return data if data is not None else ()
    except mariadb.Error as e:
      print(e)
      return ()

def insert_time_log_record(id: str, pais=None) -> int:
  try:
    conn = get_db(pais)
    cursor = conn.cursor()
    query = """
      INSERT INTO pki_validacion.log_tiempos
      (id_firmador, inicio_fecha)
      VALUES (?, NOW())
    """
    cursor.execute(query, (id,))
    conn.commit()
    return cursor.lastrowid
  except mariadb.Error as e:
    print(e)
    return 0

def updateDate(column: str, id: str, pais=None) -> bool:
    try:
      conn = get_db(pais)
      cursor = conn.cursor()
      query = f"UPDATE pki_validacion.log_tiempos as log SET {column} = NOW() WHERE log.id = {id}"
      cursor.execute(query, ())
      conn.commit()
      return cursor.rowcount > 0
    except mariadb.Error as e:
      print(e)
      return False

def updateSpeedtest(id: str, values: tuple, pais=None) -> bool:
    try:
        conn = get_db(pais)
        cursor = conn.cursor()
        query = (
            "UPDATE pki_validacion.log_tiempos as log "
            "SET velocidad_descarga = ?, tiempo_descarga = ?, velocidad_subida = ?, tiempo_subida = ?, velocidad_ping = ? "
            "WHERE log.id = ?"
        )
        cursor.execute(query, values + (id,))
        conn.commit()
        return cursor.rowcount > 0
    except mariadb.Error as e:
        print(e)
        return False

def updateBodySize(values: tuple, pais=None) -> bool:
    try:
        conn = get_db(pais)
        cursor = conn.cursor()
        query = (
            "UPDATE pki_validacion.log_tiempos as log "
            "SET peso_evidencias = ? "
            "WHERE log.id_firmador = ?"
        )
        cursor.execute(query, values)
        conn.commit()
        return cursor.rowcount > 0
    except mariadb.Error as e:
        print(e)
        return False
