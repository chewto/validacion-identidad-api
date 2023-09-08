import controlador_db

def comprobarDuplicado(tabla:str,numeroDocumento:str):

  condicion = f'numero_documento = {numeroDocumento}'

  duplicado = controlador_db.obtenerSolo(tabla, condicion)

  return duplicado
