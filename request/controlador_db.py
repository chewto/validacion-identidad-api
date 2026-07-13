import mariadb
import base64
import socket
import requests
import utilities.logs as logs
import os
from urllib.parse import urlparse
from flask import g, request as flask_request
from dotenv import load_dotenv

load_dotenv()

def _parse_db_uri(uri):
  parsed = urlparse(uri)
  return {
    "host": parsed.hostname,
    "port": parsed.port or 3306,
    "user": parsed.username,
    "password": parsed.password,
    "database": parsed.path.lstrip("/"),
  }

DB_CONFIGS = {
    "CO": _parse_db_uri(os.getenv("DB_COL_URI", "")),
    "HN": _parse_db_uri(os.getenv("DB_HON_URI", "")),
}

DEFAULT_COUNTRY = "CO"

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
    g_dict[key] = mariadb.connect(**config)
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
