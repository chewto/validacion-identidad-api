from flask import Blueprint, request, jsonify
import controlador_db
from reconocimiento import obtencionEncodings, orientacionImagen, reconocimiento
from utilidades import cv2Blob, getBrowser, readDataURL, recorteData, stringBool
from eKYC import ekycDataDTO,ekycRules, getAdminToken, getSession, getValidationMedia, getVideoToken, getRequest, getSessionStatus


validation_bp = Blueprint('validation', __name__, url_prefix="/validation")

@validation_bp.route('/webhook-lleida', methods=['POST'])
def webhook():

  reqBody = request.get_json()

  userCoords = reqBody['coords'].split(',')

  userLatitude = '0'

  userLongitude = '0' 

  return jsonify({'latitude': userLatitude,'longitude':userLongitude })

@validation_bp.route('/test', methods=['POST'])
def testing():

  reqBody = request.get_json()

  userCoords = reqBody['coords'].split(',')

  print(len(userCoords))

  userLatitude = '0' if(len(userCoords) <= 1) else userCoords[0]

  userLongitude = '0' if(len(userCoords) <= 1) else userCoords[1]

  return jsonify({'latitude': userLatitude,'longitude':userLongitude })


@validation_bp.route('/validation-provider', methods=['GET'])
def validationProvider():

  entityId = request.args.get('entityId')

  selectProvider = controlador_db.selectProvider(id=entityId)

  validationProvider = selectProvider

  return jsonify({"provider": validationProvider})

@validation_bp.route('/check-validation', methods=['GET'])
def checkValidation():

  userSignId = request.args.get("efirmaId")

  checkVal = controlador_db.checkValidation(userSignId)

  return jsonify({"results": checkVal})


@validation_bp.route('/validation-lleida', methods=['POST'])
def lleidaValidation():

  userSignId = request.args.get('efirmaId')

  externalId = "0132456"

  reqJson = request.get_json()

  userCoords = reqJson['coords'].split(',')

  userLatitude ='0' if(len(userCoords) <= 1) else  userCoords[0]

  userLongitude = '0' if(len(userCoords) <= 1) else  userCoords[1]

  userIp = reqJson['ip']

  userDevice = reqJson['userDevice']

  userBrowser = getBrowser(userDevice)

  callDate = reqJson['date']

  callHour = reqJson['hour']

  callId = reqJson['callId']

  privateIp = controlador_db.obtenerIpPrivada()

  signData = getRequest(url=f"https://honducert.firma.e-custodia.com/fe-back/api/Firmador/{userSignId}")

  extractData = {
  }

  userSignData = {
    "nombre": "",
    "apellido": "",
    "correo": "",
    "tipoDocumento": "",
    "documento": ""
  }

  if('dato' in signData):

    extractData = signData['dato']

    userSignData = {
      "nombre": extractData['nombre'],
      "apellido": extractData['apellido'],
      "correo": extractData['correo'],
      "tipoDocumento": extractData['tipoDocumento'],
      "documento": extractData['documento']
    }


  adminToken = getAdminToken()

  if(adminToken == False):
    return jsonify({"error": "error generating the admin token"}), 400

  sessionStatus = getSessionStatus(callId=callId, auth=adminToken)

  selfie = getValidationMedia(callId=callId, externalId=externalId, mediaType='FACE', auth=adminToken)

  front_ID = getValidationMedia(callId=callId, externalId=externalId, mediaType='ID_FRONT', auth=adminToken)

  back_ID = getValidationMedia(callId=callId, externalId=externalId, mediaType='ID_BACK', auth=adminToken)

  validationInfo = getValidationMedia(callId=callId, externalId=externalId, mediaType='VALIDATION_INFO', auth=adminToken)

  validationCheck = getValidationMedia(callId=callId, externalId=externalId, mediaType='VALIDATION_CHECK', auth=adminToken)

  eKYCValidation = ekycDataDTO(validationInfo, userSignData)

  ekycExtractedRules, validRules = ekycRules(validationInfo)

  # isValid = 'Verificado' if(validRules == eKYCValidation['faceResult']) else 'No verificado'

  tableColumns = ('selfie','anverso_documento','reverso_documento','info_validacion','check_validacion','reglas_negocio','callId')
  insertValues = (selfie, front_ID, back_ID, validationInfo, validationCheck, ekycExtractedRules,callId)

  insertDataId = controlador_db.insertTabla(columns=tableColumns, table='validacion_raw', values=insertValues)

  userEvidenceColumns = ('anverso_documento', 'reverso_documento', 'foto_usuario','estado_verificacion', 'tipo_documento')
  userEvidenceValues = (front_ID, back_ID, selfie, '', '')

  insertUserEvidenceId = controlador_db.insertTabla(columns=userEvidenceColumns, table='evidencias_usuario', values=userEvidenceValues)

  userAditionalsColumns = ('estado_verificacion', 'dispositivo', 'navegador', 'ip_privada','latitud','longitud','hora','fecha','ip_publica','validacion_nombre_ocr','validacion_apellido_ocr','validacion_documento_ocr', 'nombre_ocr','apellido_ocr','documento_ocr', 'id_carpeta_entidad','id_carpeta_usuario','validacion_vida','proveedor_validacion', 'mrz','codigo_barras')
  userAditionalsValues = (sessionStatus, userDevice, userBrowser, privateIp, userLatitude, userLongitude, callHour, callDate, userIp, eKYCValidation['name']['ocrPercent'], eKYCValidation['surname']['ocrPercent'],eKYCValidation['document']['ocrPercent'], eKYCValidation['name']['ocrData'],eKYCValidation['surname']['ocrData'],eKYCValidation['document']['ocrData'], 0, 0, 'OK' if(validRules) else '!OK', f'lleida {callId}', '','')
  # userAditionalsValues = ("verificado", userDevice, userBrowser, privateIp, userLatitude, userLongitude, callHour, callDate, userIp, 0, 0, 0, '','', '', 0, 0, '', f'lleida {callId}')

  insertUserAditionalsId = controlador_db.insertTabla(columns=userAditionalsColumns, table='evidencias_adicionales', values=userAditionalsValues)
  
  userValidationColumns = ('nombres', 'apellidos', 'numero_documento', 'tipo_documento', 'email', 'id_evidencias', 'id_evidencias_adicionales', 'id_usuario_efirma')
  userValidationValues = (userSignData['nombre'].lower(), userSignData['apellido'].lower(), userSignData['documento'], userSignData['tipoDocumento'].lower(), userSignData['correo'], insertUserEvidenceId, insertUserAditionalsId, int(userSignId))

  insertUserValidationId = controlador_db.insertTabla(columns=userValidationColumns, table='documento_usuario', values=userValidationValues)

  return jsonify({
    "validationRawDataId": insertDataId,
    "userValidationId": insertUserValidationId,
    "userSignId":userSignId
  }), 200

@validation_bp.route('/cbs/get-session', methods=['POST'])
def createSession():

  reqBody = request.get_json()

  token = getVideoToken()

  sessionHeader = {
    'Authorization': f"Bearer {token}"
  }

  data = {
    "externalId": "0132456",
    "userClientIP": "8.8.8.8",
    "latitude": reqBody['latitude'],
    "longitude": reqBody['longitude'],
    "userAgentHeader": "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:47.0) Gecko/20100101 Firefox/47.0"
  }

  sessionRes = getSession(sessionData=data, sessionHeaders=sessionHeader)

  return jsonify({
    "status": "200",
    "message": "Session created",
    "action": "create_session_response",
    "riuSessionId": sessionRes['riuSessionId'],
    "callToken": sessionRes['callToken'],
    "adminToken": token,
    "mediaServerUrl": sessionRes['mediaServerUrl'],
    "riuCoreUrl": sessionRes['riuCoreUrl']
  })

@validation_bp.route('/type-3', methods=['POST'])
def validationType3():
  idUsuario = request.args.get('idUsuario')
  idUsuario = int(idUsuario)

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

  mrz = request.form.get('mrz')
  codigoBarras = request.form.get('codigo_barras')

  #leer data url
  fotoPersonaData = readDataURL(fotoPersona)
  anversoData = readDataURL(anverso)
  reversoData = readDataURL(reverso)

  anversoOrientado, documentoValido = orientacionImagen(anversoData)
  selfie, selfieValida = orientacionImagen(fotoPersonaData)

  documentoEncodings = obtencionEncodings(documentoValido)
  selfieEncodings = obtencionEncodings(selfieValida)

  coincidencia = reconocimiento(selfieEncodings, documentoEncodings)

  estadoVericacion = ''

  if(coincidencia is True):
    estadoVericacion = 'Verificado'
  else:
    estadoVericacion = 'No verificado'

  anversoOrientado = cv2Blob(anversoOrientado)
  fotoPersonaBlob = cv2Blob(selfie)
  reversoBlob = cv2Blob(reversoData)

  # elementosVerificacion = [coincidencia]

  # verificacionDirecta = all(elementosVerificacion)

  # if(verificacionDirecta is True):
  #   estadoVericacion = 'Verificado'

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

  columnasEvidenciasAdicionales = ('estado_verificacion', 'dispositivo', 'navegador', 'ip_publica', 'ip_privada', 'latitud', 'longitud', 'hora', 'fecha', 'validacion_nombre_ocr', 'validacion_apellido_ocr', 'validacion_documento_ocr', 'nombre_ocr', 'apellido_ocr', 'documento_ocr', 'validacion_vida', 'id_carpeta_entidad', 'id_carpeta_usuario', 'proveedor_validacion', 'mrz', 'codigo_barras')
  tablaEvidenciasAdicionales = 'evidencias_adicionales'
  valoresEvidenciasAdicionales = (estadoVericacion, dispositivo, navegador, ipPublica, ipPrivada, latitud, longitud, hora,fecha, ocrNombre, ocrApellido, ocrDocumento, dataOCRNombre, dataOCRApellido, dataOCRDocumento, movimiento, idCarpetaEntidad, idCarpetaUsuario ,'eFirma', mrz, codigoBarras)
  idEvidenciasAdicionales = controlador_db.insertTabla(columnasEvidenciasAdicionales, tablaEvidenciasAdicionales, valoresEvidenciasAdicionales)

  columnasDocumentoUsuario = ('nombres', 'apellidos', 'numero_documento', 'tipo_documento', 'email', 'id_evidencias', 'id_evidencias_adicionales', 'id_usuario_efirma')
  tablaDocumento = 'documento_usuario'
  valoresDocumento = (nombres, apellidos, documento, tipoDocumento, email, idEvidenciasUsuario, idEvidenciasAdicionales, idUsuario)
  documentoUsuario = controlador_db.insertTabla(columnasDocumentoUsuario, tablaDocumento, valoresDocumento)

  return jsonify({"idValidacion":documentoUsuario, "idUsuario":idUsuario, "coincidenciaDocumentoRostro":coincidencia, "estadoVerificacion":estadoVericacion})
