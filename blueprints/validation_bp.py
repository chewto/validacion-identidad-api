import uuid
from flask import Blueprint, request, jsonify
import controlador_db
import json
from reconocimiento import orientacionImagen, verifyFaces, antiSpoofingTest
from utilidades import cv2Blob, getBrowser, readDataURL, recorteData, stringBool
from eKYC import ekycDataDTO,ekycRules, getAdminToken, getSession, getValidationMedia, getVideoToken, getRequest, getSessionStatus
from mrz import validateMRZ, hasMRZ
from check_result import results
from lector_codigo import hasBarcode
from callback_request import callbackRequest
import hashlib
import urllib.parse


validation_bp = Blueprint('validation', __name__, url_prefix="/validation")



@validation_bp.route('/webhook-lleida', methods=['POST'])
def webhook():

  reqBody = request.get_json()

  userCoords = reqBody['coords'].split(',')

  userLatitude = '0'

  userLongitude = '0' 

  return jsonify({'latitude': userLatitude,'longitude':userLongitude })

@validation_bp.route('/callback', methods=['POST'])
def callback():

  reqBody = request.get_json()
  data_str = str(reqBody) 
  with open('archivo.txt', 'a') as file: 
      file.write(data_str + '\n') 
  return 'Datos añadidos al archivo', 200

@validation_bp.route('/validation-provider', methods=['GET'])
def validationProvider():

  entityId = request.args.get('entityId')

  selectProvider = controlador_db.selectProvider(id=entityId)

  print(selectProvider)

  validationProvider = selectProvider

  return jsonify({"provider": validationProvider})

@validation_bp.route('/check-validation', methods=['GET'])
def checkValidation():

  userSignId = request.args.get("efirmaId")
  userHash = request.args.get('hash')

  if(userHash != None):


    checkVal = controlador_db.checkValidation(f"""
    SELECT ev.id, ev.estado_verificacion 
FROM documento_usuario AS doc
INNER JOIN evidencias_adicionales ev ON doc.id_evidencias_adicionales = ev.id
INNER JOIN parametros_validacion AS params ON params.parametros_hash = doc.id_usuario
WHERE params.parametros_hash = '{userHash}'
ORDER BY ev.id DESC
LIMIT 1;
""")

    return jsonify({'results':checkVal})

  checkVal = controlador_db.checkValidation(f"""SELECT ev.id, ev.estado_verificacion 
    FROM documento_usuario AS doc
    INNER JOIN evidencias_adicionales ev ON doc.id_evidencias_adicionales = ev.id
    WHERE id_usuario_efirma = {userSignId}
    ORDER BY ev.id DESC
    LIMIT 1;""")

  return jsonify({"results": checkVal})


@validation_bp.route('/validation-params', methods=['GET'])
def validationParams():

  userSignId = request.args.get('efirmaId')
  userHash = request.args.get('hash')

  if(userHash != None):
    validationParameters = controlador_db.selectValidationParams(id=userHash, query="""SELECT usu_ent.tipo_validacion, usu_ent.porcentaje_acierto, usu_ent.intentos_documentos FROM usuarios.entidades AS usu_ent 
    inner join usuarios.usuarios AS usu ON usu.entity_id = usu_ent.entity_id 
    INNER JOIN pki_validacion.parametros_validacion AS params ON usu.id = params.id 
    WHERE params.parametros_hash = ?""")

    print(validationParameters)

    params = {
    "validationAttendance":validationParameters[0],
    "validationPercent": validationParameters[1],
    "documentsTries": validationParameters[2]
  } 
    return jsonify(params)

  validationParameters = controlador_db.selectValidationParams(id=userSignId, query="SELECT ent.tipo_validacion, ent.porcentaje_acierto, ent.intentos_documentos from pki_firma_electronica.firmador_pki fir INNER JOIN pki_firma_electronica.firma_electronica_pki AS fe ON fe.id = fir.firma_electronica_id INNER JOIN usuarios.usuarios AS usu ON usu.id = fe.usuario_id INNER JOIN usuarios.entidades AS ent ON ent.entity_id = usu.entity_id WHERE fir.id = ?")

  params = {
    "validationAttendance":validationParameters[0],
    "validationPercent": validationParameters[1],
    "documentsTries": validationParameters[2]
  }

  return jsonify(params)

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


@validation_bp.route('/crear', methods=['POST'])
def testingCal():

  reqHeaders = request.headers
  apiKey = reqHeaders.get('X-Api-Key')

  reqBody = request.get_json()
  userId = reqBody['idUsuario']
  redirection = reqBody['redireccion']
  callback = reqBody['callback']
  typeValidation = reqBody['tipo']

  name = reqBody['nombre']
  lastName = reqBody['apellido']
  document = reqBody['documento']
  documentType = reqBody['tipoDocumento']
  email = reqBody['correo']

  userInfo = controlador_db.selectAPIKey(userId)

  userApiKey = userInfo[0]
  isValid = True if apiKey == userApiKey else False

  livenessTest = controlador_db.selectData(f'''SELECT ent.validacion_vida FROM usuarios.entidades AS ent 
  INNER JOIN usuarios.usuarios AS usu ON usu.entity_id = ent.entity_id
  WHERE usu.id = {userId}''', ())

  livenessTest = livenessTest[0]
  livenessTest = True if(livenessTest == 1) else False

  if(isValid):
    unique_id = uuid.uuid4()

    queryParams = f'?id={unique_id}'
    encodedParams = urllib.parse.quote(queryParams)
    hashParams = hashlib.sha256(encodedParams.encode())
    hashHex = hashParams.hexdigest()

    paramsColumns = ('id','callback','redireccion','parametros_hash', 'nombre', 'apellido', 'documento', 'tipo_documento', 'email', 'tipo_validacion')
    paramsValues = (userId,callback, redirection, hashHex, name, lastName, document, documentType, email, typeValidation)
    paramsInsert = controlador_db.insertTabla(paramsColumns, 'parametros_validacion', paramsValues)

    #callback

    subdomain = 'desarrollo'

    callbackRequest([callback, userApiKey], {
    'claveApi':userApiKey,
    'estadoValidacion': 'iniciando validacion',
    'tipoValidacion': typeValidation,
    'idUsuario': int(userId),
    # 'idValidacion': documentoUsuarioId,
    'direccionValidacion': f'https://{subdomain}.e-custodia.com/validacion-vida?hash={hashHex}' if(livenessTest) else f'https://{subdomain}.e-custodia.com/validacion/#/ekyc/validation/{hashHex}'
    }
    )

    res = {
      'idUsuario': int(userId),
      # 'idValidacion': documentoUsuarioId,
      'direccionValidacion':  f'https://{subdomain}.e-custodia.com/validacion-vida?hash={hashHex}' if(livenessTest) else f'https://{subdomain}.e-custodia.com/validacion/#/ekyc/validation/{hashHex}'
    }

    return jsonify(res)

  return 'La api key es invalida'

@validation_bp.route('/get-user', methods=['GET'])
def getInfo():

  userHash = request.args.get('hash')

  info = controlador_db.selectUserData(userHash)

  if(info == None):
    return jsonify({'dato':None})

  livenessTest = True if(info[9] == 1) else False

  info = {
    'idUsuario': info[0],
    'nombre': info[1],
    'apellido': info[2],
    'documento': info[3],
    'tipoDocumento': info[4],
    'correo': info[5],
    'tipoValidacion': info[6],
    'callback': info[7],
    'redireccion': info[8],
    'validacionVida': livenessTest
  }

  return jsonify({'dato':info})

@validation_bp.route('/get-livenesstest', methods=['GET'])
def getLivenessTest():

  signerId = request.args.get('id')
  userHash = request.args.get('hash')

  livenessTest = None

  if(signerId):
    livenessTest = controlador_db.selectData(f'''SELECT ent.validacion_vida FROM usuarios.entidades AS ent 
    INNER JOIN usuarios.usuarios AS usu ON usu.entity_id = ent.entity_id
    INNER JOIN pki_firma_electronica.firma_electronica_pki AS firma ON firma.usuario_id = usu.id
    INNER JOIN pki_firma_electronica.firmador_pki AS firmador ON firmador.firma_electronica_id = firma.id
    WHERE firmador.id = {signerId}''', ())
  
  if(userHash):
    livenessTest = controlador_db.selectData(f'''SELECT ent.validacion_vida FROM usuarios.entidades AS ent 
    INNER JOIN usuarios.usuarios AS usu ON usu.entity_id = ent.entity_id
    INNER JOIN pki_validacion.parametros_validacion AS params ON params.id = usu.id
    WHERE params.parametros_hash = '{userHash}'
    ''', ())

  print(livenessTest)

  livenessTest = livenessTest[0]
  livenessTest = True if(livenessTest == 1) else False

  return jsonify({'validacionVida':livenessTest})


@validation_bp.route('/type-3', methods=['POST'])
def validationType3():
  idUsuario = request.args.get('idUsuario')
  idUsuario = int(idUsuario)
  tipo = request.args.get('tipo')

  idCarpetaEntidad = request.form.get('carpeta_entidad_prueba_vida')
  idCarpetaUsuario = request.form.get('carpeta_usuario_prueba_vida')
  movimiento = request.form.get('movement_test')

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

  frontCode = request.form.get('front_code')
  frontCountry = request.form.get('front_country')
  frontCountryCheck = request.form.get('front_country_check')
  frontType = request.form.get('front_type')
  frontTypeCheck = request.form.get('front_type_check')
  frontIsExpired = request.form.get('front_isExpired')
  frontTries = request.form.get('front_tries')
  frontTries = int(frontTries) if frontTries is not None else None

  backCode = request.form.get('back_code')
  backCountry = request.form.get('back_country')
  backCountryCheck = request.form.get('back_country_check')
  backType = request.form.get('back_type')
  backTypeCheck = request.form.get('back_type_check')
  backIsExpired = request.form.get('back_isExpired')
  backTries = request.form.get('back_tries')
  backTries = int(backTries) if backTries is not None else None

  movementTest = request.form.get('movement_test')

  #validacion del ocr
  ocrNombre = request.form.get('porcentaje_nombre_ocr')
  ocrApellido = request.form.get('porcentaje_apellido_ocr')
  ocrDocumento = request.form.get('porcentaje_documento_ocr')

  dataOCRNombre = request.form.get('nombre_ocr')
  dataOCRApellido = request.form.get('apellido_ocr')
  dataOCRDocumento = request.form.get('documento_ocr')

  mrz = request.form.get('mrz')
  mrzName = request.form.get('mrz_name')
  mrzLastname = request.form.get('mrz_lastname')
  mrzNamePercent = request.form.get('mrz_name_percent')
  mrzLastnamePercent = request.form.get('mrz_lastname_percent')

  barcode = request.form.get('codigo_barras')

  validationAttendance = request.form.get('validation_attendance')
  validationPercent = request.form.get('validation_percent')
  validationPercent = int(validationPercent)

  videoHash =  request.form.get('video_hash')

  failed = request.form.get('failed')
  failedBack = request.form.get('failed_back')
  failedFront = request.form.get('failed_front')

  face = request.form.get('face')
  confidenceValue = request.form.get('confidence')
  confidenceValue = float(confidenceValue)
  # landmarks = request.form.get('landmarks')

  country = request.form.get('country')

  countryData = controlador_db.selectData(f'''
      SELECT * FROM pki_validacion.pais as pais 
    WHERE pais.codigo = "{country}"''', ())
  
  mrzData = json.loads(countryData[3])
  barcodeData = json.loads(countryData[4])

  #leer data url
  fotoPersonaData = readDataURL(fotoPersona)
  anversoData = readDataURL(anverso)
  reversoData = readDataURL(reverso)

  # anversoOrientado, documentoValido = orientacionImagen(anversoData)
  selfie, selfieValida = orientacionImagen(fotoPersonaData)


  checkValuesDict = {}

  checkValuesJSON = {}

  faceValidation = {}

  isIdentical = True if(face == 'OK') else False

  checkValuesDict['confidence'] = isIdentical

  movementCheck = True if(movementTest == 'OK') else False
  checkValuesDict['movement'] = movementCheck

  antiSpoof = antiSpoofingTest(selfie)
  checkValuesDict['antiSpoofing'] = antiSpoof

  test = [movementCheck, antiSpoof, isIdentical]


  faceValidation['liveness_test'] = {
    'movement': movementCheck,
    'antiSpoofing':  antiSpoof
  }


  faceValidation['confidence_test'] = {
    'confidence': confidenceValue,
    'value': isIdentical
  }

  # faceValidation['img1_data'] = {
  #   'faceLandmarks': landmarks['img1']
  # }

  # faceValidation['img2_data'] = {
  #   'faceLandmarks': landmarks['img2']
  # }

  checkValuesJSON['face_validation'] = faceValidation

  checkValuesJSON['mrz_validation'] = {
    'code': mrz,
    'data': {
      'name': mrzName,
      'lastName': mrzLastname
    },
    'percentage':{
      'name': mrzNamePercent,
      'lastName': mrzLastnamePercent
    }
  }

  checkValuesJSON['barcode_validation'] = {
    'barcode': barcode
  }

  mrzNameCheck = True if(int(mrzNamePercent) >= 75) else False
  checkValuesDict['mrz_name'] = mrzNameCheck

  mrzLastnameCheck = True if(int(mrzLastnamePercent) >= 75) else False
  checkValuesDict['mrz_lastname'] = mrzLastnameCheck

  fCountryCheck = True if(frontCountryCheck == 'OK') else False
  checkValuesDict['front_country'] = fCountryCheck

  fTypeCheck = True if(frontTypeCheck == 'OK') else False
  checkValuesDict['front_type'] = fTypeCheck

  fIsExpired = True if(frontIsExpired == 'OK') else False
  checkValuesDict['front_isExpired'] = fIsExpired
  frontCheck = all([fCountryCheck, fTypeCheck, fIsExpired])

  # frontCheck = all([fCountryCheck, fTypeCheck])
  checkValuesDict['front'] = frontCheck

  checkValuesJSON['sides_validation'] = {
    'front': {
      'correspond': frontCheck,
      'code': frontCode,
      'country': frontCountry,
      'type': frontType,
      'isExpired': not fIsExpired
    }
  }

  test.append(frontCheck)

  if(tipoDocumento != 'Pasaporte'):

    bCountryCheck = True if(backCountryCheck == 'OK') else False
    checkValuesDict['back_country'] = bCountryCheck

    bTypeCheck = True if(backTypeCheck == 'OK') else False
    checkValuesDict['back_type'] = bTypeCheck

    # bIsExpired = True if(backIsExpired == 'OK') else False
    # checkValuesDict['back_isExpired'] = bIsExpired
    # backCheck = all([bTypeCheck,bCountryCheck, bIsExpired])

    backCheck = all([bTypeCheck,bCountryCheck])
    checkValuesDict['back'] = backCheck

    checkValuesDict['sides_country_confidence'] = True if(frontCountry == backCountry) else False
    
    checkValuesDict['sides_type_confidence'] = True if(frontTypeCheck == backTypeCheck) else False

    # checkValuesDict['both_sides_isExpired'] = all([fIsExpired, bIsExpired])

    checkValuesJSON['sides_validation']['back'] = {
      'correspond': backCheck,
      'code': backCode,
      'country': backCountry,
      'type': backType,
      # 'isExpired': not bIsExpired
    }

    test.append(backCheck)

  checkHasMRZ = hasMRZ(documentType=tipoDocumento, mrzData=mrzData)
  if(checkHasMRZ):
    mrzCheck = validateMRZ(documentType=tipoDocumento,mrzKeys=mrzData, mrzData=mrz)
    checkValuesDict['mrz'] = mrzCheck
    test.append(mrzCheck)

  checkHasBarcode = hasBarcode(documentType=tipoDocumento, barcodeData=barcodeData)
  if(checkHasBarcode):
    barcodeCheck = True if(barcode == 'OK') else False
    checkValuesDict['barcode'] = barcodeCheck
    if(tipoDocumento != "CEDULA DIGITAL"):
      test.append(barcodeCheck)

  ocrNameCheck = True if(int(ocrNombre) >= 50) else False
  checkValuesDict['ocr_name'] = ocrNameCheck
  ocrLastNameCheck = True if(int(ocrApellido) >= 50) else False
  checkValuesDict['ocr_lastname'] = ocrLastNameCheck
  ocrIDCheck = True if(int(ocrDocumento) >= 50) else False
  checkValuesDict['ocr_id'] = ocrIDCheck

  ocrTotal = int(ocrNombre) + int(ocrApellido) + int(ocrDocumento)
  average = ocrTotal / 3
  ocrAverageCheck = True if(int(average) >= 75) else False
  test.append(ocrAverageCheck)
  checkValuesDict['ocr_average'] = ocrAverageCheck

  ocrValidation = {
    'data': {
      'name': dataOCRNombre,
      'lastName': dataOCRApellido,
      'ID': dataOCRDocumento,
    },
    'percent': {
      'name':ocrNombre,
      'lastName':ocrApellido,
      'ID':ocrDocumento
    },
    'average': average
  }

  checkValuesJSON['ocr_validation'] = ocrValidation


  boolResult, resultState, resultPercent = results(validatioAttendance=validationAttendance, percent=validationPercent, checksDict=checkValuesDict)

  checkValuesJSON['checks'] = checkValuesDict

  checkValuesJSON['results_validation'] = {
    'validation_percentage': resultPercent
  }

  test = all(test)

  final = all([test,boolResult])

  if(not final and validationAttendance == 'AUTOMATICA'):
    resultState = 'validación fallida'
  
  if(failed == 'OK'):

    resultState = 'validación fallida'
    
    if(failedBack == '!OK'):
      resultState += ' el anverso no es válido'
    if(failedFront == '!OK'):
      resultState += ' el reverso no es válido'

  checkValuesJson = json.dumps(checkValuesJSON)

  #compresiones

  anversoOrientado = cv2Blob(anversoData)
  fotoPersonaBlob = cv2Blob(selfie)
  reversoBlob = cv2Blob(reversoData)

  #tabla evidencias 
  columnasEvidencias = ('anverso_documento', 'reverso_documento', 'foto_usuario', 'estado_verificacion', 'tipo_documento')
  tablaEvidencias = 'evidencias_usuario'
  valoresEvidencias = (anversoOrientado, reversoBlob, fotoPersonaBlob, '', '')
  idEvidenciasUsuario = controlador_db.insertTabla(columnasEvidencias, tablaEvidencias, valoresEvidencias)

  # #tabla evidencias adicionales

  # columnasEvidenciasAdicionales = ('estado_verificacion', 'dispositivo', 'navegador', 'ip_publica', 'ip_privada', 'latitud', 'longitud', 'hora', 'fecha', 'validacion_nombre_ocr', 'validacion_apellido_ocr', 'validacion_documento_ocr', 'nombre_ocr', 'apellido_ocr', 'documento_ocr', 'validacion_vida', 'id_carpeta_entidad', 'id_carpeta_usuario', 'proveedor_validacion', 'mrz', 'codigo_barras', 'checks_json')
  columnasEvidenciasAdicionales = ('estado_verificacion', 'dispositivo', 'navegador', 'ip_publica', 'ip_privada', 'latitud', 'longitud', 'hora', 'fecha', 'validacion_nombre_ocr', 'validacion_apellido_ocr', 'validacion_documento_ocr', 'nombre_ocr', 'apellido_ocr', 'documento_ocr', 'validacion_vida', 'id_carpeta_entidad', 'id_carpeta_usuario', 'video_hash', 'proveedor_validacion', 'mrz', 'codigo_barras', 'checks_json', 'intentos_anverso', 'intentos_reverso')
  tablaEvidenciasAdicionales = 'evidencias_adicionales'
  valoresEvidenciasAdicionales = (resultState, dispositivo, navegador, ipPublica, ipPrivada, latitud, longitud, hora,fecha, ocrNombre, ocrApellido, ocrDocumento, dataOCRNombre, dataOCRApellido, dataOCRDocumento, movimiento, idCarpetaEntidad, idCarpetaUsuario , videoHash,'eFirma', mrz, barcode, checkValuesJson, frontTries, backTries)
  # valoresEvidenciasAdicionales = (resultState, dispositivo, navegador, ipPublica, ipPrivada, latitud, longitud, hora,fecha, ocrNombre, ocrApellido, ocrDocumento, dataOCRNombre, dataOCRApellido, dataOCRDocumento, movimiento, idCarpetaEntidad, idCarpetaUsuario ,'eFirma', mrz, barcode, checkValuesJson)
  idEvidenciasAdicionales = controlador_db.insertTabla(columnasEvidenciasAdicionales, tablaEvidenciasAdicionales, valoresEvidenciasAdicionales)

  columnasDocumentoUsuario = ('nombres', 'apellidos', 'numero_documento', 'tipo_documento', 'email', 'id_evidencias', 'id_evidencias_adicionales', 'id_usuario_efirma')
  tablaDocumento = 'documento_usuario'
  valoresDocumento = (nombres, apellidos, documento, tipoDocumento, email, idEvidenciasUsuario, idEvidenciasAdicionales, idUsuario)
  documentoUsuarioId = controlador_db.insertTabla(columnasDocumentoUsuario, tablaDocumento, valoresDocumento)

  

  callbackData =  controlador_db.selectCallback(idUsuario,"""SELECT ent.validacion_callback, usu.clave_api,firmador.firma_electronica_id FROM usuarios.usuarios As usu 
    INNER JOIN usuarios.entidades AS ent  ON usu.entity_id = ent.entity_id 
    INNER JOIN pki_firma_electronica.firma_electronica_pki AS firma ON  firma.usuario_id = usu.id 
    INNER JOIN pki_firma_electronica.firmador_pki AS firmador ON firmador.firma_electronica_id = firma.id 
    WHERE firmador.id = ?""")
  

  idFirma = callbackData[2]

  callbackRequest([callbackData[0], callbackData[1]], {
    'claveApi':callbackData[1],
    'estadoValidacion': resultState,
    'porcentajeValidacion': resultPercent,
    'tipoValidacion': int(tipo),
    'idFirma': int(idFirma),
    'idFirmador': int(idUsuario),
    'idValidacion': documentoUsuarioId,
    'nombre': nombres,
    'apellido': apellidos,
    'documento': documento,
    'tipo': tipoDocumento,
    'parametrosValidacion': checkValuesJSON,
    'enlaceFirma': f'https://desarrollo.e-custodia.com/mostrar_validacion?idUsuario={idUsuario}'
  })

  return jsonify({"idValidacion":documentoUsuarioId, "idUsuario":idUsuario, "coincidenciaDocumentoRostro":isIdentical, "estadoVerificacion":resultState})


@validation_bp.route('/standalone', methods=['POST'])
def standoleValidation():
  idUsuario = request.args.get('idUsuario')
  idUsuario = int(idUsuario)
  idValidacion = request.args.get('id')
  tipoValidacion = request.args.get('tipo')
  userHash = request.args.get('hash')

  nombres = request.form.get('nombres')
  apellidos = request.form.get('apellidos')

  nombres = nombres.upper()
  apellidos = apellidos.upper()

  email = request.form.get('email')
  tipoDocumento = request.form.get('tipo_documento')
  documento = request.form.get('numero_documento')

  idCarpetaEntidad = request.form.get('carpeta_entidad_prueba_vida')
  idCarpetaUsuario = request.form.get('carpeta_usuario_prueba_vida')
  movimiento = request.form.get('movement_test')

  tipoDocumento = request.form.get('tipo_documento')

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

  frontCode = request.form.get('front_code')
  frontCountry = request.form.get('front_country')
  frontCountryCheck = request.form.get('front_country_check')
  frontType = request.form.get('front_type')
  frontTypeCheck = request.form.get('front_type_check')
  frontIsExpired = request.form.get('front_isExpired')
  frontTries = request.form.get('front_tries')
  frontTries = int(frontTries) if frontTries is not None else None

  backCode = request.form.get('back_code')
  backCountry = request.form.get('back_country')
  backCountryCheck = request.form.get('back_country_check')
  backType = request.form.get('back_type')
  backTypeCheck = request.form.get('back_type_check')
  backIsExpired = request.form.get('back_isExpired')
  backTries = request.form.get('back_tries')
  backTries = int(backTries) if backTries is not None else None

  movementTest = request.form.get('movement_test')

  #validacion del ocr
  ocrNombre = request.form.get('porcentaje_nombre_ocr')
  ocrApellido = request.form.get('porcentaje_apellido_ocr')
  ocrDocumento = request.form.get('porcentaje_documento_ocr')

  dataOCRNombre = request.form.get('nombre_ocr')
  dataOCRApellido = request.form.get('apellido_ocr')
  dataOCRDocumento = request.form.get('documento_ocr')

  mrz = request.form.get('mrz')
  mrzName = request.form.get('mrz_name')
  mrzLastname = request.form.get('mrz_lastname')
  mrzNamePercent = request.form.get('mrz_name_percent')
  mrzLastnamePercent = request.form.get('mrz_lastname_percent')

  barcode = request.form.get('codigo_barras')
  videoHash =  request.form.get('video_hash')

  validationAttendance = request.form.get('validation_attendance')
  validationPercent = request.form.get('validation_percent')
  validationPercent = int(validationPercent)

  failed = request.form.get('failed')
  failedBack = request.form.get('failed_back')
  failedFront = request.form.get('failed_front')

  callback = request.form.get('callback')

  face = request.form.get('face')
  confidenceValue = request.form.get('confidence')
  confidenceValue = float(confidenceValue)

  country = request.form.get('country')
  countryData = controlador_db.selectData(f'''
      SELECT * FROM pki_validacion.pais as pais 
    WHERE pais.codigo = "{country}"''', ())
  
  mrzData = json.loads(countryData[3])
  barcodeData = json.loads(countryData[4])


  #leer data url
  fotoPersonaData = readDataURL(fotoPersona)
  anversoData = readDataURL(anverso)
  reversoData = readDataURL(reverso)

  # anversoOrientado, documentoValido = orientacionImagen(anversoData)
  selfie, selfieValida = orientacionImagen(fotoPersonaData)


  checkValuesDict = {}

  checkValuesJSON = {}

  faceValidation = {}

  # landmarks, confidenceValue, _ = verifyFaces(selfie, anversoOrientado)

  isIdentical = True if(face == 'OK') else False

  checkValuesDict['confidence'] = isIdentical

  movementCheck = True if(movementTest == 'OK') else False
  checkValuesDict['movement'] = movementCheck

  antiSpoof = antiSpoofingTest(selfie)
  checkValuesDict['antiSpoofing'] = antiSpoof

  test = [movementCheck, antiSpoof, isIdentical]

  

  faceValidation['liveness_test'] = {
    'movement': movementCheck,
    'antiSpoofing':  antiSpoof
  }


  faceValidation['confidence_test'] = {
    'confidence': confidenceValue,
    'value': isIdentical
  }

  # faceValidation['img1_data'] = {
  #   'faceLandmarks': landmarks['img1']
  # }

  # faceValidation['img2_data'] = {
  #   'faceLandmarks': landmarks['img2']
  # }

  checkValuesJSON['face_validation'] = faceValidation

  checkValuesJSON['mrz_validation'] = {
    'code': mrz,
    'data': {
      'name': mrzName,
      'lastName': mrzLastname
    },
    'percentage':{
      'name': mrzNamePercent,
      'lastName': mrzLastnamePercent
    }
  }

  checkValuesJSON['barcode_validation'] = {
    'barcode': barcode
  }

  mrzNameCheck = True if(int(mrzNamePercent) >= 75) else False
  checkValuesDict['mrz_name'] = mrzNameCheck

  mrzLastnameCheck = True if(int(mrzLastnamePercent) >= 75) else False
  checkValuesDict['mrz_lastname'] = mrzLastnameCheck

  fCountryCheck = True if(frontCountryCheck == 'OK') else False
  checkValuesDict['front_country'] = fCountryCheck

  fTypeCheck = True if(frontTypeCheck == 'OK') else False
  checkValuesDict['front_type'] = fTypeCheck

  fIsExpired = True if(frontIsExpired == 'OK') else False
  checkValuesDict['front_isExpired'] = fIsExpired
  frontCheck = all([fCountryCheck, fTypeCheck, fIsExpired])

  # frontCheck = all([fCountryCheck, fTypeCheck])
  checkValuesDict['front'] = frontCheck

  checkValuesJSON['sides_validation'] = {
    'front': {
      'correspond': frontCheck,
      'code': frontCode,
      'country': frontCountry,
      'type': frontType,
      'isExpired': not fIsExpired
    }
  }

  test.append(frontCheck)

  if(tipoDocumento != 'Pasaporte'):

    bCountryCheck = True if(backCountryCheck == 'OK') else False
    checkValuesDict['back_country'] = bCountryCheck

    bTypeCheck = True if(backTypeCheck == 'OK') else False
    checkValuesDict['back_type'] = bTypeCheck

    # bIsExpired = True if(backIsExpired == 'OK') else False
    # checkValuesDict['back_isExpired'] = bIsExpired
    # backCheck = all([bTypeCheck,bCountryCheck, bIsExpired])

    backCheck = all([bTypeCheck,bCountryCheck])
    checkValuesDict['back'] = backCheck

    checkValuesDict['sides_country_confidence'] = True if(frontCountry == backCountry) else False
    
    checkValuesDict['sides_type_confidence'] = True if(frontTypeCheck == backTypeCheck) else False

    # checkValuesDict['both_sides_isExpired'] = all([fIsExpired, bIsExpired])

    checkValuesJSON['sides_validation']['back'] = {
      'correspond': backCheck,
      'code': backCode,
      'country': backCountry,
      'type': backType,
      # 'isExpired': not bIsExpired
    }

    test.append(backCheck)

  checkHasMRZ = hasMRZ(documentType=tipoDocumento, mrzData=mrzData)
  if(checkHasMRZ):
    mrzCheck = validateMRZ(documentType=tipoDocumento,mrzKeys=mrzData, mrzData=mrz)
    checkValuesDict['mrz'] = mrzCheck
    test.append(mrzCheck)

  checkHasBarcode = hasBarcode(documentType=tipoDocumento, barcodeData=barcodeData)
  if(checkHasBarcode):
    barcodeCheck = True if(barcode == 'OK') else False
    checkValuesDict['barcode'] = barcodeCheck
    if(tipoDocumento != "CEDULA DIGITAL"):
      test.append(barcodeCheck)

  ocrNameCheck = True if(int(ocrNombre) >= 50) else False
  checkValuesDict['ocr_name'] = ocrNameCheck
  ocrLastNameCheck = True if(int(ocrApellido) >= 50) else False
  checkValuesDict['ocr_lastname'] = ocrLastNameCheck
  ocrIDCheck = True if(int(ocrDocumento) >= 50) else False
  checkValuesDict['ocr_id'] = ocrIDCheck

  ocrTotal = int(ocrNombre) + int(ocrApellido) + int(ocrDocumento)
  average = ocrTotal / 3
  ocrAverageCheck = True if(int(average) >= 75) else False
  test.append(ocrAverageCheck)
  checkValuesDict['ocr_average'] = ocrAverageCheck

  ocrValidation = {
    'data': {
      'name': dataOCRNombre,
      'lastName': dataOCRApellido,
      'ID': dataOCRDocumento,
    },
    'percent': {
      'name':ocrNombre,
      'lastName':ocrApellido,
      'ID':ocrDocumento
    },
    'average': average
  }

  checkValuesJSON['ocr_validation'] = ocrValidation

  boolResult, resultState, resultPercent = results(validatioAttendance=validationAttendance, percent=validationPercent, checksDict=checkValuesDict)

  print(resultPercent, resultState)

  checkValuesJSON['checks'] = checkValuesDict

  checkValuesJSON['results_validation'] = {
    'validation_percentage': resultPercent
  }

  test = all(test)

  final = all([test,boolResult])

  if(not final and validationAttendance == 'AUTOMATICA'):
    resultState = 'validación fallida'
  
  if(failed == 'OK'):

    resultState = 'validación fallida'
    
    if(failedBack == '!OK'):
      resultState += ' el anverso no es válido'
    if(failedFront == '!OK'):
      resultState += ' el reverso no es válido'

  checkValuesJson = json.dumps(checkValuesJSON)

  #compresiones

  anversoOrientado = cv2Blob(anversoData)
  fotoPersonaBlob = cv2Blob(selfie)
  reversoBlob = cv2Blob(reversoData)

  #tabla evidencias 
  columnasEvidencias = ('anverso_documento', 'reverso_documento', 'foto_usuario', 'estado_verificacion', 'tipo_documento')
  tablaEvidencias = 'evidencias_usuario'
  valoresEvidencias = (anversoOrientado, reversoBlob, fotoPersonaBlob, '', '')
  idEvidenciasUsuario = controlador_db.insertTabla(columnasEvidencias, tablaEvidencias, valoresEvidencias)

  columnasEvidenciasAdicionales = ('estado_verificacion', 'dispositivo', 'navegador', 'ip_publica', 'ip_privada', 'latitud', 'longitud', 'hora', 'fecha', 'validacion_nombre_ocr', 'validacion_apellido_ocr', 'validacion_documento_ocr', 'nombre_ocr', 'apellido_ocr', 'documento_ocr', 'validacion_vida', 'id_carpeta_entidad', 'id_carpeta_usuario', 'video_hash', 'proveedor_validacion', 'mrz', 'codigo_barras', 'checks_json', 'intentos_anverso', 'intentos_reverso')
  tablaEvidenciasAdicionales = 'evidencias_adicionales'
  valoresEvidenciasAdicionales = (resultState, dispositivo, navegador, ipPublica, ipPrivada, latitud, longitud, hora,fecha, ocrNombre, ocrApellido, ocrDocumento, dataOCRNombre, dataOCRApellido, dataOCRDocumento, movimiento, idCarpetaEntidad, idCarpetaUsuario , videoHash,'eFirma', mrz, barcode, checkValuesJson, frontTries, backTries)
  idEvidenciasAdicionales = controlador_db.insertTabla(columnasEvidenciasAdicionales, tablaEvidenciasAdicionales, valoresEvidenciasAdicionales)

  #aqui debemos actualizar los indices y el tipo documento

  documentoUsuarioColumns = ('nombres', 'apellidos', 'numero_documento', 'tipo_documento', 'email', 'id_evidencias', 'id_evidencias_adicionales', 'id_usuario', 'tipo_validacion')
  documentoValues = (nombres, apellidos, documento, tipoDocumento, email, idEvidenciasUsuario, idEvidenciasAdicionales, userHash, tipoValidacion)
  documentoUsuarioId = controlador_db.insertTabla(documentoUsuarioColumns, 'documento_usuario', documentoValues)

  callbackData =  controlador_db.selectCallback(idUsuario, 'SELECT usu.clave_api FROM usuarios.usuarios as usu WHERE usu.id = ?')

  #
  callbackRequest([callback, callbackData[0]], {
    'claveApi':callbackData[0],
    'estadoValidacion': resultState,
    'porcentajeValidacion': resultPercent,
    'tipoValidacion': int(tipoValidacion),
    'idUsuario': int(idUsuario),
    'idValidacion': documentoUsuarioId,
    'parametrosValidacion': checkValuesJSON,
    'enlaceValidacion': f'https://desarrollo.e-custodia.com/resultado_validacion?hash={userHash}'
  })

  return jsonify({"idValidacion":documentoUsuarioId, "idUsuario":idUsuario, "coincidenciaDocumentoRostro":isIdentical, "estadoVerificacion":resultState})

@validation_bp.route('/failed', methods=['POST'])
def rejectedValidation():

  idUser = request.args.get('idUsuario')
  idUser = int(idUser)

  reqBody = request.get_json()

  signInfo = reqBody['informacionFirmador']

  name = signInfo['nombre']
  lastName = signInfo['apellido']
  email = signInfo['correo']
  documentID = signInfo['documento']


  generalInfo = reqBody['informacion']

  anverse = generalInfo['anverso']
  anverse = readDataURL(anverse)
  anverse = cv2Blob(anverse)
  reverse = generalInfo['reverso']
  reverse = readDataURL(reverse)
  reverse = cv2Blob(reverse)
  selfie = generalInfo['foto_persona']
  selfie = readDataURL(selfie)
  selfie = cv2Blob(selfie)
  documentType = generalInfo['tipoDocumento']
  device = generalInfo['dispositivo']
  browser = generalInfo['navegador']

  privateIp = controlador_db.obtenerIpPrivada()
  publicIp = generalInfo['ip']
  
  latitude = generalInfo['latitud']
  longitude = generalInfo['longitud']

  hour = generalInfo['hora']
  date = generalInfo['fecha']

  documentValidation = reqBody['validacionDocumento']

  ocr = documentValidation['ocr']
  dataOCR = ocr['data']
  percentageOCR = ocr['percentage']

  mrz = documentValidation['mrz']
  mrzCode = mrz['code']

  face = documentValidation['face']

  barcode = documentValidation['barcode']

  livenessTest = reqBody['pruebaVida']

  movement = livenessTest['movimiento']
  idFolderEntity = livenessTest['idCarpetaEntidad']
  idFolderUser = livenessTest['idCarpetaUsuario']

  state = "Procesando validación"


  #tabla evidencias 
  columnasEvidencias = ('anverso_documento', 'reverso_documento', 'foto_usuario', 'estado_verificacion', 'tipo_documento')
  tablaEvidencias = 'evidencias_usuario'
  valoresEvidencias = (anverse, reverse, selfie, '', '')
  idEvidenciasUsuario = controlador_db.insertTabla(columnasEvidencias, tablaEvidencias, valoresEvidencias)

  #tabla evidencias adicionales

  columnasEvidenciasAdicionales = ('estado_verificacion', 'dispositivo', 'navegador', 'ip_publica', 'ip_privada', 'latitud', 'longitud', 'hora', 'fecha', 'validacion_nombre_ocr', 'validacion_apellido_ocr', 'validacion_documento_ocr', 'nombre_ocr', 'apellido_ocr', 'documento_ocr', 'validacion_vida', 'id_carpeta_entidad', 'id_carpeta_usuario', 'proveedor_validacion', 'mrz', 'codigo_barras')
  tablaEvidenciasAdicionales = 'evidencias_adicionales'
  valoresEvidenciasAdicionales = (state, device, browser, publicIp, privateIp, latitude, longitude, hour,date, percentageOCR['name'], percentageOCR['lastName'],percentageOCR['ID'] , dataOCR['name'], dataOCR['lastName'], dataOCR['ID'],  movement, idFolderEntity, idFolderUser ,'eFirma', '', '')
  idEvidenciasAdicionales = controlador_db.insertTabla(columnasEvidenciasAdicionales, tablaEvidenciasAdicionales, valoresEvidenciasAdicionales)

  columnasDocumentoUsuario = ('nombres', 'apellidos', 'numero_documento', 'tipo_documento', 'email', 'id_evidencias', 'id_evidencias_adicionales', 'id_usuario_efirma')
  tablaDocumento = 'documento_usuario'
  valoresDocumento = (name, lastName, documentID, documentType, email, idEvidenciasUsuario, idEvidenciasAdicionales, idUser)
  documentoUsuario = controlador_db.insertTabla(columnasDocumentoUsuario, tablaDocumento, valoresDocumento)

  #callback



  return jsonify({"idValidacion":documentoUsuario, "idUsuario":idUser, "coincidenciaDocumentoRostro": face, "estadoVerificacion":state})
