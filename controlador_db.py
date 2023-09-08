import mariadb

def obtenerTodos(tabla:str) -> list:
  conn = mariadb.connect(
    user='root',
    password="30265611",
    host='localhost',
    port=3306,
    database='pki_validacion_identidad'
  )
  cursor = conn.cursor()

  cursor.execute(f'SELECT * FROM {tabla}')

  filas:list = cursor.fetchall()

  cursor.close()
  conn.close()

  return filas

def obtenerSolo(tabla:str, condicion:str):
  try:
    conn = mariadb.connect(
      user='root',
      password="30265611",
      host='localhost',
      port=3306,
      database='pki_validacion_identidad'
    )
  except mariadb.Error as e:
    return f'error = {e}'

  try:
    cursor = conn.cursor()

    query = f'SELECT * FROM {tabla} WHERE {condicion}'

    cursor.execute(query)

    usuario = cursor.fetchone()

    if usuario is not None:
      documento = usuario[3]
      return documento
    else:
      return ''


  except mariadb.Error as e:
    print(e)
    return ''

  finally:
    cursor.close()
    conn.close()


def agregarDocumento(columnas: tuple, tabla:str, valores: tuple) -> str:

  try:
    conn = mariadb.connect(
      user='root',
      password="30265611",
      host='localhost',
      port=3306,
      database='pki_validacion_identidad'
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


    query:str = f'INSERT IGNORE INTO {tabla} ({columnasStr}) VALUES ({placeHolderStr})'

    cursor.execute(query, valores)

    return "usuario agregado correctamente"
  except mariadb.Error as e:
    return f"error = {e}"

  finally:
    conn.commit()
    cursor.close()
    conn.close()