from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin
from reconocimiento import reconocerRostro, pruebaVida
import controlador_db
from validar_duplicado import comprobarDuplicado
from utilidades import leerDataUrl, cv2Blob
from ocr import imagenOCR, validarOCR

app = Flask(__name__)
cors = CORS(app, resources={
  r"/*":{
    "origins":"*"
  }
})
app.config['CORS_HEADER'] = 'Content-type'

@app.route('/obtener-firmador/<id>', methods=['GET'])
def obtenerFirmador(id):
  return jsonify({
    "dato": {
        "id": 11,
        "firmaElectronicaId": 11,
        "nombre": "BENITO",
        "apellido": "OTERO",
        "correo": "benito.otero.carreira@gmail.com",
        "tipoDocumento": "CEDULA",
        "documento": "423105",
        "evidenciasCargadas": False,
        "enlaceTemporal": "nhxNYeTyF8",
        "ordenFirma": 1,
        "fechaCreacion": "2023-10-07T11:13:52-05:00"
    }
})

#rutas para el front
@app.route('/ocr', methods=['POST'])
def verificarDocumento():

  tipoDocumento = request.args.get('tipoDocumento')
  ladoDocumento = request.args.get('ladoDocumento')

  print(tipoDocumento, ladoDocumento)

  documento = request.get_json()

  documentoData = documento['imagen'][ladoDocumento]

  documentoOCR = imagenOCR(documentoData, tipoDocumento, ladoDocumento)

  print(documentoOCR)

  validacion = validarOCR(documentoOCR, tipoDocumento, ladoDocumento)

  return jsonify({'validacion':validacion})


@app.route('/validacion-vida', methods=['POST'])
def validacionVida():

  data = request.get_json()

  imagenes = data['imagenes']

  imagenBaseContador = 0
  imagenComaparacionContador = 1

  porcentaje = 0

  while imagenBaseContador <= 7 and imagenComaparacionContador <= 8:

    print(f"vuelta: {imagenComaparacionContador}")
    imagenBase = imagenes[imagenBaseContador]
    imagenComparacion = imagenes[imagenComaparacionContador]

    imagenBaseData = leerDataUrl(imagenBase)
    imagenComparacionData = leerDataUrl(imagenComparacion)

    comparacion = pruebaVida(imagenBaseData, imagenComparacionData)

    coincidencia = comparacion[0]

    resultado = comparacion[1]

    porcentaje = porcentaje + resultado

    print(comparacion)
    print(f'{porcentaje}%')

    imagenBaseContador = imagenBaseContador + 1
    imagenComaparacionContador = imagenComaparacionContador + 1


  return jsonify({'porcentajePruebaVida':porcentaje})

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
  ipPrivada = controlador_db.obtenerIpPrivada()
  ipPublica = controlador_db.obtenerIpPublica()
  dispositivo = request.form.get('dispositivo')
  navegador = request.form.get('navegador')
  latitud = request.form.get('latitud')
  longitud = request.form.get('longitud')
  hora = request.form.get('hora')
  fecha = request.form.get('fecha')

  #evidencias usuario
  fotoPersona = request.form.get('foto_persona')
  anverso = request.form.get('anverso')
  reverso = request.form.get('reverso')

  #leer data url
  fotoPersonaData = leerDataUrl(fotoPersona)
  anversoData = leerDataUrl(anverso)
  reversoData = leerDataUrl(reverso)

  print(fotoPersonaData, anversoData, reversoData)

  reconocer = reconocerRostro(fotoPersonaData, anversoData)
  coincidencia = reconocer[0]
  estadoVericacion = reconocer[1]
  anversoOrientado = reconocer[2]

  fotoPersonaBlob = cv2Blob(fotoPersonaData)
  reversoBlob = cv2Blob(reversoData)


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
  valoresEvidencias = (anversoOrientado, reversoBlob, fotoPersonaBlob, '', '')
  evidenciasUsuario = controlador_db.agregarDocumento(columnasEvidencias, tablaEvidencias, valoresEvidencias)

  #tabla evidencias adicionales

  columnasEvidenciasAdicionales = ('estado_verificacion', 'dispositivo', 'navegador', 'ip_publica', 'ip_privada', 'latitud', 'longitud', 'hora', 'fecha')
  tablaEvidenciasAdicionales = 'evidencias_adicionales'
  valoresEvidenciasAdicionales = (estadoVericacion, dispositivo, navegador, ipPublica, ipPrivada, latitud, longitud, hora,fecha)
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

  ipPrivada = controlador_db.obtenerIpPrivada()
  ipPublica = controlador_db.obtenerIpPublica()

  tablaActualizar = 'documento_usuario'

  #evidencias usuario
  fotoPersona = request.form.get('foto_persona')
  anverso = request.form.get('anverso')
  reverso = request.form.get('reverso')

  #leer data url
  fotoPersonaData = leerDataUrl(fotoPersona)
  anversoData = leerDataUrl(anverso)
  reversoData = leerDataUrl(reverso)

  print(fotoPersonaData, anversoData, reversoData)

  reconocer = reconocerRostro(fotoPersonaData, anversoData)
  coincidencia = reconocer[0]
  estadoVericacion = reconocer[1]
  anversoOrientado = reconocer[2]

  fotoPersonaBlob = cv2Blob(fotoPersonaData)
  reversoBlob = cv2Blob(reversoData)


  columnasEvidencias = ('anverso_documento','reverso_documento','foto_usuario','estado_verificacion','tipo_documento')
  tablaEvidencias = 'evidencias_usuario'
  valoresEvidencias = (anversoOrientado, reversoBlob, fotoPersonaBlob, '', '')
  columnaActualizarEvidencias = 'id_evidencias'
  evidencias = controlador_db.agregarEvidencias(columnasEvidencias, tablaEvidencias,valoresEvidencias,tablaActualizar,columnaActualizarEvidencias, id)

  #tabla evidencias adicionales

  columnasEvidenciasAdicionales = ('estado_verificacion','dispositivo','navegador','ip_publica', 'ip_privada','latitud','longitud','hora','fecha')
  tablaEvidenciasAdicionales = 'evidencias_adicionales'
  valoresEvidenciasAdicionales = (estadoVericacion, dispositivo, navegador, ipPublica, ipPrivada, latitud, longitud, hora,fecha)
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