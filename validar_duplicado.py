import controlador_db

def comprobarDuplicado(nombres:str, apellidos:str, anverso,reverso):
  filas:list = controlador_db.obtenerTodos('documento_usuario')

  global duplicado
  duplicado = False

  for fila in filas:
    nombresComparacion:str = fila[1]
    apellidosComparacion:str = fila[2]
    anversoComparacion = fila[3]
    reversoComparacion = fila[4]
    if anversoComparacion == anverso and reversoComparacion == reverso and nombres == nombresComparacion and apellidos == apellidosComparacion:
      duplicado = True

  return duplicado