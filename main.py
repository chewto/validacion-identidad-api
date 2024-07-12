from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin
import mariadb
from reconocimiento import obtencionEncodings, orientacionImagen, reconocimiento, obtenerFrames, deteccionRostro, determinarMovimiento
import controlador_db
from utilidades import leerFileStorage, leerDataUrl, cv2Blob, recorteData, normalizarTexto, stringBool
import lector_codigo
from ocr import busquedaData,validarLadoDocumento, ocr, validacionOCR, comparacionOCR
import os


app = Flask(__name__)

carpetaPruebaVida = "./evidencias-vida"

cors = CORS(app, resources={
  r"/*":{
    "origins":"*"
  }
})
app.config['CORS_HEADER'] = 'Content-type'

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



#rutas para el front
@app.route('/ocr-reverso', methods=['POST'])
def verificarReverso():

    documento = request.get_json()

    imagenDocumento = documento['imagen']

    ladoDocumento = documento['ladoDocumento']

    tipoDocumento = documento['tipoDocumento']

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

    return jsonify({
        "codigoBarra":{
          'reconocido': 'false',
          'nombre':'false',
          'apellido':'false',
          'documento':'false'
        },
        'ladoValido': ladoValido
      })

    codigoBarrasData = lector_codigo.lectorCodigoBarras(imagenDocumento, tipoDocumento)

    if(codigoBarrasData is False):
      return jsonify({
        "codigoBarra":{
          'reconocido': 'false',
          'nombre': 'false',
          'apellido':'false',
          'documento':'false'
        },
        "ladoValido": validarLado
      })

    validacionNombre = lector_codigo.validarDataCodigo(nombre, f"{codigoBarrasData['primerNombre']}" + ' ' + f"{codigoBarrasData['segundoNombre']}")
    validacionApellido = lector_codigo.validarDataCodigo(apellido, f"{codigoBarrasData['primerApellido']}" + ' ' + f"{codigoBarrasData['segundoApellido']}")
    validacionDocumento = lector_codigo.validarDataCodigo(numeroDocumento, f"{codigoBarrasData['numeroDocumento']}")


    if(tipoDocumento == 'Cédula de extranjería'):
      return jsonify({
        "codigoBarra":{
          'reconocido': 'true',
          'nombre':'true',
          'apellido':'true',
          'documento':'true'
        },
        'ladoValido': validarLado
      })
    if(tipoDocumento == 'Cédula de ciudadanía'):
      return jsonify({
        "codigoBarra":{
          'reconocido': 'true',
          'nombre':validacionNombre,
          'apellido':validacionApellido,
          'documento':validacionDocumento
        },
        'ladoValido': validarLado
      })


@app.route('/prueba-vida', methods=['POST'])
def pruebaVida():

  id = request.args.get("id")

  formato = "webm"

  video = request.files.get("video")

  usuarioId, entidadId = controlador_db.obtenerEntidad(id)

  pathEntidad = f"{carpetaPruebaVida}/{entidadId}"

  pathUsuario = f"{pathEntidad}/{usuarioId}"

  existenciaCarpetaEntidad = os.path.exists(pathEntidad)

  existenciaCarpetaUsuario = os.path.exists(pathUsuario)

  creadoEntidad = False
  creadoUsuario = False

  if(not existenciaCarpetaEntidad):
    os.mkdir(pathEntidad)
    creadoEntidad = True

  if(not existenciaCarpetaUsuario):
    os.mkdir(pathUsuario)
    creadoUsuario = True

  pathPrueba = ""

  if((creadoEntidad and creadoUsuario)or( existenciaCarpetaEntidad and existenciaCarpetaUsuario) or (creadoEntidad and existenciaCarpetaUsuario) or (creadoUsuario and existenciaCarpetaEntidad)):
    pathPrueba = f"{pathUsuario}/{entidadId}-{usuarioId}-prueba.{formato}"
    
    video.save(pathPrueba)

  dataURL, frames = obtenerFrames(pathPrueba)

  rostroReferencia, rostrosComparacion = deteccionRostro(frames)

  movimientoDetectado = determinarMovimiento(rostroReferencia, rostrosComparacion)

  return jsonify({"idCarpetaUsuario":f"{usuarioId}", "idCarpetaEntidad":f"{entidadId}", "movimientoDetectado":f"{movimientoDetectado}", "preview":dataURL})

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
        return jsonify({
          "validaciones":peticionProceso[0]
        })
    else:
        return jsonify({"validaciones": 0})



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

  nombreCodigoBarras = request.form.get('nombre_CB')
  apellidoCodigoBarras = request.form.get('apellido_CB')
  documentoCodigoBarras = request.form.get('documento_CB')

  nombreCodigoBarras = stringBool(nombreCodigoBarras)
  apellidoCodigoBarras = stringBool(apellidoCodigoBarras)
  documentoCodigoBarras =stringBool(documentoCodigoBarras)

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

  # reconocer = reconocerRostro(fotoPersonaData, anversoData)
  # coincidencia = reconocer[0]
  # estadoVericacion = reconocer[1]
  # anversoOrientado = reconocer[2]


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

  columnasEvidenciasAdicionales = ('estado_verificacion', 'dispositivo', 'navegador', 'ip_publica', 'ip_privada', 'latitud', 'longitud', 'hora', 'fecha', 'validacion_nombre_ocr', 'validacion_apellido_ocr', 'validacion_documento_ocr', 'nombre_ocr', 'apellido_ocr', 'documento_ocr', 'validacion_vida', 'id_carpeta_entidad', 'id_carpeta_usuario')
  tablaEvidenciasAdicionales = 'evidencias_adicionales'
  valoresEvidenciasAdicionales = (estadoVericacion, dispositivo, navegador, ipPublica, ipPrivada, latitud, longitud, hora,fecha, ocrNombre, ocrApellido, ocrDocumento, dataOCRNombre, dataOCRApellido, dataOCRDocumento, movimiento, idCarpetaEntidad, idCarpetaUsuario)
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

# @app.route('/validacion-identidad-tipo-1', methods=['POST'])
# def validacionIdentidadTipo1():

#   id = request.args.get('id')
#   idUsuario = request.args.get('idUsuario')
#   tipo = request.args.get('tipo')

#   dispositivo = request.form.get('dispositivo')
#   navegador = request.form.get('navegador')
#   latitud = request.form.get('latitud')
#   longitud = request.form.get('longitud')
#   hora = request.form.get('hora')
#   fecha = request.form.get('fecha')

#   ipPrivada = controlador_db.obtenerIpPrivada()
#   # ipPublica = controlador_db.obtenerIpPublica()
#   ipPublica = request.form.get('ip')

#   tablaActualizar = 'documento_usuario'

#   #evidencias usuario
#   fotoPersona = request.form.get('foto_persona')
#   anverso = request.form.get('anverso')
#   reverso = request.form.get('reverso')

#   #validacion del ocr
#   ocrNombre = request.form.get('porcentaje_nombre_ocr')
#   ocrApellido = request.form.get('porcentaje_apellido_ocr')
#   ocrDocumento = request.form.get('porcentaje_documento_ocr')

#   dataOCRNombre = request.form.get('nombre_ocr')
#   dataOCRApellido = request.form.get('apellido_ocr')
#   dataOCRDocumento = request.form.get('documento_ocr')

#   #leer data url
#   fotoPersonaData = leerDataUrl(fotoPersona)
#   anversoData = leerDataUrl(anverso)
#   reversoData = leerDataUrl(reverso)

#   reconocer = reconocerRostro(fotoPersonaData, anversoData)
#   coincidencia = reconocer[0]
#   estadoVericacion = reconocer[1]
#   anversoOrientado = reconocer[2]

#   fotoPersonaBlob = cv2Blob(fotoPersonaData)
#   reversoBlob = cv2Blob(reversoData)


#   columnasEvidencias = ('anverso_documento','reverso_documento','foto_usuario','estado_verificacion','tipo_documento')
#   tablaEvidencias = 'evidencias_usuario'
#   valoresEvidencias = (anversoOrientado, reversoBlob, fotoPersonaBlob, '', '')
#   columnaActualizarEvidencias = 'id_evidencias'
#   evidencias = controlador_db.agregarEvidencias(columnasEvidencias, tablaEvidencias,valoresEvidencias,tablaActualizar,columnaActualizarEvidencias, id)

#   #tabla evidencias adicionales

#   columnasEvidenciasAdicionales = ('estado_verificacion','dispositivo','navegador','ip_publica', 'ip_privada','latitud','longitud','hora','fecha',  'validacion_nombre_ocr', 'validacion_apellido_ocr', 'validacion_documento_ocr', 'nombre_ocr', 'apellido_ocr', 'documento_ocr')
#   tablaEvidenciasAdicionales = 'evidencias_adicionales'
#   valoresEvidenciasAdicionales = (estadoVericacion, dispositivo, navegador, ipPublica, ipPrivada, latitud, longitud, hora,fecha, ocrNombre, ocrApellido, ocrDocumento, dataOCRNombre, dataOCRApellido, dataOCRDocumento)
#   columnaActualizarEvidenciasAdicionales = 'id_evidencias_adicionales'
#   evidenciasAdicionales = controlador_db.agregarEvidencias(columnasEvidenciasAdicionales, tablaEvidenciasAdicionales,valoresEvidenciasAdicionales,tablaActualizar,columnaActualizarEvidenciasAdicionales, id)

#   #actualizar documento usuario
#   tipoDocumento = request.form.get('tipo_documento')
#   tipoDocumento = tipoDocumento.lower()

#   columnaTipoDocumento = 'tipo_documento'
#   actualizarTipoDocumento = controlador_db.actualizarTipoDocumento(tablaActualizar, columnaTipoDocumento, tipoDocumento, id)

#   return jsonify({"coincidenciaDocumentoRostro":coincidencia, "estadoVerificacion":estadoVericacion})
  
if __name__ == "__main__":
  app.run(debug=True,host="0.0.0.0", port=4000)