import mariadb
import base64
import socket

passwordDB = '30265611'
nombreDB = 'pki_validacion_identidad'

def obtenerIP():
  hostname = socket.gethostname()
  direccionIp = socket.gethostbyname(hostname)
  return direccionIp

def obtenerUsuario(tabla,id):
  
  conn = mariadb.connect(
    user='root',
    password=passwordDB,
    host='localhost',
    port=3306,
    database=nombreDB
  )

  cursor = conn.cursor()

  cursor.execute(f'SELECT * FROM {tabla} WHERE id = {id}')

  usuario = cursor.fetchone()

  cursor.close()
  conn.close()

  return usuario

  cursor.close()
  conn.close()


def agregarVerificacion(columnas:tuple,tabla:str, valores:tuple, tablaActualizar:str, columnaActualizar:str, idParam):

  try:
    conn = mariadb.connect(
      user='root',
      password=passwordDB,
      host='localhost',
      port=3306,
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

    return 'agregada y actualizada'


  except mariadb.Error as e:
    return f"error = {e}"

  finally:
    conn.commit()
    cursor.close()
    conn.close()

def actualizarData(tablaActualizar:str,columnaActualizar:str,valorNuevo:any, idParam):

  try:
    conn = mariadb.connect(
      user='root',
      password=passwordDB,
      host='localhost',
      port=3306,
      database=nombreDB
    )
  except mariadb.Error as e:
    return f"error en la query, error = {e}"

  try:
    cursor = conn.cursor()


    queryUpdate = f"UPDATE {tablaActualizar} SET {columnaActualizar} = '{valorNuevo}' WHERE id = {idParam}"
    cursor.execute(queryUpdate)

    return 'actualizado tipo documento'

  except mariadb.Error as e:
    return f"error = {e}"

  finally:
    conn.commit()
    cursor.close()
    conn.close()


def agregarDocumento(columnas: tuple, tabla:str, valores: tuple):

  try:
    conn = mariadb.connect(
      user='root',
      password=passwordDB,
      host='localhost',
      port=3306,
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

    return 'agregado'

  except mariadb.Error as e:
    return f"error = {e}"

  finally:
    conn.commit()
    cursor.close()
    conn.close()


# def obtenerUltimoId(tabla:str):
#   try:
#     conn = mariadb.connect(
#       user='root',
#       password=passwordDB,
#       host='localhost',
#       port=3306,
#       database='pki_validacion_identidad'
#     )
#   except mariadb.Error as e:
#     return f"error en la query, error = {e}"

#   try:
#     cursor = conn.cursor()

#     query:str = f'select last_insert_id() from {tabla}'

#     cursor.execute(query)

#     id = cursor.fetchone()

#     return id
#   except mariadb.Error as e:
#     return f"error = {e}"

#   finally:
#     conn.commit()
#     cursor.close()
#     conn.close()