import pymysql
import ssl
import base64
import socket
import requests
import utilities.logs as logs
import os
from pathlib import Path
from urllib.parse import urlparse, parse_qsl, unquote
from flask import g, request as flask_request
from dotenv import load_dotenv, find_dotenv

# ----------------------------------------------------------------------
class MissingDbUriError(RuntimeError):
    """Raised when a required DB URI environment variable is absent."""
    pass

# if the current working directory changes (e.g. when the app is
# executed from a sub‑process or test runner).
# ----------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_ENV_PATH = find_dotenv(str(_PROJECT_ROOT / ".env"))
load_dotenv(_ENV_PATH, override=True)

_SSL_BOOL_PARAMS = ("ssl", "ssl_verify_cert")
_SSL_PATH_PARAMS = ("ssl_ca", "ssl_capath", "ssl_cert", "ssl_key", "ssl_crlpath")
_SSL_STR_PARAMS = ("tls_version",)
_SSL_PATH_MAP = {
    "ssl_ca": "ca",
    "ssl_capath": "capath",
    "ssl_cert": "cert",
    "ssl_key": "key",
    "ssl_crlpath": "crl",
}

DB_CONNECT_TIMEOUT = int(os.getenv("DB_CONNECT_TIMEOUT", "10"))
DB_READ_TIMEOUT = int(os.getenv("DB_READ_TIMEOUT", "30"))
DB_WRITE_TIMEOUT = int(os.getenv("DB_WRITE_TIMEOUT", "30"))

class DbConnectionError(pymysql.Error):
  """Fallo al abrir una conexion a la base de datos."""

_TLS_WARNED = set()

def _as_bool(value):
  """Normaliza un flag booleano de la URI."""
  return str(value).strip().lower() in ("1", "true", "yes", "on")

def _parse_db_uri(uri):
  """Convierte la URI de conexion en kwargs de pymysql.connect()."""
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

  try:
    port = parsed.port or 3306
  except ValueError:
    port = 3306
    problemas.append(
      "el puerto no es un numero entero; la password parece traer un caracter "
      "sin escapar (@ / ? #)"
    )

  if parsed.fragment:
    problemas.append(
      f"se tranco en el fragmento '{parsed.fragment[:40]}': la password parece "
      "contener un '#' sin escapar, codificalo con %23"
    )

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

  query_params = dict(parse_qsl(parsed.query))
  ssl_dict = {}
  has_ssl_param = False

  for q_key, ssl_key in _SSL_PATH_MAP.items():
    if q_key in query_params:
      ssl_dict[ssl_key] = query_params[q_key]
      config[q_key] = query_params[q_key]
      has_ssl_param = True

  if "tls_version" in query_params:
    config["tls_version"] = query_params["tls_version"]

  if "ssl" in query_params and _as_bool(query_params["ssl"]):
    has_ssl_param = True
    config["ssl"] = True

  if has_ssl_param or "ssl_verify_cert" in query_params:
    ssl_verify = _as_bool(query_params.get("ssl_verify_cert", "false"))
    ssl_dict["check_hostname"] = ssl_verify
    if not ssl_verify:
      ssl_dict["verify_mode"] = ssl.CERT_NONE
    else:
      ssl_dict["verify_mode"] = ssl.CERT_REQUIRED
    config["ssl"] = True
    config["_ssl_dict"] = ssl_dict
    config["ssl_verify_cert"] = ssl_verify

  return config

def _validar_tls(config, pais):
  """Comprueba la config TLS antes de abrir el socket."""
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

  if pais in _TLS_WARNED:
    return
  _TLS_WARNED.add(pais)
  try:
    logs.addLog(
      logs.checkLogsFile(),
      f"AVISO TLS: {config.get('host')} se conecta cifrado pero SIN verificar el "
      "certificado del servidor (ssl_verify_cert=False)."
    )
  except Exception as e:
    print(f"No se pudo escribir el aviso TLS en el log: {e}")

def _tls_negociada(conn):
  """Devuelve el cifrado y la version TLS realmente negociados, o "" si es texto plano."""
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
  if negotiated:
    return " ".join(negotiated)
  try:
    sock = getattr(conn, '_sock', None)
    if not sock:
        sock = getattr(conn, 'socket', None)
    if sock and hasattr(sock, 'cipher') and sock.cipher():
      cipher = sock.cipher()
      version = sock.version() if hasattr(sock, 'version') else (cipher[1] if len(cipher) > 1 else '')
      return f"tls_cipher={cipher[0]} tls_version={version}"
    if getattr(conn, '_secure', False):
      return "tls_cipher=secured tls_version=unknown"
  except Exception:
    pass
  return ""

# Load DB configurations with graceful handling of missing env vars
def _load_db_config(pais: str) -> dict:
    """Return DB config dict for *pais*.
    If the required ``DB_{PAIS}_URI`` environment variable is missing, an empty
    dict is returned and a warning is logged.
    """
    env_key = f"DB_{pais}_URI"
    uri = os.getenv(env_key)
    if not uri:
        logs.addLog(
            logs.checkLogsFile(),
            f"WARNING: {env_key} not defined in .env – DB config will be empty."
        )
        return {}
    return _parse_db_uri(uri)

DB_CONFIGS = {
    "COL": _load_db_config("COL"),
    "HND": _load_db_config("HND"),
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
    # Validate that the config exists and has required fields
    if not config or not config.get("host") or not config.get("database"):
        raise MissingDbUriError(
            f"País no soportado o configuración incompleta: {pais}. "
            f"Verificá que DB_{pais}_URI esté definida en .env y el .env se cargue correctamente."
        )
    _validar_tls(config, pais)

    kwargs = {k: v for k, v in config.items() if not k.startswith("_") and not k.startswith("ssl_") and k != "tls_version" and k != "ssl"}
    kwargs.setdefault("connect_timeout", DB_CONNECT_TIMEOUT)
    kwargs.setdefault("read_timeout", DB_READ_TIMEOUT)
    kwargs.setdefault("write_timeout", DB_WRITE_TIMEOUT)

    if config.get("_ssl_dict"):
      kwargs["ssl"] = config["_ssl_dict"]
    elif config.get("ssl"):
      kwargs["ssl"] = {"check_hostname": False, "verify_mode": ssl.CERT_NONE}

    tls_requerido = bool(config.get("ssl"))
    try:
      conn = pymysql.connect(**kwargs)
    except pymysql.Error as e:
      raise DbConnectionError(
        f"Fallo de conexion a {config.get('host')}:{config.get('port')}/"
        f"{config.get('database')} [{pais}, {'TLS' if tls_requerido else 'SIN TLS'}]: {e}"
      ) from e

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

def _execute_query(cursor, query, values=None):
  if isinstance(query, str) and "?" in query:
    query = query.replace("?", "%s")
    
  # Si enviaron un solo argumento y es una tupla, la desempaquetamos.
  # Esto soluciona el caso donde se llama selectData(query, ()) y values llega como ((),)
  if values is not None and len(values) == 1 and isinstance(values[0], tuple):
      values = values[0]
      
  if values:
    return cursor.execute(query, values)
  return cursor.execute(query)

def selectData(query, *values, pais=None):
  logsPath = logs.checkLogsFile()
  logs.addLog(logsPath, f"selectData: query={query}, values={values}, pais={pais}")
  try:
    conn = get_db(pais)
    cursor = conn.cursor()
    _execute_query(cursor, query, values if values else None)
    data = cursor.fetchone()
    cursor.close()
    return data if data is not None else ()
  except pymysql.Error as e:
    print(e)
    return ()

def selectValidations(query, *values, pais=None):
  try:
    conn = get_db(pais)
    cursor = conn.cursor()
    _execute_query(cursor, query, values if values else None)
    data = cursor.fetchall()
    cursor.close()
    return data if data is not None else ()
  except pymysql.Error as e:
    print(e)
    return ()

def getUser(tabla, id, pais=None):
  try:
    conn = get_db(pais)
    cursor = conn.cursor()
    _execute_query(cursor, f'SELECT * FROM {tabla} WHERE id = %s', (id,))
    usuario = cursor.fetchone()
    cursor.close()
    if not usuario:
      return {}
    usuarioDiccionario = {
      'nombre': usuario[1],
      'apellido': usuario[2],
      'correo': usuario[5],
      'documento': usuario[3]
    }
    return usuarioDiccionario
  except pymysql.Error as e:
    print(e)
    return {}

def insertTabla(columns: tuple, table: str, values: tuple, pais=None):
    conn = None
    try:
        conn = get_db(pais)
        cursor = conn.cursor()
        columnasStr = ','.join(columns)
        placeHolderStr = ','.join(['%s' for _ in columns])
        query = f"INSERT INTO {table} ({columnasStr}) VALUES ({placeHolderStr})"
        _execute_query(cursor, query, values)
        documentoUsuarioID = cursor.lastrowid
        conn.commit()
        cursor.close()
        return documentoUsuarioID
    except pymysql.Error as e:
        if conn:
            try:
              conn.rollback()
            except Exception:
              pass
        print(f"Error en base de datos: {e}")
        logsPath = logs.checkLogsFile()
        logs.writeLogs(logsPath, f"Error en tabla {table}: {e}")
        return 0

def comprobarProceso(id, pais=None):
  try:
    conn = get_db(pais)
    cursor = conn.cursor()
    queryInfo = f'SELECT count(ea.estado_verificacion), ea.estado_verificacion FROM documento_usuario as du INNER JOIN evidencias_adicionales ea ON ea.id=du.id_evidencias_adicionales WHERE (ea.estado_verificacion="verificado" OR ea.estado_verificacion="Iniciando segunda validación" OR ea.estado_verificacion="Procesando segunda validación" OR ea.estado_verificacion="se requiere nueva validación") and id_usuario_efirma = %s'
    _execute_query(cursor, queryInfo, (id,))
    comprobacion = cursor.fetchone()
    cursor.close()
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
  except pymysql.Error as e:
    print("error =", e)
    return {"validaciones": 0, "estado": ''}

def checkValidation(query, pais=None):
  try:
    conn = get_db(pais)
    cursor = conn.cursor()
    _execute_query(cursor, query)
    comprobacion = cursor.fetchone()
    cursor.close()
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
  except pymysql.Error as e:
    print("error =", e)
    return {
        "id": 0,
        "estado": ''
      }

def obtenerEntidad(query, pais=None):
  try:
    conn = get_db(pais)
    cursor = conn.cursor()
    _execute_query(cursor, query)
    entidad = cursor.fetchone()
    cursor.close()
    if(entidad):
      return entidad[0], entidad[1]
    else:
      return 0, 0
  except pymysql.Error as e:
    print(e)
    return 0, 0

def obtenerEntidadHash(hash, pais=None):
  try:
    conn = get_db(pais)
    cursor = conn.cursor()
    query = """SELECT id FROM pki_validacion.parametros_validacion AS pv
    WHERE pv.parametros_hash = %s"""
    _execute_query(cursor, query, (hash,))
    entidad = cursor.fetchone()
    cursor.close()
    if(entidad):
      return entidad[0]
    else:
      return 0
  except pymysql.Error as e:
    print(e)
    return 0

def selectProvider(id, pais=None):
  try:
    conn = get_db(pais)
    cursor = conn.cursor()
    queryInfo = "SELECT ent.nombre_entidad, ent.validacion FROM pki_firma_electronica.firmador_pki fir INNER JOIN pki_firma_electronica.firma_electronica_pki AS fe ON fe.id = fir.firma_electronica_id INNER JOIN usuarios.usuarios AS usu ON usu.id = fe.usuario_id INNER JOIN usuarios.entidades AS ent ON ent.entity_id = usu.entity_id WHERE fir.id = %s"
    _execute_query(cursor, queryInfo, (id,))
    entidad = cursor.fetchone()
    cursor.close()
    if(entidad != None):
      if(entidad[1] == None or len(entidad[1]) <= 0):
        return 'EFIRMA'
      return entidad[1]
    else:
      return 'EFIRMA'
  except pymysql.Error as e:
    print(e)
    return 'EFIRMA'

def selectValidationParams(id, query, pais=None):
  try:
    conn = get_db(pais)
    cursor = conn.cursor()
    _execute_query(cursor, query, (id,))
    entidad = cursor.fetchone()
    cursor.close()
    return entidad if(entidad != None) else (None, None, None)
  except pymysql.Error as e:
    return (None, None, None)

def selectCallback(id, query, pais=None):
  try:
    conn = get_db(pais)
    cursor = conn.cursor()
    _execute_query(cursor, query, (id,))
    callbackData = cursor.fetchone()
    cursor.close()
    return callbackData if(callbackData != None) else (None, None, None)
  except pymysql.Error as e:
    print(e)
    return (None, None, None)

def selectAPIKey(id, pais=None):
  try:
    conn = get_db(pais)
    cursor = conn.cursor()
    queryInfo = """
      SELECT usu.clave_api FROM usuarios.usuarios AS usu WHERE usu.id = %s
    """
    _execute_query(cursor, queryInfo, (id,))
    callbackData = cursor.fetchone()
    cursor.close()
    print(callbackData)
    return callbackData if(callbackData != None) else (None)
  except pymysql.Error as e:
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
      WHERE params.parametros_hash = %s
    """
    _execute_query(cursor, queryInfo, (id,))
    callbackData = cursor.fetchone()
    cursor.close()
    return callbackData if(callbackData != None) else None
  except pymysql.Error as e:
    return None

def setIDs(idEvidencias, idEvidenciasAdicionales, tipoDocumento, idValidacion, pais=None):
  try:
    conn = get_db(pais)
    cursor = conn.cursor()
    queryInfo = """UPDATE pki_validacion.documento_usuario AS du
      SET du.id_evidencias = %s,
      du.id_evidencias_adicionales = %s,
      du.tipo_documento = %s
      WHERE du.id = %s"""
    _execute_query(cursor, queryInfo, (idEvidencias, idEvidenciasAdicionales, tipoDocumento, idValidacion,))
    conn.commit()
    cursor.close()
    return 'success'
  except pymysql.Error as e:
    print(e)
    return 'error'

def select_time_logs(id_firmador: str, pais=None):
    try:
      conn = get_db(pais)
      cursor = conn.cursor()
      query = """
        SELECT id, id_firmador
        FROM pki_validacion.log_tiempos
        WHERE id_firmador = %s
        ORDER BY inicio_fecha DESC
      """
      _execute_query(cursor, query, (id_firmador,))
      data = cursor.fetchall()
      cursor.close()
      return data if data is not None else ()
    except pymysql.Error as e:
      print(e)
      return ()

def insert_time_log_record(id: str, pais=None) -> int:
  try:
    conn = get_db(pais)
    cursor = conn.cursor()
    query = """
      INSERT INTO pki_validacion.log_tiempos
      (id_firmador, inicio_fecha)
      VALUES (%s, NOW())
    """
    _execute_query(cursor, query, (id,))
    last_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    return last_id
  except pymysql.Error as e:
    print(e)
    return 0

def updateDate(column: str, id: str, pais=None) -> bool:
    try:
      conn = get_db(pais)
      cursor = conn.cursor()
      query = f"UPDATE pki_validacion.log_tiempos as log SET {column} = NOW() WHERE log.id = %s"
      _execute_query(cursor, query, (id,))
      count = cursor.rowcount
      conn.commit()
      cursor.close()
      return count > 0
    except pymysql.Error as e:
      print(e)
      return False

def updateSpeedtest(id: str, values: tuple, pais=None) -> bool:
    try:
        conn = get_db(pais)
        cursor = conn.cursor()
        query = (
            "UPDATE pki_validacion.log_tiempos as log "
            "SET velocidad_descarga = %s, tiempo_descarga = %s, velocidad_subida = %s, tiempo_subida = %s, velocidad_ping = %s "
            "WHERE log.id = %s"
        )
        _execute_query(cursor, query, values + (id,))
        count = cursor.rowcount
        conn.commit()
        cursor.close()
        return count > 0
    except pymysql.Error as e:
        print(e)
        return False

def updateBodySize(values: tuple, pais=None) -> bool:
    try:
        conn = get_db(pais)
        cursor = conn.cursor()
        query = (
            "UPDATE pki_validacion.log_tiempos as log "
            "SET peso_evidencias = %s "
            "WHERE log.id_firmador = %s"
        )
        _execute_query(cursor, query, values)
        count = cursor.rowcount
        conn.commit()
        cursor.close()
        return count > 0
    except pymysql.Error as e:
        print(e)
        return False
