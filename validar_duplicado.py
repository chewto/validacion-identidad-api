import controlador_db

def comprobarDuplicado(tabla:str,numeroDocumento:str, tipoDocumento:str):

  condicion = f'numero_documento = {numeroDocumento}'

  duplicado = controlador_db.obtenerDocumentoUsuario(tabla, condicion)

  return duplicado
