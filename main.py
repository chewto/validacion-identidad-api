import cv2
from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin
import numpy
from reconocimiento import reconocerRostro
import controlador_db
from validar_duplicado import comprobarDuplicado

app = Flask(__name__)
cors = CORS(app, resources={
  r"/*":{
    "origins":"*"
  }
})
app.config['CORS_HEADER'] = 'Content-type'

@app.route("/agregar-documento", methods=['POST'])
def agregarCedula():
  nombres = request.form.get('nombres')
  apellidos = request.form.get('apellidos')
  numeroDocumento = request.form.get('numero_documento')
  anverso = request.files['anverso']
  reverso = request.files['reverso']

  nombres = nombres.lower()
  apellidos = apellidos.lower()
  anversoBlob = anverso.stream.read()
  reversoBlob = reverso.stream.read()

  if len(anversoBlob) >= 200 and len(reversoBlob) >= 200:

    duplicado = comprobarDuplicado('documento_usuario', numeroDocumento)

    if duplicado != numeroDocumento:
      columnasQuery:tuple = ('nombres', 'apellidos', 'numero_documento', 'anverso_documento', 'reverso_documento')
      tablaQuery:str = 'documento_usuario'
      valoresQuery:tuple = (nombres, apellidos, numeroDocumento, anversoBlob, reversoBlob,)

      mensaje:str = controlador_db.agregarDocumento(columnasQuery, tablaQuery, valoresQuery)

      return jsonify({"mensaje":mensaje, "duplicado":duplicado})
    
    if duplicado == numeroDocumento:
      return jsonify({"mensaje":"el documento ya se encuentra registrado", "duplicado":duplicado})


@app.route("/verificacion-rostro-rostro", methods=['POST'])
def verificacion():

  archivo = request.files['file']

  obtenerImagenSnippet = '''
for row in filas:
  b = io.BytesIO(row[1])
  imagenes.append(b)

print(imagenes)
'''

  comparacion = reconocerRostro(archivo, 'usuarios', obtenerImagenSnippet);

  reconocido = comparacion[1]

  print(comparacion[1])

  return jsonify({"mensaje":"realizado con exito" , "reconocido": reconocido})


@app.route("/verificacion-rostro-documento/<id>", methods=['POST'])
def verfificacionRostroDocumento(id):

# #   snippet = '''

# # for row in filas:
# #   b = io.BytesIO(row[5])
# #   imagenes.append(b)
# #   nombre = row[1]
# #   apellido = row[2]
# #   nombreCompleto = f"{nombre} {apellido}"
# #   nombres.append(nombreCompleto)

# # '''

#   if len(anversoBlob) >= 200 and len(reversoBlob) >= 200 and len(fotoPersonaBlob) >= 200:
#     # duplicados = comprobarDuplicado('documento_usuario',numeroDocumento, tipoDocumento)

#     # print(duplicados)

#     # documentosDuplicados = 0
#     # tipoDocumentoDuplicados = 0
  
#     # for duplicado in duplicados:
#     #   if(duplicado['documento'] == numeroDocumento):
#     #     documentosDuplicados = documentosDuplicados + 1
#     #     print(documentosDuplicados)
      
#     #   if(duplicado['tipoDocumento'] == tipoDocumento):
#     #     tipoDocumentoDuplicados = tipoDocumentoDuplicados + 1
#     #     print(tipoDocumentoDuplicados)


#     # comparacion = reconocerRostro(fotoPersona, anverso)
#     # reconocido = comparacion[1]
#     # coincidencia = comparacion[0]

#     mensaje= controlador_db.agregarDocumento(('nombres','apellidos','numero_documento','tipo_documento','email','id_evidencias','id_evidencias_adicionales'),'documento_usuario',(nombres, apellidos, numeroDocumento, tipoDocumento, email, 0, 0))


#     return jsonify({"status": mensaje})

#     # if len(duplicados) >= 1:
#     #   if(documentosDuplicados >= 1 and tipoDocumentoDuplicados >= 1):

#     #     comparacion = reconocerRostro(fotoPersona, anverso)
#     #     reconocido = comparacion[1]
#     #     coincidencia = comparacion[0]

#     #     query = f'numero_documento = "{numeroDocumento}" AND tipo_documento = "{tipoDocumento}"'
#     #     info = controlador_db.obtenerUsuario('documento_usuario', query)

#     #     idEvidencias = info[0]['id_evidencias']

#     #     queryActualizar = f'UPDATE evidencias_usuario  SET foto_usuario = {fotoPersonaBlob}  WHERE id = {idEvidencias}'
#     #     actualizar = controlador_db.actualizarEstado(queryActualizar)

#     #     return jsonify({"coincidencia_documento_rostro":reconocido, "estado_verificacion":reconocido, "status":"documento previamente registrado"})

#     #   if(documentosDuplicados >= 1 and  tipoDocumentoDuplicados <= 0):

#     #     comparacion = reconocerRostro(fotoPersona, anverso)
#     #     reconocido = comparacion[1]
#     #     coincidencia = comparacion[0]

#     #     mensaje= controlador_db.agregarDocumento(anversoBlob, reversoBlob, fotoPersonaBlob, nombres, apellidos, numeroDocumento, tipoDocumento, reconocido)

#     #     return jsonify({"coincidencia_documento_rostro":reconocido, "estado_verificacion":reconocido, "status": 'agregado satisfactoriamente desde b'})

    return jsonify({'mensaje':'blob invalido'})



@app.route('/validacion-vida', methods=['POST'])
def validacionVida():

  imagenes = request.get_json()

  print(imagenes)


  return jsonify({'probando':imagenes})

@app.route('/obtener-firmador/<id>', methods=['GET'])
def obtenerFirmador(id):
  return jsonify({'firmaElectronicaId':id, "nombre":"prueba", "apellido": "prueba2", "correo":"prueba3", "tipoDocumento": "prueba4", "documento":"prueba5", "enlaceTemporal":"prueba6", "ordenFirma":0})

@app.route('/obtener-evidencias', methods=['GET'])
def obtenerEvidencias():

  id = request.args.get('id')
  tipo = request.args.get('tipo')

  usuario = controlador_db.obtenerUsuario('documento_usuario', id)

  idEvidencias = usuario[6]
  idEvidenciasAdicionales = usuario[7]

  return jsonify({'idEvidencias':idEvidencias, 'idEvidenciasAdicionales':idEvidenciasAdicionales, "tipo": tipo})

@app.route('/validacion-identidad-tipo-3', methods=['POST'])
def validacionIdentidadTipo3():

  id = request.args.get('id')
  idUsuario = request.args.get('idUsuario')
  idUsuario = int(idUsuario)
  tipo = request.args.get('tipo')

  #documento usuario
  nombres = request.form.get('nombres')
  apellidos = request.form.get('apellidos')
  email = request.form.get('email')
  tipoDocumento = request.form.get('tipo_documento')
  documento = request.form.get('numero_documento')

  #evidencias adicionales
  IP = controlador_db.obtenerIP()
  dispositivo = request.form.get('dispositivo')
  navegador = request.form.get('navegador')
  latitud = request.form.get('latitud')
  longitud = request.form.get('longitud')
  hora = request.form.get('hora')
  fecha = request.form.get('fecha')

  #evidencias usuario
  fotoPersona = request.files['foto_persona']
  anverso = request.files['anverso']
  reverso = request.files['reverso']

  #streams
  fotoPersonaBlob = fotoPersona.stream.read()
  anversoBlob = anverso.stream.read()
  reversoBlob = reverso.stream.read()


  reconocer = reconocerRostro(fotoPersona, anverso)
  coincidencia = reconocer[0]
  estadoVericacion = reconocer[1]

  #normalizacion
  nombres = nombres.lower()
  apellidos = apellidos.lower()
  email = email.lower()
  tipoDocumento = tipoDocumento.lower()
  documento = documento.lower()

  #creando documento_usuario
  columnasDocumentoUsuario = ('nombres', 'apellidos', 'numero_documento', 'tipo_documento', 'email', 'id_evidencias', 'id_evidencias_adicionales', 'id_usuario_efirma')
  tablaDocumento = 'documento_usuario'
  valoresDocumento = (nombres, apellidos, documento, tipoDocumento, email, 0, 0, idUsuario)
  documentoUsuario = controlador_db.agregarDocumento(columnasDocumentoUsuario, tablaDocumento, valoresDocumento)


  tablaActualizar = 'documento_usuario'

  #tabla evidencias 
  columnasEvidencias = ('anverso_documento', 'reverso_documento', 'foto_usuario', 'estado_verificacion', 'tipo_documento')
  tablaEvidencias = 'evidencias_usuario'
  valoresEvidencias = (anversoBlob, reversoBlob, fotoPersonaBlob, '', '')
  evidenciasUsuario = controlador_db.agregarDocumento(columnasEvidencias, tablaEvidencias, valoresEvidencias)

  #tabla evidencias adicionales

  columnasEvidenciasAdicionales = ('estado_verificacion', 'dispositivo', 'navegador', 'ip', 'latitud', 'longitud', 'hora', 'fecha')
  tablaEvidenciasAdicionales = 'evidencias_adicionales'
  valoresEvidenciasAdicionales = (estadoVericacion, dispositivo, navegador, IP, latitud, longitud, hora,fecha)
  evidenciasAdicionales = controlador_db.agregarDocumento(columnasEvidenciasAdicionales, tablaEvidenciasAdicionales, valoresEvidenciasAdicionales)


  columnaIdEvidencias = 'id_evidencias'
  columnaIdEvidenciasA = 'id_evidencias_adicionales'

  actualizarIdEvidencias = controlador_db.actualizarData(tablaDocumento,columnaIdEvidencias,evidenciasUsuario, documentoUsuario )
  actualizarIdEvidenciasA = controlador_db.actualizarData(tablaDocumento,columnaIdEvidenciasA,evidenciasAdicionales, documentoUsuario )

  # #actualizar documento usuario
  # tipoDocumento = request.form.get('tipo_documento')
  # tipoDocumento = tipoDocumento.lower()

  # columnaTipoDocumento = 'tipo_documento'
  # actualizarTipoDocumento = controlador_db.actualizarData(tablaActualizar, columnaTipoDocumento, tipoDocumento, documentoUsuario)

  return jsonify({"idValidacion":documentoUsuario, "idUsuario":idUsuario, "coincidenciaDocumentoRostro":coincidencia, "estadoVerificacion":estadoVericacion})


@app.route('/validacion-identidad-tipo-1', methods=['POST'])
def validacionIdentidadTipo1():

  id = request.args.get('id')
  idUsuario = request.args.get('idUsuario')
  tipo = request.args.get('tipo')

  dispositivo = request.form.get('dispositivo')
  navegador = request.form.get('navegador')
  latitud = request.form.get('latitud')
  longitud = request.form.get('longitud')
  hora = request.form.get('hora')
  fecha = request.form.get('fecha')
  fotoPersona = request.files['foto_persona']
  anverso = request.files['anverso']
  reverso = request.files['reverso']

  IP = controlador_db.obtenerIP()

  tablaActualizar = 'documento_usuario'

  #tabla evidencias
  
  fotoPersonaBlob = fotoPersona.stream.read()
  anversoBlob = anverso.stream.read()
  reversoBlob = reverso.stream.read()
  print(fotoPersonaBlob)
  reconocer = reconocerRostro(fotoPersona, anverso)
  coincidencia = reconocer[0]
  estadoVericacion = reconocer[1]


  columnasEvidencias = ('anverso_documento','reverso_documento','foto_usuario','estado_verificacion','tipo_documento')
  tablaEvidencias = 'evidencias_usuario'
  valoresEvidencias = (anversoBlob, reversoBlob, fotoPersonaBlob, '', '')
  columnaActualizarEvidencias = 'id_evidencias'
  evidencias = controlador_db.agregarEvidencias(columnasEvidencias, tablaEvidencias,valoresEvidencias,tablaActualizar,columnaActualizarEvidencias, id)

  #tabla evidencias adicionales

  columnasEvidenciasAdicionales = ('estado_verificacion','dispositivo','navegador','ip','latitud','longitud','hora','fecha')
  tablaEvidenciasAdicionales = 'evidencias_adicionales'
  valoresEvidenciasAdicionales = (estadoVericacion, dispositivo, navegador, IP, latitud, longitud, hora,fecha)
  columnaActualizarEvidenciasAdicionales = 'id_evidencias_adicionales'
  evidenciasAdicionales = controlador_db.agregarEvidencias(columnasEvidenciasAdicionales, tablaEvidenciasAdicionales,valoresEvidenciasAdicionales,tablaActualizar,columnaActualizarEvidenciasAdicionales, id)

  #actualizar documento usuario
  tipoDocumento = request.form.get('tipo_documento')
  tipoDocumento = tipoDocumento.lower()

  columnaTipoDocumento = 'tipo_documento'
  actualizarTipoDocumento = controlador_db.actualizarTipoDocumento(tablaActualizar, columnaTipoDocumento, tipoDocumento, id)

  return jsonify({"coincidenciaDocumentoRostro":coincidencia, "estadoVerificacion":estadoVericacion})
  
if __name__ == "__main__":
  app.run(debug=True,host="0.0.0.0", port=4000)