import mariadb
import base64
import socket
import requests
import utilities.logs as logs
import os
from dotenv import load_dotenv

load_dotenv()

passwordDB = os.getenv("DB_PASSWORD")
nombreDB = os.getenv("DB_NAME")
hostDB = os.getenv("DB_HOST")
portDB = int(os.getenv("DB_PORT"))
userDB = os.getenv("DB_USER")

def obtenerIpPrivada():
  hostname = socket.gethostname()
  direccionIp = socket.gethostbyname(hostname)
  return direccionIp

def obtenerIpPublica():
  ip = requests.get('https://api.ipify.org').text

  return ip

def selectData(query, *values):
  try:
    conn = mariadb.connect(
      user=userDB,
      password=passwordDB,
      host=hostDB,
      port=portDB,
      database=nombreDB
    )
  except mariadb.Error as e:
    print(e)
    return ()
  
  try:

    cursor = conn.cursor()

    cursor.execute(query, values)

    data = cursor.fetchone()

    return data

  except mariadb.Error as e:
    print(e)
    return ()

  finally:
    conn.commit()
    cursor.close()
    conn.close()

def getUser(tabla,id):
  
  conn = mariadb.connect(
    user=userDB,
    password=passwordDB,
    host=hostDB,
    port=portDB,
    database=nombreDB
  )

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
  conn.close()

  return usuarioDiccionario


def insertTabla(columns: tuple, table: str, values: tuple):
    conn = None
    try:
        # 1. Establecer conexión única para esta petición
        conn = mariadb.connect(
            user=userDB,
            password=passwordDB,
            host=hostDB,
            port=portDB,
            database=nombreDB
        )
        
        # Usamos context managers para asegurar el cierre automático del cursor
        with conn.cursor() as cursor:
            columnasStr = ','.join(columns)
            # Creamos los placeholders (?,?,?) de forma eficiente
            placeHolderStr = ','.join(['?' for _ in columns])

            query = f"INSERT INTO {table} ({columnasStr}) VALUES ({placeHolderStr})"
            
            # 2. Ejecutar la inserción
            cursor.execute(query, values)
            
            # 3. Capturar el ID antes de cualquier otra operación
            documentoUsuarioID = cursor.lastrowid
            
            # 4. Confirmar los cambios solo si llegamos aquí sin errores
            conn.commit()
            
            return documentoUsuarioID

    except mariadb.Error as e:
        # 5. Si algo falla, revertimos cualquier cambio pendiente
        if conn:
            conn.rollback()
            
        print(f"Error en base de datos: {e}")
        logsPath = logs.checkLogsFile()
        logs.writeLogs(logsPath, f"Error en tabla {table}: {e}")
        return 0

    finally:
        # 6. Asegurar que la conexión regrese al pool o se cierre
        if conn:
            conn.close()

def comprobarProceso(id):

  try:
    conn = mariadb.connect(
      user=userDB,
      password=passwordDB,
      host=hostDB,
      port=portDB,
      database=nombreDB
    )
  except mariadb.Error as e:
    print(e)
    return f"error en la query, error = {e}"

  try:
    cursor = conn.cursor()

    queryInfo = f'SELECT count(ea.estado_verificacion), ea.estado_verificacion FROM documento_usuario as du INNER JOIN evidencias_adicionales ea ON ea.id=du.id_evidencias_adicionales WHERE (ea.estado_verificacion="verificado" OR ea.estado_verificacion="Iniciando segunda validación" OR ea.estado_verificacion="Procesando segunda validación" OR ea.estado_verificacion="se requiere nueva validación") and id_usuario_efirma = {id}'
    # queryInfo = f"""SELECT ev.id, ev.estado_verificacion 
    # FROM documento_usuario AS doc
    # INNER JOIN evidencias_adicionales ev ON doc.id_evidencias_adicionales = ev.id
    # WHERE id_usuario_efirma = {id}
    # ORDER BY ev.id DESC
    # LIMIT 1;
    # """
    
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

  finally:
    conn.commit()
    cursor.close()
    conn.close()

def checkValidation(query):

  try:
    conn = mariadb.connect(
      user=userDB,
      password=passwordDB,
      host=hostDB,
      port=portDB,
      database=nombreDB
    )
  except mariadb.Error as e:
    print(e)
    return f"error en la query, error = {e}"

  try:
    cursor = conn.cursor()

    queryInfo = query
    
    cursor.execute(queryInfo)

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

  finally:
    conn.commit()
    cursor.close()
    conn.close()

def obtenerEntidad(query):

  try:
    conn = mariadb.connect(
      user=userDB,
      password=passwordDB,
      host=hostDB,
      port=portDB,
      database=nombreDB
    )
  except mariadb.Error as e:
    print(e)
    return 0,0

  try:
    cursor = conn.cursor()

    cursor.execute(query)

    entidad = cursor.fetchone()

    if(entidad):
      return entidad[0], entidad[1]
    else:
      return 0, 0


  except mariadb.Error as e:
    print(e)
    return 0,0

  finally:
    conn.commit()
    cursor.close()
    conn.close()


def obtenerEntidadHash(hash):

  try:
    conn = mariadb.connect(
      user=userDB,
      password=passwordDB,
      host=hostDB,
      port=portDB,
      database=nombreDB
    )
  except mariadb.Error as e:
    print(e)
    return 0

  try:
    cursor = conn.cursor()
    query = """SELECT id_usuario FROM pki_validacion.documento_usuario AS du
    INNER JOIN pki_validacion.parametros_validacion AS pv ON pv.id= du.id
    WHERE pv.parametros_hash = ?"""

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

  finally:
    conn.commit()
    cursor.close()
    conn.close()

def selectProvider(id):
  
  try:
    conn = mariadb.connect(
      user=userDB,
      password=passwordDB,
      host=hostDB,
      port=portDB,
      database=nombreDB
    )
  except mariadb.Error as e:
    print(e)
    return 'EFIRMA'

  try:
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

  finally:
    conn.commit()
    cursor.close()
    conn.close()


def selectValidationParams(id, query):
  
  try:
    conn = mariadb.connect(
      user=userDB,
      password=passwordDB,
      host=hostDB,
      port=portDB,
      database=nombreDB
    )
    # conn = mariadb.connect(
    #   user="root",
    #   password="10830921",
    #   host="154.38.190.87",
    #   port=3306,
    #   database="pki_validacion"
    # )
  except mariadb.Error as e:
    print(e)
    return ''

  try:
    cursor = conn.cursor()

    cursor.execute(query, (id,))

    entidad = cursor.fetchone()

    return entidad if(entidad != None) else (None, None, None)

  except mariadb.Error as e:
    return (None, None, None)

  finally:
    conn.commit()
    cursor.close()
    conn.close()


def selectCallback(id, query):

  try:
    conn = mariadb.connect(
      user=userDB,
      password=passwordDB,
      host=hostDB,
      port=portDB,
      database=nombreDB
    )

  except mariadb.Error as e:
    print(e)
    return (None, None, None)

  try:
    cursor = conn.cursor()

    cursor.execute(query, (id,))

    callbackData = cursor.fetchone()

    return callbackData if(callbackData != None) else (None, None, None)

  except mariadb.Error as e:
    print(e)
    return (None, None, None)

  finally:
    conn.commit()
    cursor.close()
    conn.close()

def selectAPIKey(id):
  try:
    conn = mariadb.connect(
      user=userDB,
      password=passwordDB,
      host=hostDB,
      port=portDB,
      database=nombreDB
    )

  except mariadb.Error as e:
    print(e)
    return (None)
  

  try:
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

  
  finally:
    conn.commit()
    cursor.close()
    conn.close()



def selectUserData(id):
  try:
    conn = mariadb.connect(
      user=userDB,
      password=passwordDB,
      host=hostDB,
      port=portDB,
      database=nombreDB
    )

  except mariadb.Error as e:
    print(e)
    return None
  

  try:
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

  
  finally:
    conn.commit()
    cursor.close()
    conn.close()


def setIDs(idEvidencias, idEvidenciasAdicionales, tipoDocumento, idValidacion):
  
  try:
    conn = mariadb.connect(
      user=userDB,
      password=passwordDB,
      host=hostDB,
      port=portDB,
      database=nombreDB
    )
  except mariadb.Error as e:
    return 'error'

  try:
    cursor = conn.cursor()

    queryInfo = """UPDATE pki_validacion.documento_usuario AS du
      SET du.id_evidencias = ?,
      du.id_evidencias_adicionales = ?,
      du.tipo_documento = ?
      WHERE du.id = ?"""

    cursor.execute(queryInfo, (idEvidencias, idEvidenciasAdicionales, tipoDocumento, idValidacion,))

    return 'success'


  except mariadb.Error as e:
    print(e)
    return 'error'

  finally:
    conn.commit()
    cursor.close()
    conn.close()

#revalidation process


def selectValidations(query, *values):
  try:
    conn = mariadb.connect(
      user=userDB,
      password=passwordDB,
      host=hostDB,
      port=portDB,
      database=nombreDB
    )
  except mariadb.Error as e:
    print(e)
    return ()
  
  try:
    cursor = conn.cursor()

    cursor.execute(query, values)

    data = cursor.fetchall()

    return data

  except mariadb.Error as e:
    print(e)
    return ()

  finally:
    conn.commit()
    cursor.close()
    conn.close()

def select_time_logs(id_firmador: str):
      try:
        conn = mariadb.connect(
          user=userDB,
          password=passwordDB,
          host=hostDB,
          port=portDB,
          database=nombreDB
        )
      except mariadb.Error as e:
        print(e)
        return ()

      try:
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
      finally:
        conn.commit()
        cursor.close()
        conn.close()

def insert_time_log_record(id: str) -> int:
  try:
    conn = mariadb.connect(
      user=userDB,
      password=passwordDB,
      host=hostDB,
      port=portDB,
      database=nombreDB
    )
  except mariadb.Error as e:
    print(e)
    return 0

  try:
    cursor = conn.cursor()

    query = """
      INSERT INTO pki_validacion.log_tiempos
      (id_firmador, inicio_fecha)
      VALUES (?, NOW())
    """

    cursor.execute(query, (id,))
    return cursor.lastrowid

  except mariadb.Error as e:
    print(e)
    return 0

  finally:
    conn.commit()
    cursor.close()
    conn.close()

def updateDate(column: str, id: str) -> bool:
    try:
      conn = mariadb.connect(
        user=userDB,
        password=passwordDB,
        host=hostDB,
        port=portDB,
        database=nombreDB
      )
    except mariadb.Error as e:
      print(e)
      return False

    try:
      cursor = conn.cursor()
      query = f"UPDATE pki_validacion.log_tiempos as log SET {column} = NOW() WHERE log.id = {id}"
      cursor.execute(query, ())
      return cursor.rowcount > 0

    except mariadb.Error as e:
      print(e)
      return False

    finally:
      conn.commit()
      cursor.close()
      conn.close()


def updateSpeedtest(id: str, values: tuple) -> bool:
    try:
        conn = mariadb.connect(
          user=userDB,
          password=passwordDB,
          host=hostDB,
          port=portDB,
          database=nombreDB
        )
    except mariadb.Error as e:
        print(e)
        return False

    try:
        cursor = conn.cursor()
        query = (
            "UPDATE pki_validacion.log_tiempos as log "
            "SET velocidad_descarga = ?, tiempo_descarga = ?, velocidad_subida = ?, tiempo_subida = ?, velocidad_ping = ? "
            "WHERE log.id = ?"
        )
        cursor.execute(query, values + (id,))
        return cursor.rowcount > 0

    except mariadb.Error as e:
        print(e)
        return False

    finally:
        conn.commit()
        cursor.close()
        conn.close()

def updateBodySize(values: tuple) -> bool:
    try:
        conn = mariadb.connect(
          user=userDB,
          password=passwordDB,
          host=hostDB,
          port=portDB,
          database=nombreDB
        )
    except mariadb.Error as e:
        print(e)
        return False

    try:
        cursor = conn.cursor()
        query = (
            "UPDATE pki_validacion.log_tiempos as log "
            "SET peso_evidencias = ? "
            "WHERE log.id_firmador = ?"
        )
        cursor.execute(query, values)
        return cursor.rowcount > 0

    except mariadb.Error as e:
        print(e)
        return False

    finally:
        conn.commit()
        cursor.close()
        conn.close()
