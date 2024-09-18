from flask import Blueprint, request, jsonify
import controlador_db
from reconocimiento import obtencionEncodings, orientacionImagen, reconocimiento
from utilidades import cv2Blob, getBrowser, readDataURL, recorteData, stringBool
from eKYC import ekycDataDTO,ekycRules, getAdminToken, getSession, getValidationMedia, getVideoToken, getRequest
import json


validation_bp = Blueprint('validation', __name__, url_prefix="/validation")

@validation_bp.route('/testing', methods=['GET'])
def testing():
  data = '{"face_m4":{"image1_data":{"face_attributes":{"exposure":{"exposure_level":"goodExposure","value":0.71},"noise":{"value":0.35,"noise_level":"medium"},"blur":{"blur_level":"medium","value":0.37},"accessories":[],"head_pose":{"yaw":5,"pitch":-65.9,"roll":-8.7},"occlusion":{"eye_occluded":0,"mouth_occluded":0,"forehead_occluded":0},"glasses":"NoGlasses"},"face_landmarks":{"nose_tip":{"y":170.4,"x":134.5},"nose_left_alar_top":{"y":157.8,"x":122.7},"nose_left_alar_out_tip":{"y":168.9,"x":115.1},"mouth_right":{"y":206.1,"x":167.1},"mouth_left":{"y":207.6,"x":111.5},"eye_left_outer":{"y":132,"x":94.6},"eyebrow_left_outer":{"y":114.8,"x":77.2},"eye_right_inner":{"y":131.3,"x":158.4},"pupil_right":{"y":129.5,"x":168.6},"eye_right_outer":{"y":129.7,"x":179.3},"upper_lip_top":{"y":198.2,"x":136.7},"eyebrow_right_inner":{"y":111.5,"x":150.2},"eye_right_top":{"y":124.4,"x":168.8},"eyebrow_left_inner":{"y":110.8,"x":118},"eye_left_top":{"y":125.1,"x":104.5},"eyebrow_right_outer":{"y":111.3,"x":196.1},"eye_left_inner":{"y":131.6,"x":114.8},"pupil_left":{"y":130.6,"x":105.5},"nose_root_left":{"y":134.2,"x":125.5},"eye_left_bottom":{"y":135.9,"x":104.3},"under_lip_bottom":{"y":229.2,"x":137.1},"nose_right_alar_top":{"y":157.9,"x":149.2},"nose_right_alar_out_tip":{"y":168.6,"x":156.5},"eye_right_bottom":{"y":134.9,"x":169.5},"under_lip_top":{"y":219.1,"x":137.3},"nose_root_right":{"y":134.1,"x":145.5},"upper_lip_bottom":{"y":205,"x":137}},"face_rectangle":{"top":90,"height":155,"left":60,"width":155}},"standard_fields":{"test_face_recognition_ratio":0.81886},"confidence":{"is_identical":0,"confidence":0.81886},"image2_data":{"face_attributes":{"exposure":{"exposure_level":"goodExposure","value":0.49},"noise":{"value":0.08,"noise_level":"low"},"blur":{"blur_level":"medium","value":0.32},"accessories":[],"head_pose":{"yaw":-0.1,"pitch":-3.9,"roll":0.5},"occlusion":{"eye_occluded":0,"mouth_occluded":0,"forehead_occluded":0},"glasses":"NoGlasses"},"face_landmarks":{"nose_tip":{"y":284.9,"x":324.9},"nose_left_alar_top":{"y":266.6,"x":305.3},"nose_left_alar_out_tip":{"y":287.2,"x":295.6},"mouth_right":{"y":340.3,"x":374.5},"mouth_left":{"y":339.7,"x":284.6},"eye_left_outer":{"y":230.8,"x":265.1},"eyebrow_left_outer":{"y":217.5,"x":244.2},"eye_right_inner":{"y":228.6,"x":357.2},"pupil_right":{"y":228.8,"x":374.2},"eye_right_outer":{"y":228.2,"x":388.6},"upper_lip_top":{"y":326.7,"x":328.5},"eyebrow_right_inner":{"y":207.2,"x":342.2},"eye_right_top":{"y":221.9,"x":372.5},"eyebrow_left_inner":{"y":208.2,"x":305.7},"eye_left_top":{"y":223.8,"x":279.5},"eyebrow_right_outer":{"y":209.1,"x":408},"eye_left_inner":{"y":229.2,"x":293.8},"pupil_left":{"y":230.5,"x":280.4},"nose_root_left":{"y":229.6,"x":311.2},"eye_left_bottom":{"y":235.7,"x":280.1},"under_lip_bottom":{"y":359.1,"x":333},"nose_right_alar_top":{"y":266.6,"x":345.5},"nose_right_alar_out_tip":{"y":287.5,"x":358.1},"eye_right_bottom":{"y":234.9,"x":374.5},"under_lip_top":{"y":344.7,"x":331.1},"nose_root_right":{"y":228.6,"x":340.5},"upper_lip_bottom":{"y":336.9,"x":328.9}},"face_rectangle":{"top":168,"height":229,"left":213,"width":229}}},"ocr_m2":{"surname_and_given_names_mrz":"QTERO CARREIRA BENITO","given_names":"BENITo","date_of_birth":"21/08/1972","surname_and_given_names_viz":"OTERO CARREIRA BENITo","mrz_type":"ID-1","date_of_birth_viz":"21/06/1972","mrz_type_mrz":"ID-1","document_class_code_mrz":"I","date_of_issue":"02/08/2021","final_check_digit_mrz":"0","age_at_issue_viz":"49","final_check_digit":"0","mrz_strings_mrz":"I<<BL423105<<<9<<<<<<<<<<<<<<<^7208218M2407290ESP<<<<<<<<<<<0^QTERO<CARREIRA<<BENITO<<<<<<<<","surname_viz":"OTERO CARREIRA","surname":"OTERO CARREIRA","nationality":"Spain","document_types_candidates":[{"icao_code":"COL","type":22,"probability":0.875918090343475,"mrz":0,"year":"2017","country_name":"Colombia","name":"Colombia - Alien Id Card (2017)"}],"age_viz":"52","given_names_viz":"BENITo","date_of_expiry_viz":"29/07/2024","date_of_birth_mrz":"21/08/1972","document_number_viz":"423105","issuing_state_code_mrz":"BL","nationality_code":"ESP","age_mrz":"52","issuing_state_name_mrz":"Saint Barthelemy","nationality_code_mrz":"ESP","remainder_term_mrz":"0","sides_number":"3","date_of_issue_viz":"02/08/2021","given_names_mrz":"BENITO","sex":"M","surname_and_given_names_transliteration_viz":"OTERO CARREIRA BENITO","document_number_mrz":"423105","age_at_issue":"49","remainder_term":"0","blood_group":"A","sex_viz":"M","standard_fields":{"nationality":"ESP","sex":"M","document_info":[{"description":"AliensIdentityCard","icao_code":"COL","type":22}],"date_of_expiry":"2024-07-29","document_number_mrz":"423105","document_number":"423105","date_of_expiry_viz":"2024-07-29","date_of_birth_mrz":"1972-08-21","document_number_viz":"423105","date_of_birth":"1972-08-21","sex_viz":"M","name_mrz":"BENITO","mrz":["I<<BL423105<<<9<<<<<<<<<<<<<<<","7208218M2407290ESP<<<<<<<<<<<0","QTERO<CARREIRA<<BENITO<<<<<<<<"],"surname_mrz":["QTERO","CARREIRA"],"date_of_birth_viz":"1972-06-21","name":"BENITo","sides_number":"3","nationality_mrz":"ESP","sex_mrz":"M","date_of_expiry_mrz":"2024-07-29","name_viz":"BENITo","issuing_state_code_viz":"COL","surname":["OTERO","CARREIRA"],"surname_viz":["OTERO","CARREIRA"]},"date_of_birth_check_digit":"8","sex_mrz":"M","age":"52","nationality_mrz":"Spain","issuing_state_name_viz":"Colombia","document_class_code":"I","document_number_check_digit":"9","nationality_viz":"ESP","document_number_check_digit_mrz":"9","issuing_state_code_viz":"COL","blood_group_viz":"A","date_of_expiry":"29/07/2024","document_number":"423105","years_since_issue_viz":"3","given_names_transliteration_viz":"BENITO","surname_and_given_names":"QTERO CARREIRA BENITO","surname_mrz":"QTERO CARREIRA","date_of_expiry_check_digit":"0","date_of_birth_check_digit_mrz":"8","date_of_expiry_check_digit_mrz":"0","issuing_state_name":"Saint Barthelemy","date_of_expiry_mrz":"29/07/2024","mrz_strings":"I<<BL423105<<<9<<<<<<<<<<<<<<<^7208218M2407290ESP<<<<<<<<<<<0^QTERO<CARREIRA<<BENITO<<<<<<<<","issuing_state_code":"BL","years_since_issue":"3","remainder_term_viz":"0"},"validation_m2":{"test_correspondence_viz_mrz_date_of_expiry":"OK","test_global_authenticity_ratio":0.8156918,"test_global_authenticity_value":"DOUBTFUL","test_image_focus":"FAIL","test_correspondence_viz_mrz_sex":"OK","test_mrz_fields_integrity_date_of_expiry_check_digit":"OK","test_correspondence_viz_mrz_surname_and_given_names":"FAIL","test_correspondence_viz_mrz_remainder_term":"OK","test_mrz_fields_integrity_document_class_code":"OK","standard_fields":{"test_correspondence_viz_mrz_date_of_expiry":"OK","test_global_authenticity_ratio":0.8156918,"test_global_authenticity_value":"DOUBTFUL","test_correspondence_viz_mrz_sex":"OK","test_mrz_fields_integrity_date_of_expiry":"OK","test_mrz_global_integrity":"OK","test_correspondence_viz_mrz_date_of_birth":"FAIL","test_mrz_fields_integrity_date_of_birth":"OK","test_mrz_fields_integrity_document_number":"OK","test_correspondence_viz_mrz_document_number":"OK","test_date_of_expiry":"FAIL","test_correspondence_viz_mrz_surname":"FAIL","test_date_of_birth":"FAIL","test_correspondence_viz_mrz_name":"OK","test_side_correspondence":"FAIL"},"test_mrz_fields_integrity_document_number_check_digit":"OK","test_correspondence_viz_mrz_document_number":"OK","test_correspondence_viz_mrz_age":"OK","test_correspondence_viz_mrz_issuing_state_name":"FAIL","test_mrz_fields_integrity_sex":"OK","test_mrz_fields_integrity_issuing_state_code":"OK","test_mrz_fields_integrity_mrz_strings":"OK","test_correspondence_viz_mrz_issuing_state_code":"FAIL","test_image_glares":"OK","test_mrz_fields_integrity_date_of_expiry":"FAIL","test_correspondence_viz_mrz_date_of_birth":"FAIL","test_mrz_fields_integrity_final_check_digit":"OK","test_mrz_fields_integrity_date_of_birth":"OK","test_mrz_fields_integrity_document_number":"OK","test_correspondence_viz_mrz_given_names":"OK","test_mrz_fields_integrity_nationality_code":"OK","test_date_of_expiry":"FAIL","test_correspondence_viz_mrz_surname":"FAIL","test_side_correspondence":"FAIL","test_mrz_fields_integrity_date_of_birth_check_digit":"OK"}}'

  jsonData = json.loads(data)

  # ekycData(jsonData, )

  return jsonify(jsonData)


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

  userLatitude = userCoords[0]

  userLongitude = userCoords[1]

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

  selfie = getValidationMedia(callId=callId, externalId=externalId, mediaType='FACE', auth=adminToken)

  front_ID = getValidationMedia(callId=callId, externalId=externalId, mediaType='ID_FRONT', auth=adminToken)

  back_ID = getValidationMedia(callId=callId, externalId=externalId, mediaType='ID_BACK', auth=adminToken)

  validationInfo = getValidationMedia(callId=callId, externalId=externalId, mediaType='VALIDATION_INFO', auth=adminToken)

  validationCheck = getValidationMedia(callId=callId, externalId=externalId, mediaType='VALIDATION_CHECK', auth=adminToken)

  eKYCValidation = ekycDataDTO(validationInfo, userSignData)

  ekycExtractedRules, validRules = ekycRules(validationInfo)

  isValid = 'Verificado' if(validRules == eKYCValidation['faceResult']) else 'iniciando segunda validación'

  tableColumns = ('selfie','anverso_documento','reverso_documento','info_validacion','check_validacion','reglas_negocio','callId')
  insertValues = (selfie, front_ID, back_ID, validationInfo, validationCheck, ekycExtractedRules,callId)

  insertDataId = controlador_db.insertTabla(columns=tableColumns, table='validacion_raw', values=insertValues)

  userEvidenceColumns = ('anverso_documento', 'reverso_documento', 'foto_usuario','estado_verificacion', 'tipo_documento')
  userEvidenceValues = (front_ID, back_ID, selfie, '', '')

  insertUserEvidenceId = controlador_db.insertTabla(columns=userEvidenceColumns, table='evidencias_usuario', values=userEvidenceValues)

  userAditionalsColumns = ('estado_verificacion', 'dispositivo', 'navegador', 'ip_privada','latitud','longitud','hora','fecha','ip_publica','validacion_nombre_ocr','validacion_apellido_ocr','validacion_documento_ocr', 'nombre_ocr','apellido_ocr','documento_ocr', 'id_carpeta_entidad','id_carpeta_usuario','validacion_vida','proveedor_validacion')
  userAditionalsValues = (isValid, userDevice, userBrowser, privateIp, userLatitude, userLongitude, callHour, callDate, userIp, eKYCValidation['name']['ocrPercent'], eKYCValidation['surname']['ocrPercent'],eKYCValidation['document']['ocrPercent'], eKYCValidation['name']['ocrData'],eKYCValidation['surname']['ocrData'],eKYCValidation['document']['ocrData'], 0, 0, 'OK' if(validRules) else '!OK', f'lleida {callId}')
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

  token = getVideoToken()

  sessionHeader = {
    'Authorization': f"Bearer {token}"
  }

  data = {
    "externalId": "0132456",
    "userClientIP": "8.8.8.8",
    "latitude": "22.1462027",
    "longitude": "113.56829379999999",
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

  nombreCodigoBarras = request.form.get('nombre_CB')
  apellidoCodigoBarras = request.form.get('apellido_CB')
  documentoCodigoBarras = request.form.get('documento_CB')

  nombreCodigoBarras = stringBool(nombreCodigoBarras)
  apellidoCodigoBarras = stringBool(apellidoCodigoBarras)
  documentoCodigoBarras =stringBool(documentoCodigoBarras)

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

  columnasEvidenciasAdicionales = ('estado_verificacion', 'dispositivo', 'navegador', 'ip_publica', 'ip_privada', 'latitud', 'longitud', 'hora', 'fecha', 'validacion_nombre_ocr', 'validacion_apellido_ocr', 'validacion_documento_ocr', 'nombre_ocr', 'apellido_ocr', 'documento_ocr', 'validacion_vida', 'id_carpeta_entidad', 'id_carpeta_usuario', 'proveedor_validacion')
  tablaEvidenciasAdicionales = 'evidencias_adicionales'
  valoresEvidenciasAdicionales = (estadoVericacion, dispositivo, navegador, ipPublica, ipPrivada, latitud, longitud, hora,fecha, ocrNombre, ocrApellido, ocrDocumento, dataOCRNombre, dataOCRApellido, dataOCRDocumento, movimiento, idCarpetaEntidad, idCarpetaUsuario ,'eFirma')
  idEvidenciasAdicionales = controlador_db.insertTabla(columnasEvidenciasAdicionales, tablaEvidenciasAdicionales, valoresEvidenciasAdicionales)

  columnasDocumentoUsuario = ('nombres', 'apellidos', 'numero_documento', 'tipo_documento', 'email', 'id_evidencias', 'id_evidencias_adicionales', 'id_usuario_efirma')
  tablaDocumento = 'documento_usuario'
  valoresDocumento = (nombres, apellidos, documento, tipoDocumento, email, idEvidenciasUsuario, idEvidenciasAdicionales, idUsuario)
  documentoUsuario = controlador_db.insertTabla(columnasDocumentoUsuario, tablaDocumento, valoresDocumento)

  return jsonify({"idValidacion":documentoUsuario, "idUsuario":idUsuario, "coincidenciaDocumentoRostro":coincidencia, "estadoVerificacion":estadoVericacion})
