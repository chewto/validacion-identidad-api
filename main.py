import subprocess
import time
from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin
from reconocimiento import obtencionEncodings, orientacionImagen, reconocimiento, obtenerFrames, deteccionRostro, determinarMovimiento
import controlador_db
from utilidades import boolString, leerFileStorage, leerDataUrl, cv2Blob, recorteData, normalizarTexto, stringBool
from barcode import isValid, uploadBarcodeFile, readBarcode, barcodeDTO
from ocr import busquedaData, extraerPorcentaje,validarLadoDocumento, ocr, validacionOCR, comparacionOCR
import os

app = Flask(__name__)

carpetaPruebaVida = "./evidencias-vida"

cors = CORS(app, resources={
  r"/*":{
    "origins":"*"
  }
})
app.config['CORS_HEADER'] = 'Content-type'



@app.route('/', methods=['GET'])
def health():

  if(request.method == 'GET'):
    return jsonify({'activo': True})

@app.route('/ocr-anverso', methods=['POST'])
def verificarAnverso():

    documento = request.get_json()

    imagenPersona = documento['imagenPersona']

    imagenDocumento = documento['imagen']

    ladoDocumento = documento['ladoDocumento']

    tipoDocumento = documento['tipoDocumento']

    documentoData = leerDataUrl(imagenDocumento)

    personaData = leerDataUrl(imagenPersona)
    
    nombre = documento['nombre']

    nombre = normalizarTexto(nombre)

    apellido = documento['apellido']

    apellido = normalizarTexto(apellido)

    numeroDocumento = documento['documento']

    selfieOrientada, carasImagenPersona = orientacionImagen(personaData)
    documentoOrientado, carasImagenDocumento = orientacionImagen(documentoData)

    validarLadoPre = validarLadoDocumento(tipoDocumento, ladoDocumento, documentoOrientado, preprocesado=True)
    validarLadoSencillo = validarLadoDocumento(tipoDocumento, ladoDocumento, documentoOrientado, preprocesado=False)

    totalValidacionLado = validarLadoPre + validarLadoSencillo

    ladoValido = False

    if(totalValidacionLado >=1):
      ladoValido = True

    documentoOCRSencillo = ocr(documentoOrientado, 'sencillo')

    documentoOCRPre = ocr(documentoOrientado, 'preprocesado')

    #ocr sencillo
    nombreOCR, porcentajeNombre = validacionOCR(documentoOCRSencillo, nombre)
    apellidoOCR, porcentajeApellido = validacionOCR(documentoOCRSencillo, apellido)
    numeroDocumentoOCR, porcentajeDocumento = validacionOCR(documentoOCRSencillo, numeroDocumento)

    nombrePreOCR, porcentajeNombrePre = validacionOCR(documentoOCRPre, nombre)
    apellidoPreOCR, porcentajeApellidoPre = validacionOCR(documentoOCRPre, apellido)
    numeroDocumentoPreOCR, porcentajeDocumentoPre = validacionOCR(documentoOCRPre, numeroDocumento)

    nombreComparado, porcentajeNombreComparado = comparacionOCR(porcentajePre=porcentajeNombrePre, porcentajeSencillo=porcentajeNombre, ocrPre=nombrePreOCR, ocrSencillo=nombreOCR)
    apellidoComparado, porcentajeApellidoComparado = comparacionOCR(porcentajePre=porcentajeApellidoPre, porcentajeSencillo=porcentajeApellido, ocrPre=apellidoPreOCR, ocrSencillo=apellidoOCR)
    documentoComparado, porcentajeDocumentoComparado = comparacionOCR(porcentajePre=porcentajeDocumentoPre, porcentajeSencillo=porcentajeDocumento, ocrPre=numeroDocumentoPreOCR, ocrSencillo=numeroDocumentoOCR)

    coincidencia = False

    if(len(carasImagenPersona) >= 1 and len(carasImagenDocumento) >= 1):
      coincidencia = True

    return jsonify({
      'ocr': {
          'nombreOCR': nombreComparado,
          'apellidoOCR': apellidoComparado,
          'documentoOCR': documentoComparado
      },
      'porcentajes': {
          'porcentajeNombreOCR': porcentajeNombreComparado,
          'porcentajeApellidoOCR': porcentajeApellidoComparado,
          'porcentajeDocumentoOCR': porcentajeDocumentoComparado
        },
      'rostro': coincidencia,
      'ladoValido': ladoValido
    })

@app.route("/test-route", methods=["POST"])
def test():

  data = request.get_json()

  documentReverso = data['reverso']

  uploadedBarcodeFile = uploadBarcodeFile(documentReverso, fileName="reverso.jpeg")

  if(uploadedBarcodeFile == None):
    return {
        "codigoAFIS": '',
        "huella": '',
        "numeroDocumento": '',
        "primerNombre": '',
        "segundoNombre": '',
        "primerApellido": '',
        "segundoApellido": '',
        "genero": '',
        "anhoNacimiento": '',
        "mesNacimiento": '',
        "diaNacimiento": '',
        "codigoMunicipio": '',
        "codigoDepartamento": '',
        "tipoSangre": ''
    }

  barcodeData = readBarcode(uploadedBarcodeFile)

  organizedData = barcodeDTO(barcodeData)

  name = organizedData['primerNombre']
  lastName = organizedData['primerApellido']
  document = organizedData['numeroDocumento']

  existName = isValid('MARA', name)
  existLastname = isValid('CRZ', lastName)
  existDocument = isValid('100531627', document)

  return jsonify({"name":existName, "lastName":existLastname, "document":existDocument})


#rutas para el front
@app.route('/ocr-reverso', methods=['POST'])
def verificarReverso():

    documento = request.get_json()

    imagenDocumento = documento['imagen']

    ladoDocumento = documento['ladoDocumento']

    tipoDocumento = documento['tipoDocumento']

    lecturaCodigoBarras = documento['lectura']

    documentoData = leerDataUrl(imagenDocumento)
    
    nombre = documento['nombre']

    nombre = normalizarTexto(nombre)

    apellido = documento['apellido']

    apellido = normalizarTexto(apellido)

    numeroDocumento = documento['documento']

    # documentoOCRSencillo = ocr(documentoData, 'sencillo')

    # documentoOCRPre = ocr(documentoData, 'preprocesado')

    # busquedaSencillo = busquedaData(documentoOCRSencillo, nombre, apellido, numeroDocumento)
    # busquedaPre = busquedaData(documentoOCRPre, nombre, apellido, numeroDocumento)


    # print(busquedaSencillo, busquedaPre)
    validarLadoPre = validarLadoDocumento(tipoDocumento, ladoDocumento, documentoData, preprocesado=True)
    validarLadoSencillo = validarLadoDocumento(tipoDocumento, ladoDocumento, documentoData, preprocesado=False)

    totalValidacion = validarLadoPre + validarLadoSencillo

    ladoValido = False

    if(totalValidacion >= 1):
      ladoValido = True

    if((lecturaCodigoBarras != 'EFIRMA-QR') or
      (lecturaCodigoBarras == 'EFIRMA-QR' and (tipoDocumento == "Pasaporte"))
      ):

      return jsonify({
          "codigoBarra":{
            'reconocido': 'false',
            'nombre':'false',
            'apellido':'false',
            'documento':'false'
          },
          'ladoValido': ladoValido
        })

    uploadedBarcodeFile = uploadBarcodeFile(imagenDocumento, fileName="reverso.jpeg")

    if(uploadedBarcodeFile == None):

      return jsonify({
        "codigoBarra":{
          'reconocido': 'false',
          'nombre':'false',
          'apellido':'false',
          'documento':'false'
        },
        'ladoValido': ladoValido
      })

    barcodeData = readBarcode(uploadedBarcodeFile)

    organizedData = barcodeDTO(barcodeData)

    bcName = organizedData['primerNombre']
    bcLastName = organizedData['primerApellido']
    bcDocument = organizedData['numeroDocumento']

    existName = isValid(bcName,nombre)
    existLastname = isValid(bcLastName,apellido)
    existDocument = isValid(bcDocument,numeroDocumento)

    existName = boolString(existName)
    existLastname = boolString(existLastname)
    existDocument = boolString(existDocument)

    return jsonify({
      "codigoBarra":{
        'reconocido': 'true',
        'nombre':existName,
        'apellido':existLastname,
        'documento':existDocument
      },
      'ladoValido': ladoValido
    })


@app.route('/proveedor-lector', methods=['GET'])
def proveedorLector():
  entityId = request.args.get('entityId')

  selectProvider = controlador_db.selectProvider(id=entityId)

  validationProvider = selectProvider

  return jsonify({"proveedor": validationProvider})

@app.route('/obtener-usuario', methods=['GET'])
def obtenerUsuario():

  id = request.args.get('id')

  usuario = controlador_db.obtenerUsuario('documento_usuario',id)

  return jsonify({'dato':usuario})


@app.route('/obtener-evidencias', methods=['GET'])
def obtenerEvidencias():

  id = request.args.get('id')
  tipo = request.args.get('tipo')

  usuario = controlador_db.obtenerUsuario('documento_usuario', id)

  idEvidencias = usuario[6]
  idEvidenciasAdicionales = usuario[7]

  return jsonify({'idEvidencias':idEvidencias, 'idEvidenciasAdicionales':idEvidenciasAdicionales, "tipo": tipo})

@app.route('/comprobacion-proceso', methods=['GET'])
def comprobacionProceso():
    idUsuarioEFirma = request.args.get('idUsuarioEFirma')

    peticionProceso = controlador_db.comprobarProceso(idUsuarioEFirma)

    if peticionProceso:
        return jsonify(peticionProceso)
    else:
        return jsonify({"estado":""})

@app.route('/validacion-identidad-tipo-3', methods=['POST'])
def validacionIdentidadTipo3():


  id = request.args.get('id')
  idUsuario = request.args.get('idUsuario')
  idUsuario = int(idUsuario)
  tipo = request.args.get('tipo')

  idCarpetaEntidad = request.form.get('carpeta_entidad_prueba_vida')
  idCarpetaUsuario = request.form.get('carpeta_usuario_prueba_vida')
  movimiento = request.form.get('movimiento_prueba_vida')

  #documento usuario
  nombres = request.form.get('nombres')
  apellidos = request.form.get('apellidos')
  email = request.form.get('email')
  tipoDocumento = request.form.get('tipo_documento')
  documento = request.form.get('numero_documento')

  #evidencias adicionales
  ipPrivada = controlador_db.obtenerIpPrivada()
  ipPublica = request.form.get('ip')

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

  #validacion del ocr
  ocrNombre = request.form.get('porcentaje_nombre_ocr')
  ocrApellido = request.form.get('porcentaje_apellido_ocr')
  ocrDocumento = request.form.get('porcentaje_documento_ocr')

  dataOCRNombre = request.form.get('nombre_ocr')
  dataOCRApellido = request.form.get('apellido_ocr')
  dataOCRDocumento = request.form.get('documento_ocr')

  reconocidoCodigoBarras = request.form.get("reconocido_CB")
  nombreCodigoBarras = request.form.get('nombre_CB')
  apellidoCodigoBarras = request.form.get('apellido_CB')
  documentoCodigoBarras = request.form.get('documento_CB')

  # reconocidoCodigoBarras = stringBool(reconocidoCodigoBarras)
  # nombreCodigoBarras = stringBool(nombreCodigoBarras)
  # apellidoCodigoBarras = stringBool(apellidoCodigoBarras)
  # documentoCodigoBarras =stringBool(documentoCodigoBarras)

  #leer data url
  fotoPersonaData = leerDataUrl(fotoPersona)
  anversoData = leerDataUrl(anverso)
  reversoData = leerDataUrl(reverso)

  anversoOrientado, documentoValido = orientacionImagen(anversoData)
  selfie, selfieValida = orientacionImagen(fotoPersonaData)

  documentoEncodings = obtencionEncodings(documentoValido)
  selfieEncodings = obtencionEncodings(selfieValida)

  coincidencia = reconocimiento(selfieEncodings, documentoEncodings)

  estadoVericacion = ''

  if(coincidencia is True):
    estadoVericacion = 'Procesando segunda validación'
  else:
    estadoVericacion = 'Iniciando segunda validación'

  anversoOrientado = cv2Blob(anversoOrientado)
  fotoPersonaBlob = cv2Blob(selfie)
  reversoBlob = cv2Blob(reversoData)

  elementosVerificacion = [coincidencia, nombreCodigoBarras, apellidoCodigoBarras, documentoCodigoBarras]

  verificacionDirecta = all(elementosVerificacion)

  if(verificacionDirecta is True):
    estadoVericacion = 'Procesando Verificado'

  #normalizacion
  nombres = nombres.lower()
  apellidos = apellidos.lower()
  email = email.lower()
  tipoDocumento = tipoDocumento.lower()
  documento = documento.lower()

  estadoVericacion = recorteData(estadoVericacion)
  dispositivo = recorteData(dispositivo)
  navegador = recorteData(navegador)
  ipPublica = recorteData(ipPublica)
  ipPrivada = recorteData(ipPrivada)
  latitud = recorteData(latitud)
  longitud = recorteData(longitud)
  hora = recorteData(hora)
  fecha = recorteData(fecha)
  ocrNombre = recorteData(ocrNombre)
  ocrApellido = recorteData(ocrApellido)
  ocrDocumento = recorteData(ocrDocumento)
  dataOCRNombre = recorteData(dataOCRNombre)
  dataOCRApellido = recorteData(dataOCRApellido)
  dataOCRDocumento = recorteData(dataOCRDocumento)


  tablaActualizar = 'documento_usuario'

  #tabla evidencias 
  columnasEvidencias = ('anverso_documento', 'reverso_documento', 'foto_usuario', 'estado_verificacion', 'tipo_documento')
  tablaEvidencias = 'evidencias_usuario'
  valoresEvidencias = (anversoOrientado, reversoBlob, fotoPersonaBlob, '', '')
  idEvidenciasUsuario = controlador_db.insertTabla(columnasEvidencias, tablaEvidencias, valoresEvidencias)

  #tabla evidencias adicionales

  # columnasEvidenciasAdicionales = ('estado_verificacion', 'dispositivo', 'navegador', 'ip_publica', 'ip_privada', 'latitud', 'longitud', 'hora', 'fecha', 'validacion_nombre_ocr', 'validacion_apellido_ocr', 'validacion_documento_ocr', 'nombre_ocr', 'apellido_ocr', 'documento_ocr', 'validacion_vida', 'id_carpeta_entidad', 'id_carpeta_usuario')
  # tablaEvidenciasAdicionales = 'evidencias_adicionales'
  # valoresEvidenciasAdicionales = (estadoVericacion, dispositivo, navegador, ipPublica, ipPrivada, latitud, longitud, hora,fecha, ocrNombre, ocrApellido, ocrDocumento, dataOCRNombre, dataOCRApellido, dataOCRDocumento, movimiento, idCarpetaEntidad, idCarpetaUsuario)
  columnasEvidenciasAdicionales = ('estado_verificacion', 'dispositivo', 'navegador', 'ip_publica', 'ip_privada', 'latitud', 'longitud', 'hora', 'fecha', 'validacion_nombre_ocr', 'validacion_apellido_ocr', 'validacion_documento_ocr', 'nombre_ocr', 'apellido_ocr', 'documento_ocr', 'reconocido_cb', 'nombre_cb', 'apellido_cb', 'documento_cb')
  tablaEvidenciasAdicionales = 'evidencias_adicionales'
  valoresEvidenciasAdicionales = (estadoVericacion, dispositivo, navegador, ipPublica, ipPrivada, latitud, longitud, hora,fecha, ocrNombre, ocrApellido, ocrDocumento, dataOCRNombre, dataOCRApellido, dataOCRDocumento, reconocidoCodigoBarras, nombreCodigoBarras, apellidoCodigoBarras, documentoCodigoBarras)
  idEvidenciasAdicionales = controlador_db.insertTabla(columnasEvidenciasAdicionales, tablaEvidenciasAdicionales, valoresEvidenciasAdicionales)

  columnasDocumentoUsuario = ('nombres', 'apellidos', 'numero_documento', 'tipo_documento', 'email', 'id_evidencias', 'id_evidencias_adicionales', 'id_usuario_efirma')
  tablaDocumento = 'documento_usuario'
  valoresDocumento = (nombres, apellidos, documento, tipoDocumento, email, idEvidenciasUsuario, idEvidenciasAdicionales, idUsuario)
  documentoUsuario = controlador_db.insertTabla(columnasDocumentoUsuario, tablaDocumento, valoresDocumento)
  # #actualizar documento usuario
  # tipoDocumento = request.form.get('tipo_documento')
  # tipoDocumento = tipoDocumento.lower()

  # columnaTipoDocumento = 'tipo_documento'
  # actualizarTipoDocumento = controlador_db.actualizarData(tablaActualizar, columnaTipoDocumento, tipoDocumento, documentoUsuario)

  #return jsonify({"idValidacion":idValidacion, "idUsuario":idUsuario, "coincidenciaDocumentoRostro":coincidencia, "estadoVerificacion":estadoVericacion})

  return jsonify({"idValidacion":documentoUsuario, "idUsuario":idUsuario, "coincidenciaDocumentoRostro":coincidencia, "estadoVerificacion":estadoVericacion})

@app.errorhandler(405)
def metodoNoPermitido(e):
  return jsonify({"mensaje": "metodo no permitido", "metodoUsado": request.method}), 405

if __name__ == "__main__":
  try:
    app.run(debug=True,host="0.0.0.0", port=4000)
  finally:
    print('reactivando')
    # time.sleep(2)
    # comando = 'python main.py'
    # resultado = subprocess.run(comando, shell=True, capture_output=True, text=True)