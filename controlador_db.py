import mariadb
import base64
import socket
import requests

passwordDB = '30265611'
nombreDB = 'pki_validacion'
hostDB = 'localhost'
portDB = 3306
userDB = 'root'

def obtenerIpPrivada():
  hostname = socket.gethostname()
  direccionIp = socket.gethostbyname(hostname)
  return direccionIp

def obtenerIpPublica():
  ip = requests.get('https://api.ipify.org').text

  return ip

def obtenerUsuario(tabla,id):
  
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


def agregarEvidencias(columnas:tuple,tabla:str, valores:tuple, tablaActualizar:str, columnaActualizar:str, idParam):

  try:
    conn = mariadb.connect(
      user=userDB,
      password=passwordDB,
      host=hostDB,
      port=portDB,
      database=nombreDB
    )
  except mariadb.Error as e:
    return f"error en la query, error = {e}"

  try:
    cursor = conn.cursor()

    columnasStr:str = ','.join(columnas)
    placeHolder:list = []

    for columna in columnas:
      placeHolder.append('?')

    placeHolderStr:str = ','.join(placeHolder)

    queryEvidencias = f"INSERT INTO {tabla}({columnasStr}) VALUES ({placeHolderStr})"
    cursor.execute(queryEvidencias, valores)

    evidenciasID = cursor.lastrowid

    queryUpdate = f"UPDATE {tablaActualizar} SET {columnaActualizar} = {evidenciasID} WHERE id = {idParam}"
    cursor.execute(queryUpdate)

    return evidenciasID


  except mariadb.Error as e:
    print("error = ", e)

    with open('log.txt', "a") as file:
        file.write(f"error = {e}")

    return f"error = {e}"


  finally:
    conn.commit()
    cursor.close()
    conn.close()

def actualizarTipoDocumento(tablaActualizar:str,columnaActualizar:str,valorNuevo:any, idParam):

  try:
    conn = mariadb.connect(
      user=userDB,
      password=passwordDB,
      host=hostDB,
      port=portDB,
      database=nombreDB
    )
  except mariadb.Error as e:
    return f"error en la query, error = {e}"

  try:
    cursor = conn.cursor()


    queryUpdate = f"UPDATE {tablaActualizar} SET {columnaActualizar} = '{valorNuevo}' WHERE id = {idParam}"
    cursor.execute(queryUpdate)

    return 'actualizada data'

  except mariadb.Error as e:
    print("error = ", e)

    with open('log.txt') as f:
      f.write(f"error = {e}\n")
    return f"error = {e}"

  finally:
    conn.commit()
    cursor.close()
    conn.close()

def actualizarData(tablaActualizar:str,columnaActualizar:str,valorNuevo:any, idParam):

  try:
    conn = mariadb.connect(
      user=userDB,
      password=passwordDB,
      host=hostDB,
      port=portDB,
      database=nombreDB
    )
  except mariadb.Error as e:
    return f"error en la query, error = {e}"

  try:
    cursor = conn.cursor()


    queryUpdate = f"UPDATE {tablaActualizar} SET {columnaActualizar} = {valorNuevo} WHERE id = {idParam}"
    cursor.execute(queryUpdate)

    return 'actualizada data'

  except mariadb.Error as e:
    print("error = ", e)
    return f"error = {e}"

  finally:
    conn.commit()
    cursor.close()
    conn.close()


def insertTabla(columnas: tuple, tabla:str, valores: tuple):

  try:
    conn = mariadb.connect(
      user=userDB,
      password=passwordDB,
      host=hostDB,
      port=portDB,
      database=nombreDB
    )
  except mariadb.Error as e:
    return f"error en la query, error = {e}"

  try:
    cursor = conn.cursor()

    columnasStr:str = ','.join(columnas)
    placeHolder:list = []

    for columna in columnas:
      placeHolder.append('?')

    placeHolderStr:str = ','.join(placeHolder)


    queryInfo = f"INSERT INTO {tabla} ({columnasStr}) VALUES ({placeHolderStr})"
    cursor.execute(queryInfo,valores)

    documentoUsuarioID = cursor.lastrowid

    return documentoUsuarioID

  except mariadb.Error as e:

    print("error =", e)
    return f"error = {e}"

  finally:
    conn.commit()
    cursor.close()
    conn.close()


def comprobarProceso(id):

  try:
    conn = mariadb.connect(
      # user=userDB,
      user=userDB,
      password=passwordDB,
      # host=hostDB,
      host=hostDB,
      port=portDB,
      database=nombreDB
    )
  except mariadb.Error as e:
    return f"error en la query, error = {e}"

  try:
    cursor = conn.cursor()

    queryInfo = f'SELECT count(ea.estado_verificacion) FROM documento_usuario as du INNER JOIN evidencias_adicionales ea ON ea.id=du.id_evidencias_adicionales WHERE (ea.estado_verificacion="verificado" OR ea.estado_verificacion="Iniciando segunda validación" OR ea.estado_verificacion="Procesando segunda validación") and id_usuario_efirma={id}'
    cursor.execute(queryInfo)

    comprobacion = cursor.fetchall()

    if(len(comprobacion) >= 1):
      return comprobacion[-1]
    else:
      return None

  except mariadb.Error as e:

    print("error =", e)

  finally:
    conn.commit()
    cursor.close()
    conn.close()
