import uuid
from flask import Blueprint, g, request, jsonify
import request.controlador_db as controlador_db
import json
from reconocimiento import orientacionImagen, verifyFaces, antiSpoofingTest
from utilities.utilidades import cv2Blob, getBrowser, readDataURL, recorteData, saveYoloCrops, stringBool
from request.eKYC import ekycDataDTO,ekycRules, getAdminToken, getSession, getValidationMedia, getVideoToken, getRequest, getSessionStatus
from mrz import validateMRZ, hasMRZ
from utilities.check_result import results
from lector_codigo import hasBarcode
from request.callback_request import callbackRequest
import hashlib
import urllib.parse
import os
import request.controlador_db as controlador_db
import requests
import base64
import json
import argparse

from utilities.utilidades import removeAccents
from utilities.token_utils import token_required
from utilities.progress_store import save_progress, get_progress, delete_progress
from utilities.api_errors import INVALID_PARAMS, error_response
from utilities.document_config import load_document_config
from utilities.request_fields import request_json, standalone_fields
from utilities.signature_security import evaluate_signature_security
import utilities.logs as logs
import time
import document_detection



validation_bp = Blueprint('validation', __name__, url_prefix="/validation")

# Raiz de almacenamiento de los recortes generados por YOLO.
# En produccion debe apuntar a un volumen montado, de lo contrario los ficheros
# se pierden en cada `docker compose up -d --build`.
RECORTES_DIR = os.getenv("RECORTES_DIR", "./recortes")



@validation_bp.route('/webhook-lleida', methods=['POST'])
def webhook():

  reqBody = request.get_json()

  return jsonify({'180.45':'no response'})

@validation_bp.route('/callback', methods=['POST'])
def callback():

  reqBody = request.get_json()
  data_str = str(reqBody) 
  with open('archivo.txt', 'a') as file: 
      file.write(data_str + '\n') 
  return 'Datos añadidos al archivo', 200

@validation_bp.route('/validation-provider', methods=['GET'])
@token_required
def validationProvider():

  entityId = request.args.get('entityId')

  selectProvider = controlador_db.selectProvider(id=entityId)

  print(selectProvider)

  validationProvider = selectProvider

  return jsonify({"provider": validationProvider})



@validation_bp.route('/check-validation', methods=['GET'])
@token_required
def checkValidation():

  userSignId = request.args.get("efirmaId")
  userHash = request.args.get('hash')

  if(userHash != None):


    checkVal = controlador_db.checkValidation(f"""
    SELECT ev.id, ev.estado_verificacion 
FROM pki_validacion.documento_usuario AS doc
INNER JOIN pki_validacion.evidencias_adicionales ev ON doc.id_evidencias_adicionales = ev.id
INNER JOIN pki_validacion.parametros_validacion AS params ON params.parametros_hash = doc.id_usuario
WHERE params.parametros_hash = '{userHash}'
ORDER BY ev.id DESC
LIMIT 1
""")

    return jsonify({'results':checkVal})

  checkVal = controlador_db.checkValidation(f"""SELECT ev.id, ev.estado_verificacion 
    FROM pki_validacion.documento_usuario AS doc
    INNER JOIN pki_validacion.evidencias_adicionales AS ev ON doc.id_evidencias_adicionales = ev.id
    WHERE doc.id_usuario_efirma = {userSignId}
    ORDER BY ev.id DESC
    LIMIT 1;""")


  return jsonify({"results": checkVal})


@validation_bp.route('/validation-params', methods=['GET'])
@token_required
def validationParams():

    userSignId = request.args.get('efirmaId')
    userHash = request.args.get('hash')

    if (userHash is not None):
        validationParameters = controlador_db.selectValidationParams(id=userHash, query="""SELECT usu_ent.tipo_validacion, usu_ent.porcentaje_acierto, usu_ent.intentos_documentos, usu_ent.intentos_rostro FROM usuarios.entidades AS usu_ent 
        inner join usuarios.usuarios AS usu ON usu.entity_id = usu_ent.entity_id
        INNER JOIN pki_validacion.parametros_validacion AS params ON usu.id = params.id_usuario 
        WHERE params.parametros_hash = ?""")

        params = {
            "validationAttendance": validationParameters[0],
            "validationPercent": validationParameters[1],
            "documentsTries": validationParameters[2],
            "faceTries": validationParameters[3]
        }
        return jsonify(params)

    validationParameters = controlador_db.selectValidationParams(id=userSignId, query="""
      SELECT ent.tipo_validacion, ent.porcentaje_acierto, ent.intentos_documentos, ent.intentos_deteccion, ent.intentos_rostro from pki_firma_electronica.firmador_pki fir
      INNER JOIN pki_firma_electronica.firma_electronica_pki AS fe ON fe.id = fir.firma_electronica_id
      INNER JOIN usuarios.usuarios AS usu ON usu.id = fe.usuario_id
      INNER JOIN usuarios.entidades AS ent ON ent.entity_id = usu.entity_id WHERE fir.id = ?
    """)

    params = {
      "validationAttendance": validationParameters[0],
      "validationPercent": validationParameters[1],
      "documentsTries": validationParameters[2],
      "detectionTries": validationParameters[3],
      "faceTries": validationParameters[4]
    }

    return jsonify(params)


@validation_bp.route('/document-config', methods=['GET'])
@token_required
def documentConfig():
    """Configuracion de seguridad del documento para la SPA.

    GET /validation/document-config?hash=<standalone>|efirmaId=<embebido>&country=<XX>

    El frontend trata cualquier error como fail-open (false/false); por eso
    aqui solo se responde 400 cuando faltan los dos identificadores y se
    devuelven los defaults cuando no hay fila configurada.
    """
    userHash = (request.args.get('hash') or '').strip()
    efirmaId = (request.args.get('efirmaId') or '').strip()

    if not userHash and not efirmaId:
        return error_response(INVALID_PARAMS, status=400)

    config = load_document_config(hash_=userHash or None, efirma_id=efirmaId or None)

    body = {
        "require_location_validation": config.require_location_validation,
        "block_on_vpn": config.block_on_vpn,
    }
    if config.location_radius_meters is not None:
        # El frontend solo conserva el valor si llega como number.
        body["location_radius_meters"] = config.location_radius_meters

    return jsonify(body), 200


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

  dataAvaible = reqBody['dataDisponible']

  userInfo = controlador_db.selectAPIKey(userId)

  userApiKey = userInfo[0]
  isValid = True if apiKey == userApiKey else False

  livenessTest = controlador_db.selectData(f'''SELECT ent.validacion_vida FROM usuarios.entidades AS ent 
  INNER JOIN usuarios.usuarios AS usu ON usu.entity_id = ent.entity_id
  WHERE usu.id = {userId}''', ())

  livenessTest = livenessTest[0]
  livenessTest = True if(livenessTest == 1) else False
  print(livenessTest)

  if(isValid):
    unique_id = uuid.uuid4()

    queryParams = f'?id={unique_id}'
    encodedParams = urllib.parse.quote(queryParams)
    hashParams = hashlib.sha256(encodedParams.encode())
    hashHex = hashParams.hexdigest()

    paramsColumns = ('id_usuario','callback','redireccion','parametros_hash', 'nombre', 'apellido', 'documento', 'tipo_documento', 'email', 'tipo_validacion', 'uso_modelo')
    paramsValues = (userId,callback, redirection, hashHex, name if(dataAvaible) else None, lastName if(dataAvaible) else None, document if(dataAvaible) else None, documentType, email, typeValidation, 'modelo' if(not dataAvaible) else None)
    paramsInsert = controlador_db.insertTabla(paramsColumns, 'parametros_validacion', paramsValues)

    #callback

    subdomain = 'desarrollo'

    callbackRequest([callback, userApiKey], {
    'claveApi':userApiKey,
    'estadoValidacion': 'iniciando validacion',
    'tipoValidacion': typeValidation,
    'idUsuario': int(userId),
    'idValidacion': paramsInsert,
    'hashValidacion': hashHex,
    'direccionValidacion': f'https://{subdomain}.e-custodia.com/validacion-vida?hash={hashHex}' if(livenessTest) else f'https://{subdomain}.e-custodia.com/validacion/#/ekyc/validation/{hashHex}'
    }
    )

    res = {
      'idUsuario': int(userId),
      'idValidacion': paramsInsert,
      'hashValidacion': hashHex,
      'direccionValidacion':  f'https://{subdomain}.e-custodia.com/validacion-vida?hash={hashHex}' if(livenessTest) else f'https://{subdomain}.e-custodia.com/validacion/#/ekyc/validation/{hashHex}'
    }

    return jsonify(res)

  return 'La api key es invalida'

@validation_bp.route('/get-user', methods=['GET'])
@token_required
def getInfo():
  firmador_id = request.args.get('id')
  pais = request.args.get('pais')

  if not firmador_id:
    return jsonify({'error': 'El parámetro id es requerido'}), 400

  row = controlador_db.selectData(
    '''SELECT
      f_pki.id,
      f_pki.firma_electronica_id,
      f_pki.nombre,
      f_pki.apellido,
      f_pki.correo,
      f_pki.tipo_documento,
      f_pki.documento,
      f_pki.evidencias_cargadas,
      f_pki.evidencias_voz,
      f_pki.enlace_temporal,
      f_pki.orden_firma,
      f_pki.tipo_firmador,
      f_pki.tipo_firma,
      f_pki.ubicacion_x_firma,
      f_pki.ubicacion_y_firma,
      f_pki.logo_firma,
      f_pki.ubicacion,
      f_pki.motivo,
      f_pki.usuario_final_predeterminado,
      f_pki.requiere_firma_grafica,
      f_pki.fecha_creacion,
      f_pki.fecha_actualizacion
    FROM pki_firma_electronica.firmador_pki AS f_pki
    WHERE f_pki.id = ?''',
    firmador_id,
    pais=pais.upper() if pais else None
  )

  if not row:
    return jsonify({'error': 'Firmador no encontrado'}), 404

  return jsonify({'dato': {
    'id': row[0],
    'firmaElectronicaId': row[1],
    'nombre': row[2],
    'apellido': row[3],
    'correo': row[4],
    'tipoDocumento': row[5],
    'documento': row[6],
    'evidenciasCargadas': bool(row[7]) if row[7] is not None else False,
    'evidenciasVoz': bool(row[8]) if row[8] is not None else False,
    'enlaceTemporal': row[9],
    'ordenFirma': row[10],
    'tipoFirmador': row[11],
    'tipoFirma': row[12],
    'ubicacionXFirma': row[13],
    'ubicacionYFirma': row[14],
    'logoFirma': row[15] if row[15] else '',
    'ubicacion': row[16] if row[16] else '',
    'motivo': row[17] if row[17] else '',
    'usuarioFinalPredeterminado': row[18] if row[18] else '',
    'requiereFirmaGrafica': bool(row[19]) if row[19] is not None else False,
    'fechaCreacion': row[20].isoformat() if hasattr(row[20], 'isoformat') else row[20],
    'fechaActualizacion': row[21].isoformat() if hasattr(row[21], 'isoformat') else row[21]
  }})

@validation_bp.route('/get-livenesstest', methods=['GET'])
@token_required
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
    INNER JOIN pki_validacion.parametros_validacion AS params ON params.id_usuario = usu.id
    WHERE params.parametros_hash = '{userHash}'
    ''', ())

  print(livenessTest)

  livenessTest = livenessTest[0] if (len(livenessTest) >=1 ) else 0
  livenessTest = True if(livenessTest == 1) else False

  return jsonify({'validacionVida':livenessTest})


@validation_bp.route('/test', methods=['POST'])
def test():

  length = request.headers.get('Content-Length')

  print(f"peso del contenido: {length}")

  return ''


@validation_bp.route('/progress', methods=['POST'])
# @token_required
def saveValidationProgress():

  idUsuario = request.args.get('idUsuario') or request.args.get('efirmaId')
  country = request.args.get('country')
  paso = request.args.get('paso')

  if not idUsuario:
    return jsonify({'error': 'El parámetro idUsuario es requerido'}), 400

  if paso is not None and not paso.isdigit():
    return jsonify({'error': 'El parámetro paso debe ser un número entero'}), 400

  data = request.get_json(silent=True)

  if data is None:
    return jsonify({'error': 'El cuerpo debe ser un JSON válido'}), 400

  if paso is not None:
    data['paso'] = int(paso)

  try:
    path = save_progress(idUsuario, data, country=country)
  except ValueError as e:
    return jsonify({'error': str(e)}), 400
  except Exception as e:
    return jsonify({'error': f'No se pudo guardar el progreso: {str(e)}'}), 500

  return jsonify({
    'saved': True,
    'idUsuario': idUsuario,
    'country': os.path.basename(os.path.dirname(path)),
    'paso': int(paso) if paso is not None else None
  }), 200


@validation_bp.route('/progress', methods=['GET'])
# @token_required
def getValidationProgress():

  idUsuario = request.args.get('idUsuario') or request.args.get('efirmaId')
  country = request.args.get('country')

  if not idUsuario:
    return jsonify({'error': 'El parámetro idUsuario es requerido'}), 400

  try:
    progress = get_progress(idUsuario, country=country)
  except ValueError as e:
    return jsonify({'error': str(e)}), 400
  except Exception as e:
    return jsonify({'error': f'No se pudo leer el progreso: {str(e)}'}), 500

  if progress is None:
    return jsonify({'error': 'No hay progreso guardado para este usuario'}), 404

  return jsonify(progress), 200

@validation_bp.route('/type-3', methods=['POST'])
@token_required
def validate():

    dataSize = request.get_data()
    sizeBytes = len(dataSize)
    sizeKb = sizeBytes / 1024
    sizeKb = round(sizeKb, 2)

    reqBody = request.get_json()

    idUsuario = request.args.get('idUsuario')
    idUsuario = int(idUsuario)
    tipo = request.args.get('tipo')

    # Politica de ubicacion obligatoria + anti-VPN del documento.
    # Se evalua antes de tocar imagenes ni base de datos para rechazar barato.
    _configDocumento, errorSeguridad = evaluate_signature_security(
        efirma_id=idUsuario,
        location=reqBody.get('location'),
        info_ip=(reqBody.get('info') or {}).get('ip'),
    )
    if errorSeguridad:
        return errorSeguridad

    info = reqBody['info']
    signer = reqBody['signInfo']
    livesnessT = reqBody['livenessTest']
    params = reqBody['params']
    documentValidation = reqBody['documentValidation']

    timesRaw = reqBody['times']
    times = json.dumps(timesRaw)

    nombres = signer['nombre']
    apellidos = signer['apellido']
    documento = signer['documento']
    email = signer['correo']
    country = signer['pais']

    tipoDocumento = info['tipoDocumento']
    fotoPersona = info['foto_persona']
    anverso = info['anverso']
    reverso = info['reverso']
    dispositivo = info['dispositivo']
    navegador = info['navegador']
    ipPublica = info['ip']
    latitud = info['latitud']
    longitud = info['longitud']
    hora = info['hora']
    fecha = info['fecha']

    idCarpetaEntidad = 0
    idCarpetaUsuario = 0
    movementTest = livesnessT['movimiento']
    videoHash =  livesnessT['videoHash']

    validationAttendance = params['validationAttendance']
    validationPercent = params['validationPercent']
    validationPercent = int(validationPercent)
    faceTries = params['faceTries']


    # #evidencias adicionales
    ipPrivada = controlador_db.obtenerIpPrivada()

    front = documentValidation['sides']['front']


    frontCode = front['code']
    frontCountry = front['country']
    frontCountryCheck = front['countryCheck']
    frontType = front['type']
    frontTypeCheck = front['typeCheck']
    frontIsExpired = front['isExpired']
    frontTries = front['tries']
    frontDetection = front['detection']
    # frontTries = int(frontTries) if frontTries is not None else None

    back = documentValidation['sides']['back']

    backCode = back['code']
    backCountry = back['country']
    backCountryCheck = back['countryCheck']
    backType = back['type']
    backTypeCheck = back['typeCheck']
    # backIsExpired = request.form.get('back_isExpired')
    backTries = back['tries']
    backDetection = back['detection']
    # backTries = int(backTries) if backTries is not None else None


    ocr = documentValidation['ocr']

    dataOcr = ocr['data']
    percentagesOcr = ocr['percentage']

    dataOCRNombre = dataOcr['name']
    dataOCRApellido = dataOcr['lastName']
    dataOCRDocumento = dataOcr['ID']

    ocrNombre = percentagesOcr['name']
    ocrApellido = percentagesOcr['lastName']
    ocrDocumento = percentagesOcr['ID']

    # #validacion del ocr
    # ocrNombre = request.form.get('porcentaje_nombre_ocr')
    # ocrApellido = request.form.get('porcentaje_apellido_ocr')
    # ocrDocumento = request.form.get('porcentaje_documento_ocr')

    # dataOCRNombre = request.form.get('nombre_ocr')
    # dataOCRApellido = request.form.get('apellido_ocr')
    # dataOCRDocumento = request.form.get('documento_ocr')

    mrzData = documentValidation['mrz']

    mrz = mrzData['code']
    dataMrz = mrzData['data']
    percentagesMrz = mrzData['percentages']

    mrzName = dataMrz['name']
    mrzLastname = dataMrz['lastName']

    mrzNamePercent = percentagesMrz['name']
    mrzLastnamePercent = percentagesMrz['lastName']

    # mrz = request.form.get('mrz')
    # mrzName = request.form.get('mrz_name')
    # mrzLastname = request.form.get('mrz_lastname')
    # mrzNamePercent = request.form.get('mrz_name_percent')
    # mrzLastnamePercent = request.form.get('mrz_lastname_percent')

    # barcode = request.form.get('codigo_barras')

    barcode = documentValidation['barcode']

    # if(tipoDocumento == 'CEDULA DE EXTRANJERIA'):
      

    # failed = request.form.get('failed')
    # failedBack = request.form.get('failed_back')
    # failedFront = request.form.get('failed_front')

    face = documentValidation['face']

    confidenceValue = documentValidation['confidence']
    confidenceValue = float(confidenceValue)
    documentFace = documentValidation['documentFace']

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
    # selfie, selfieValida = orientacionImagen(fotoPersonaData)

    checkValuesDict = {}

    checkValuesJSON = {}

    faceValidation = {}

    # isIdentical = True if(face == 'OK') else False

    checkValuesDict['confidence'] = face

    movementCheck = True if(movementTest == 'OK') else False
    checkValuesDict['movement'] = movementCheck

    antiSpoof = antiSpoofingTest(fotoPersonaData)
    checkValuesDict['antiSpoofing'] = antiSpoof

    test = [movementCheck, antiSpoof, face]

    faceValidation['liveness_test'] = {
      'movement': movementCheck,
      'antiSpoofing':  antiSpoof
    }

    faceValidation['confidence_test'] = {
      'confidence': confidenceValue,
      'value': face,
      'documentFace': documentFace
    }

    # faceValidation['img1_data'] = {
    #   'faceLandmarks': landmarks['img1']
    # }

    # faceValidation['img2_data'] = {
    #   'faceLandmarks': landmarks['img2']
    # }

    checkValuesJSON['face_validation'] = faceValidation

    if(tipoDocumento != 'CEDULA DE CIUDADANIA'):
      mrzNameCheck = True if(int(mrzNamePercent) >= 75) else False
      checkValuesDict['mrz_name'] = mrzNameCheck

      mrzLastnameCheck = True if(int(mrzLastnamePercent) >= 75) else False
      checkValuesDict['mrz_lastname'] = mrzLastnameCheck


    fCountryCheck = frontCountryCheck
    checkValuesDict['front_country'] = fCountryCheck

    fTypeCheck = frontTypeCheck
    checkValuesDict['front_type'] = fTypeCheck


    # fIsExpired = True if(frontIsExpired == 'OK') else False
    # checkValuesDict['front_isExpired'] = fIsExpired
    frontCheck = all([fCountryCheck, fTypeCheck])

    checkValuesDict['front'] = frontCheck
      # frontCheck = all([fCountryCheck, fTypeCheck])

    checkValuesJSON['sides_validation'] = {
      'front': {
        'correspond': frontCheck,
        'code': frontCode,
        'country': frontCountry,
        'type': frontType,
          # 'isExpired': not fIsExpired
      }
    }

    test.append(frontCheck)



    if(tipoDocumento != 'PASAPORTE'):

      bCountryCheck = backCountryCheck
      checkValuesDict['back_country'] = bCountryCheck

      bTypeCheck = backTypeCheck
      checkValuesDict['back_type'] = bTypeCheck

      # bIsExpired = True if(backIsExpired == 'OK') else False
      # checkValuesDict['back_isExpired'] = bIsExpired
      # backCheck = all([bTypeCheck,bCountryCheck, bIsExpired])

      backCheck = all([bTypeCheck,bCountryCheck])
      # backCheck = all([bTypeCheck])
      checkValuesDict['back'] = backCheck

      checkValuesDict['sides_country_confidence'] = True if(fCountryCheck == True  and bCountryCheck == True) else False
      
      checkValuesDict['sides_type_confidence'] = True if(fTypeCheck == True and bTypeCheck == True) else False

      # checkValuesDict['both_sides_isExpired'] = all([fIsExpired, bIsExpired])

      checkValuesJSON['sides_validation']['back'] = {
        'correspond': backCheck,
        'code': backCode,
        'country': backCountry,
        'type': backType,
        # 'isExpired': not bIsExpired
      }

      test.append(backCheck)

    checkID = []

    checkHasMRZ = hasMRZ(documentType=tipoDocumento, mrzData=mrzData)
    if(checkHasMRZ):
      mrzCheck = validateMRZ(documentType=tipoDocumento,mrzKeys=mrzData, mrzData=mrz)
      if(tipoDocumento != 'CEDULA DE CIUDADANIA'):
        checkValuesDict['mrz'] = mrzCheck
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

        test.append(mrzCheck)
      if(tipoDocumento == 'CEDULA DE CIUDADANIA'):
        checkID.append({'type':'mrz', 'check': mrzCheck})


    checkHasBarcode = hasBarcode(documentType=tipoDocumento, barcodeData=barcodeData)
    if(checkHasBarcode):
      barcodeCheck = barcode

      if(barcode is not None):
        if(tipoDocumento != "CEDULA DIGITAL"):
          test.append(barcodeCheck)
          checkValuesDict['barcode'] = barcodeCheck
          checkValuesJSON['barcode_validation'] = {
            'barcode': barcode
          }

        if(tipoDocumento == "CEDULA DIGITAL" and tipoDocumento == "CEDULA DE CIUDADANIA"):
          checkID.append({'type':'barcode', 'check': barcodeCheck})


    if(tipoDocumento == 'CEDULA DE CIUDADANIA'):

      avaibleCode = {}
      unavaibleCode = []

      for check in checkID:
        for key, value in check.items():
          if(value == True):
            avaibleCode = {'key':key, 'value':value}
          if(value == False):
            unavaibleCode.append({'key':key, 'value':value})

      if avaibleCode and 'key' in avaibleCode and avaibleCode['key'] == 'mrz':
        mrzNameCheck = True if(int(mrzNamePercent) >= 75) else False
        checkValuesDict['mrz_name'] = mrzNameCheck
        mrzLastnameCheck = True if(int(mrzLastnamePercent) >= 75) else False
        checkValuesDict['mrz_lastname'] = mrzLastnameCheck

        checkValuesDict['mrz'] = avaibleCode['value']

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

        test.append(avaibleCode['value'])

      if avaibleCode and 'key' in avaibleCode and avaibleCode['key'] == 'barcode':
        checkValuesDict['barcode'] = avaibleCode['value']
        test.append(avaibleCode['value'])

        checkValuesJSON['barcode_validation'] = {
          'barcode': barcode
        }

      if(len(unavaibleCode) >= 2):

        checkValuesJSON['barcode_validation'] = {
          'barcode': barcode
        }

        test.append(False)

    ocrNameCheck = True if(int(ocrNombre) >= 50) else False
    checkValuesDict['ocr_name'] = ocrNameCheck
    ocrLastNameCheck = True if(int(ocrApellido) >= 50) else False
    checkValuesDict['ocr_lastname'] = ocrLastNameCheck
    ocrIDCheck = True if(int(ocrDocumento) >= 50) else False
    checkValuesDict['ocr_id'] = ocrIDCheck

    ocrTotal = int(ocrNombre) + int(ocrApellido) + int(ocrDocumento)
    average = ocrTotal / 3
    ocrAverageCheck = True if(int(average) >= 51) else False
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
    
    # if(failed == 'OK'):

    #   resultState = 'validación fallida'
      
    #   if(failedBack == '!OK'):
    #     resultState += ' el anverso no es válido'
    #   if(failedFront == '!OK'):
    #     resultState += ' el reverso no es válido'

    # Evidencia auditable de la validacion de ubicacion / anti-VPN.
    locationSecurity = getattr(g, 'location_security', None)
    if locationSecurity:
        checkValuesJSON['location_security'] = locationSecurity

    checkValuesJson = json.dumps(checkValuesJSON)

    #compresiones

    controlador_db.updateBodySize((sizeKb, idUsuario,))

    anversoOrientado = cv2Blob(anversoData)
    fotoPersonaBlob = cv2Blob(fotoPersonaData)
    reversoBlob = cv2Blob(reversoData)

    #tabla evidencias 
    columnasEvidencias = ('anverso_documento', 'reverso_documento', 'foto_usuario', 'estado_verificacion', 'tipo_documento')
    tablaEvidencias = 'pki_validacion.evidencias_usuario'
    valoresEvidencias = (anversoOrientado, reversoBlob, fotoPersonaBlob, '', '')
    idEvidenciasUsuario = controlador_db.insertTabla(columnasEvidencias, tablaEvidencias, valoresEvidencias)

    # #tabla evidencias adicionales

    # columnasEvidenciasAdicionales = ('estado_verificacion', 'dispositivo', 'navegador', 'ip_publica', 'ip_privada', 'latitud', 'longitud', 'hora', 'fecha', 'validacion_nombre_ocr', 'validacion_apellido_ocr', 'validacion_documento_ocr', 'nombre_ocr', 'apellido_ocr', 'documento_ocr', 'validacion_vida', 'id_carpeta_entidad', 'id_carpeta_usuario', 'proveedor_validacion', 'mrz', 'codigo_barras', 'checks_json')
    columnasEvidenciasAdicionales = ('estado_verificacion', 'dispositivo', 'navegador', 'ip_publica', 'ip_privada', 'latitud', 'longitud', 'hora', 'fecha', 'validacion_nombre_ocr', 'validacion_apellido_ocr', 'validacion_documento_ocr', 'nombre_ocr', 'apellido_ocr', 'documento_ocr', 'validacion_vida', 'id_carpeta_entidad', 'id_carpeta_usuario', 'video_hash', 'proveedor_validacion', 'mrz', 'codigo_barras', 'checks_json', 'intentos_anverso', 'intentos_reverso', 'intentos_rostro', 'deteccion_anverso','deteccion_reverso', 'tiempos_json')
    tablaEvidenciasAdicionales = 'pki_validacion.evidencias_adicionales'
    valoresEvidenciasAdicionales = (resultState, dispositivo, navegador, ipPublica, ipPrivada, latitud, longitud, hora,fecha, ocrNombre, ocrApellido, ocrDocumento, dataOCRNombre, dataOCRApellido, dataOCRDocumento, movementTest, idCarpetaEntidad, idCarpetaUsuario , videoHash,'eFirma', mrz, barcode, checkValuesJson, frontTries, backTries, faceTries, frontDetection, backDetection, times)
    print(valoresEvidenciasAdicionales)
    # valoresEvidenciasAdicionales = (resultState, dispositivo, navegador, ipPublica, ipPrivada, latitud, longitud, hora,fecha, ocrNombre, ocrApellido, ocrDocumento, dataOCRNombre, dataOCRApellido, dataOCRDocumento, movimiento, idCarpetaEntidad, idCarpetaUsuario ,'eFirma', mrz, barcode, checkValuesJson)
    idEvidenciasAdicionales = controlador_db.insertTabla(columnasEvidenciasAdicionales, tablaEvidenciasAdicionales, valoresEvidenciasAdicionales)

    columnasDocumentoUsuario = ('nombres', 'apellidos', 'numero_documento', 'tipo_documento', 'email', 'id_evidencias', 'id_evidencias_adicionales', 'id_usuario_efirma')
    tablaDocumento = 'pki_validacion.documento_usuario'
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
      'enlaceFirma': f'https://honducert.firma.e-custodia.com/mostrar_validacion?idUsuario={idUsuario}'
    })

    # Guardado de recortes YOLO al final de la validacion, igual que el lote:
    # deteccion en proceso sobre la imagen ORIGINAL ya decodificada, mismas
    # coordenadas 'all' y mismo RECORTES_DIR. Si falla no debe alterar el
    # resultado de la validacion, solo queda registrado en logs.
    if tipoDocumento != 'PASAPORTE':
      try:
        yoloLabelsRow = controlador_db.selectData(
          f'SELECT yolo_labels FROM pki_validacion.pais as pais WHERE pais.codigo = {country.upper()}',
          ())

        if yoloLabelsRow:
          labelsPais = [l.strip() for l in str(yoloLabelsRow[0]).upper().split(',') if l.strip()]
          sidesDetectadas, _ = detectarLadosParaRecorte(
            {'front': anversoData, 'back': reversoData}, labelsPais, country.upper())
          recorteResult = persistirRecortes(
            sidesDetectadas, country.upper(), int(idUsuario), RECORTES_DIR,
            contexto=f"type-3 {idUsuario}")

          if recorteResult['archivos']:
            logs.addLog(logs.checkLogsFile(),
                        f"type-3 {idUsuario}: {len(recorteResult['archivos'])} recortes en "
                        f"{os.path.join(RECORTES_DIR, country.upper(), str(idUsuario))}")
      except Exception as e:
        logs.addLog(logs.checkLogsFile(), f"type-3 {idUsuario}: no se guardaron recortes: {e}")

    try:
        delete_progress(idUsuario, country=country)
    except Exception as e:
        logs.addLog(logs.checkLogsFile(), f"Error al eliminar el progreso de validación: {str(e)}")

    return jsonify({"idValidacion":documentoUsuarioId, "idUsuario":idUsuario, "coincidenciaDocumentoRostro":face, "estadoVerificacion":resultState})


@validation_bp.route('/standalone', methods=['POST'])
def standoleValidation():
  idUsuario = request.args.get('idUsuario')
  idUsuario = int(idUsuario)
  idValidacion = request.args.get('id')
  tipoValidacion = request.args.get('tipo')
  userHash = request.args.get('hash')

  # La SPA manda JSON (mismo payload que /type-3); los callers legacy siguen
  # pudiendo mandar multipart/form-data. standalone_fields() traduce el JSON a
  # los campos planos y sentinels 'OK'/'!OK' que espera este endpoint.
  fields = standalone_fields()
  payloadJson = request_json()
  if not isinstance(payloadJson, dict):
    payloadJson = None

  # Politica de ubicacion obligatoria + anti-VPN del documento.
  _configDocumento, errorSeguridad = evaluate_signature_security(
      hash_=userHash,
      efirma_id=idUsuario,
      location=payloadJson.get('location') if payloadJson else None,
      info_ip=(payloadJson.get('info') or {}).get('ip') if payloadJson else None,
  )
  if errorSeguridad:
    return errorSeguridad

  nombres = fields.get('nombres')
  apellidos = fields.get('apellidos')
  tipoDocumento = fields.get('tipo_documento')
  documento = fields.get('numero_documento')

  email = fields.get('email')

  idCarpetaEntidad = fields.get('carpeta_entidad_prueba_vida')
  idCarpetaUsuario = fields.get('carpeta_usuario_prueba_vida')
  movimiento = fields.get('movement_test')

  tipoDocumento = fields.get('tipo_documento')

  #evidencias adicionales
  ipPrivada = controlador_db.obtenerIpPrivada()
  ipPublica = fields.get('ip')

  dispositivo = fields.get('dispositivo')
  navegador = fields.get('navegador')
  latitud = fields.get('latitud')
  longitud = fields.get('longitud')
  hora = fields.get('hora')
  fecha = fields.get('fecha')

  #evidencias usuario
  fotoPersona = fields.get('foto_persona')
  anverso = fields.get('anverso')
  reverso = fields.get('reverso')

  frontCode = fields.get('front_code')
  frontCountry = fields.get('front_country')
  frontCountryCheck = fields.get('front_country_check')
  frontType = fields.get('front_type')
  frontTypeCheck = fields.get('front_type_check')
  frontIsExpired = fields.get('front_isExpired')
  frontTries = fields.get('front_tries')
  frontTries = int(frontTries) if frontTries is not None else None

  backCode = fields.get('back_code')
  backCountry = fields.get('back_country')
  backCountryCheck = fields.get('back_country_check')
  backType = fields.get('back_type')
  backTypeCheck = fields.get('back_type_check')
  backIsExpired = fields.get('back_isExpired')
  backTries = fields.get('back_tries')
  backTries = int(backTries) if backTries is not None else None

  movementTest = fields.get('movement_test')

  #validacion del ocr
  ocrNombre = fields.get('porcentaje_nombre_ocr')
  ocrApellido = fields.get('porcentaje_apellido_ocr')
  ocrDocumento = fields.get('porcentaje_documento_ocr')

  dataOCRNombre = fields.get('nombre_ocr')
  dataOCRApellido = fields.get('apellido_ocr')
  dataOCRDocumento = fields.get('documento_ocr')

  if(nombres == 'NULL' or nombres == 'null' and apellidos == 'NULL' or apellidos == 'null' and documento == 'NULL' or documento == 'null'):
    nombres = dataOCRNombre
    apellidos = dataOCRApellido
    documento = dataOCRDocumento
  else:
    nombres = nombres.upper()
    apellidos = apellidos.upper()

  mrz = fields.get('mrz')
  mrzName = fields.get('mrz_name')
  mrzLastname = fields.get('mrz_lastname')
  mrzNamePercent = fields.get('mrz_name_percent')
  mrzLastnamePercent = fields.get('mrz_lastname_percent')

  barcode = fields.get('codigo_barras')
  videoHash =  fields.get('video_hash')

  validationAttendance = fields.get('validation_attendance')
  validationPercent = fields.get('validation_percent')
  validationPercent = int(validationPercent) if validationPercent not in (None, '') else 60

  failed = fields.get('failed')
  failedBack = fields.get('failed_back')
  failedFront = fields.get('failed_front')

  callback = fields.get('callback')


  face = fields.get('face')
  faceTries = fields.get('face_tries')
  faceTries = int(faceTries) if faceTries is not None else None
  confidenceValue = fields.get('confidence')
  confidenceValue = float(confidenceValue) if confidenceValue not in (None, '') else 0.0

  country = fields.get('country') or request.args.get('country')
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

  # Evidencia auditable de la validacion de ubicacion / anti-VPN.
  locationSecurity = getattr(g, 'location_security', None)
  if locationSecurity:
    checkValuesJSON['location_security'] = locationSecurity

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

  columnasEvidenciasAdicionales = ('estado_verificacion', 'dispositivo', 'navegador', 'ip_publica', 'ip_privada', 'latitud', 'longitud', 'hora', 'fecha', 'validacion_nombre_ocr', 'validacion_apellido_ocr', 'validacion_documento_ocr', 'nombre_ocr', 'apellido_ocr', 'documento_ocr', 'validacion_vida', 'id_carpeta_entidad', 'id_carpeta_usuario', 'video_hash', 'proveedor_validacion', 'mrz', 'codigo_barras', 'checks_json', 'intentos_anverso', 'intentos_reverso', 'intentos_rostro')
  tablaEvidenciasAdicionales = 'evidencias_adicionales'
  valoresEvidenciasAdicionales = (resultState, dispositivo, navegador, ipPublica, ipPrivada, latitud, longitud, hora,fecha, ocrNombre, ocrApellido, ocrDocumento, dataOCRNombre, dataOCRApellido, dataOCRDocumento, movimiento, idCarpetaEntidad, idCarpetaUsuario , videoHash,'eFirma', mrz, barcode, checkValuesJson, frontTries, backTries, faceTries)
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
    'enlaceValidacion': f'https://honducert.firma.e-custodia.com/resultado_validacion?hash={userHash}'
  })

  return jsonify({"idValidacion":documentoUsuarioId, "idUsuario":idUsuario, "coincidenciaDocumentoRostro":isIdentical, "estadoVerificacion":resultState})


@validation_bp.route('/revalidacion', methods=['POST'])
def revalidacion():

  length = request.headers.get('Content-Length')

  reqBody = request.get_json()

  checkValuesDict = {}

  documentType = reqBody['documentType']

  validationPercent = reqBody['validationPercent'] if (reqBody['validationPercent'] is not None) else 60

  front = reqBody['front']
  face = front['face']
  faceDetected = front['faceDetected']
# falta antispoofing
  ocr = front['ocr']
  test = [face, faceDetected]

  checkValuesDict['confidence'] = face
  checkValuesDict['faceDetected'] = faceDetected

  ocrPercentages = ocr['percentage']
  idPercentage = True if int(ocrPercentages['ID']) >= 50 else False
  checkValuesDict['ocrID'] =idPercentage
  namePercentage = True if int(ocrPercentages['name']) >= 50 else False
  checkValuesDict['ocrName'] = namePercentage
  lastnamePercentage = True if int(ocrPercentages['lastName']) >= 50 else False
  checkValuesDict['ocrLastname'] = lastnamePercentage

  ocrTotal = int(idPercentage) + int(namePercentage) + int(lastnamePercentage)
  average = ocrTotal / 3
  print(average)
  ocrAverageCheck = True if(int(average) >= 75) else False
  # test.append(ocrAverageCheck)
  checkValuesDict['ocrAverage'] = ocrAverageCheck

  frontIsValid = front['validSide']

  frontBarcode = front['barcode']
  if(frontBarcode is not None):
    checkValuesDict['barcode'] = frontBarcode
    test.append(frontBarcode)
  
  frontMrz = front['mrz']
  if(frontMrz['code'] is not None):
    mrzName = True if(int(frontMrz['percentages']['name']) >= 75) else False
    checkValuesDict['mrzName'] = mrzName

    mrzLastname = True if(int(frontMrz['percentages']['lastName']) >= 75) else False
    checkValuesDict['mrzLastname'] = mrzLastname

  frontType = front['document']['typeCheck']
  checkValuesDict['frontType'] = frontType

  frontCountry = front['document']['countryCheck']
  checkValuesDict['frontCountry'] = frontCountry

  checkValuesDict['frontIsValid'] = frontIsValid

  frontCheck = all([frontType, frontCountry])

  test.append(frontCheck)

  checkValuesDict['front'] = frontCheck


  if(documentType != 'PASAPORTE'):
    back = reqBody['back']
    print("reverso",back)
    backIsValid = back['validSide']

    bothSide = [frontIsValid, backIsValid]

    backBarcode = back['barcode']
    if(backBarcode is not None):
      checkValuesDict['barcode'] = backBarcode
      test.append(backBarcode)
    
    backMrz = back['mrz']
    if(backMrz['code'] is not None):
      mrzName = True if(int(backMrz['percentages']['name']) >= 75) else False
      checkValuesDict['mrzName'] = mrzName

      mrzLastname = True if(int(backMrz['percentages']['lastName']) >= 75) else False
      checkValuesDict['mrzLastname'] = mrzLastname

    backType = back['document']['typeCheck']
    checkValuesDict['backType'] = backType

    backCountry = back['document']['countryCheck']
    checkValuesDict['backCountry'] = backCountry

    checkValuesDict['backIsValid'] = backIsValid

    backCheck = all([backType, backCountry])

    checkValuesDict['back'] = backCheck

    validBothSide = all(bothSide)

    checkValuesDict['bothSidesValid'] = validBothSide

    checkValuesDict['sidesCountryConfidence'] = True if(frontCountry  and backCountry) else False
    
    checkValuesDict['sidesTypeConfidence'] = True if(frontType and backType) else False

    test.append(backCheck)

  boolResult, resultState, resultPercent = results(validatioAttendance='AUTOMATICA', percent=validationPercent, checksDict=checkValuesDict)

  test = all(test)

  final = all([test,boolResult])

  checkValuesDict['percent'] = resultPercent

  if(not final):
    resultState = 'validación fallida'

  return jsonify({"state": resultState, "checkValues":checkValuesDict})

def roisDeDeteccion(results):
  """
  Convierte la salida de document_detection.detection al contrato de
  POST /document/detection: {"label", "crop": [[y1, y2], [x1, x2]]}
  -> [{"etiqueta": str, "recorte": {"left", "right", "top", "bottom"}}, ...]
  """
  rois = []

  for result in results or []:
    crop = result.get('crop') or []
    if len(crop) < 2:
      continue

    (y1, y2), (x1, x2) = crop[0], crop[1]

    rois.append({
      "etiqueta": result.get('label', 'desconocido'),
      "recorte": {
        "left": int(x1),
        "right": int(x2),
        "top": int(y1),
        "bottom": int(y2)
      }
    })

  return rois


def persistirRecortes(sides, country, signerId, outputDir, padding=0.0, contexto=""):
  """
  Recorta y persiste en disco las ROIs ya detectadas de cada lado del documento.

  Los bounding boxes son absolutos respecto a la imagen ORIGINAL de cada lado, que
  debe llegar decodificada en sides[lado]['array']. Aplicarlos sobre un recorte
  previo produce recortes doblemente recortados.

  Args:
    sides: {"front": {"coords": {...}, "array": ndarray}, "back": {...}}
      'coords' usa el contrato de /document/detection. Si no trae 'recortes' (por
      ejemplo el short-circuit de PASAPORTE) el lado simplemente se omite.
    country: codigo de pais, primer nivel de la ruta.
    signerId: id del firmador, segundo nivel de la ruta.
    outputDir: raiz de almacenamiento.
    padding: margen proporcional alrededor de cada bbox.
    contexto: prefijo para las lineas de log.
  Returns:
    dict con el manifiesto por lado y la lista de archivos escritos.
  """
  logsPath = logs.checkLogsFile()
  resumen = {}
  archivos = []
  prefix = f"{contexto} " if contexto else ""

  for side in ('front', 'back'):
    lado = sides.get(side) or {}
    coords = lado.get('coords')
    recortes = coords.get('recortes', []) if isinstance(coords, dict) else []

    detalle = []
    guardados = []

    if recortes:
      guardados = saveYoloCrops(
        image=lado.get('array'),
        recortes=recortes,
        country=country,
        signerId=signerId,
        side=side,
        outputDir=outputDir,
        padding=padding
      )

      # saveYoloCrops omite los bboxes degenerados, asi que se empareja por indice
      # solo cuando la cantidad coincide.
      if len(guardados) == len(recortes):
        detalle = [{"etiqueta": r["etiqueta"], "recorte": r["recorte"],
                    "archivo": os.path.basename(p), "ruta": p}
                   for r, p in zip(recortes, guardados)]
      else:
        detalle = [{"archivo": os.path.basename(p), "ruta": p} for p in guardados]

    imagen = lado.get('array')
    dimensiones = {"ancho": int(imagen.shape[1]), "alto": int(imagen.shape[0])} if imagen is not None else None

    resumen[side] = {
      "dimensiones": dimensiones,
      "roisDetectadas": len(recortes),
      "recortesGuardados": len(guardados),
      "rois": detalle
    }

    archivos.extend(guardados)

    if guardados:
      logs.addLog(logsPath, f"{prefix}firmador {signerId} {side}: {len(guardados)} recortes en {os.path.dirname(guardados[0])}")

  if resumen['front']['roisDetectadas'] != resumen['front']['recortesGuardados'] or \
     resumen['back']['roisDetectadas'] != resumen['back']['recortesGuardados']:
    logs.addLog(logsPath, f"{prefix}firmador {signerId}: ROIs detectadas y recortes guardados no coinciden "
                          f"(front {resumen['front']['roisDetectadas']}/{resumen['front']['recortesGuardados']}, "
                          f"back {resumen['back']['roisDetectadas']}/{resumen['back']['recortesGuardados']})")

  return {"lados": resumen, "archivos": archivos}


def detectarLadosParaRecorte(arrays, yoloLabels, country):
  """
  Corre la deteccion YOLO en proceso sobre cada lado ya decodificado y arma la
  estructura 'sides' que espera persistirRecortes. Unico camino de deteccion ->
  coordenadas que comparten type-3, test-recortes y cualquier futuro consumidor.

  Args:
    arrays: {'front': ndarray|None, 'back': ndarray|None}.
    yoloLabels: etiquetas del modelo para el pais (lista de str).
    country: clave de documentDetection, en mayusculas.
  Returns:
    (sides, errores): sides[lado]= {'array', 'coords': {'recortes': [...]}} para
    los lados con array; errores[lado]= mensaje si la deteccion fallo.
  """
  sides = {'front': {}, 'back': {}}
  errores = {}

  for side, array in arrays.items():
    if array is None:
      continue

    sides[side]['array'] = array

    try:
      results = document_detection.detection(array, yoloLabels, country)
    except Exception as e:
      errores[side] = f"fallo la deteccion YOLO: {e}"
      continue

    sides[side]['coords'] = {'recortes': roisDeDeteccion(results)}

  return sides, errores


@validation_bp.route('/process-revalidation', methods=['POST'])
def process_revalidation():

    initTime = time.time()
    baseRoute = 'http://desarrollo.e-custodia.com'
    ocrUrl = f"{baseRoute}/validacion-ocr-back"
    validateUrl = f"{baseRoute}/validacion-back"

    api_key = request.headers.get('X-Api-Key')
    password = 'me+15%,gc}FV-9ND(;(Rr'

    if api_key != password:
      return jsonify({"error": "No autorizado"}), 401
    
    entityId = request.args.get('id_entidad', type=int)

    # obtener ultima validacion

    queryLastVal = f'''
      SELECT regis.id_recortes FROM pki_validacion.revalidacion_registro AS regis
WHERE regis.id_entidad = {entityId}
ORDER BY regis.id_firmador DESC
LIMIT 1 
''' 


    lastIndex =  controlador_db.selectData(queryLastVal, ())
    if(lastIndex is not None):
      lastIndex = lastIndex[0]

    # Obtener parámetros de la query
    revalidationBatch = request.args.get('lote_validacion', default=1, type=int)
    queryValidation = f'''
      SELECT docu.nombres, docu.apellidos, docu.numero_documento, docu.tipo_documento, docu.id_usuario_efirma, docu.id, docu.id_evidencias, pais.codigo, pais.yolo_labels, ent.porcentaje_acierto, evi_ad.estado_verificacion
      FROM pki_validacion.documento_usuario AS docu 
      INNER JOIN pki_validacion.evidencias_adicionales AS evi_ad ON evi_ad.id = docu.id_evidencias_adicionales
      INNER JOIN pki_validacion.evidencias_usuario AS evi ON evi.id = docu.id_evidencias
      INNER JOIN pki_firma_electronica.firmador_pki AS firmador ON firmador.id = docu.id_usuario_efirma
      INNER JOIN pki_firma_electronica.firma_electronica_pki AS firma ON firma.id = firmador.firma_electronica_id
      INNER JOIN usuarios.usuarios AS usu ON usu.id = firma.usuario_id
      INNER JOIN usuarios.entidades AS ent ON usu.entity_id = ent.entity_id
      INNER JOIN pki_validacion.pais AS pais ON pais.codigo = usu.pais
      WHERE ent.entity_id = {entityId} {'AND docu.id > {}'.format(lastIndex) if lastIndex is not None else ''} LIMIT {revalidationBatch}
'''

    if not entityId:
        return jsonify({"error": "El parámetro 'id_entidad' es requerido"}), 400

    validations = controlador_db.selectValidations(queryValidation, ())

    results_list = []
    for validation in validations:


      name = validation[0]
      lastname = validation[1]
      documentNumber = validation[2]
      documentType = removeAccents(validation[3])
      signerId = validation[4]
      id = validation[5]
      idEvidence = validation[6]
      country = validation[7]
      yoloLabels = validation[8]
      validationPercent = validation[9]
      originalState = validation[10]
      
      time.sleep(60)

      evidence = controlador_db.selectData(f'''SELECT evi.foto_usuario, evi.anverso_documento, evi.reverso_documento FROM pki_validacion.evidencias_usuario AS evi WHERE evi.id = {idEvidence}''', ())

      # print(evidence)
      # return 'asdasd'

      def convert_to_base64(blob):
        return f"data:image/jpeg;base64,{base64.b64encode(blob).decode('utf-8')}"

      selfieImage = convert_to_base64(evidence[0])
      frontImage = convert_to_base64(evidence[1])
      backImage = convert_to_base64(evidence[2])

      sides = {"front": {}, "back": {}}
      def getOrientation(image, side):
          response = requests.post(f"{ocrUrl}/rotate", json={"image":image})
          data = json.loads(response.text)
          sides[side]['textAngle'] = data['textAngle']

      getOrientation(frontImage, 'front')
      getOrientation(backImage, 'back')

      ocr = {}

      def getLabelCrop(image, country, side):
        # `all=true` devuelve todas las ROIs detectadas, no solo documento y FOTO,
        # para poder persistir despues los recortes de cada campo del documento.
        response = requests.post(f"{validateUrl}/document/detection?all=true", json={"image":image, "country": country})
        sides[side]['coords'] = json.loads(response.text)
        sides[side]['image'] = image
        # Los bounding boxes son absolutos respecto a la imagen original, por lo que
        # hay que conservarla decodificada para recortar sobre ella.
        sides[side]['array'] = readDataURL(image)


      getLabelCrop(frontImage, country, 'front')
      getLabelCrop(backImage, country, 'back')

      def ocr_request(image, coords, noOCRLabels, side):
        response = requests.post(f"{ocrUrl}/yolo-ocr", json={"image": image, "labels": coords, 'noOcrLabels': noOCRLabels})
        sides[side]['ocr'] = json.loads(response.text)
        ocr[side] = json.loads(response.text)

      ocr_request(frontImage, sides['front']['coords'], '', 'front')
      ocr_request(backImage, sides['back']['coords'], '', 'back')

      documentValidation = {'front': {}, 'back': {}}

      types = {
        'HND': ['DNI', 'PASAPORTE'],
        'COL': ['CEDULA DE CIUDADANIA', 'CEDULA DE EXTRANJERIA', 'PASAPORTE']
      }

      if country in types:
        if documentType not in types[country]:
          print(f"Tipo de documento '{documentType}' no corresponde al país '{country}'. Se omite la validación para id {id}.")
          continue
      else:
        print(f"No hay tipos de documento configurados para el país '{country}'. Se omite la validación para id {id}.")
        continue

      documentDataStore = {'front': {}, 'back': {}}

      for key in sides:
        side = "anverso" if key == 'front' else "reverso"
        payload = {
          "imagenPersona": selfieImage,
          "imagen": sides[key]['image'],
          "nombre": name,
          "apellido": lastname,
          "documento": documentNumber,
          "tipoDocumento": documentType,
          "ocr": sides[key]['ocr'],
          "ladoDocumento": side,
          "tries": 0,
          "country": country,
          # "textAngle": sides[key]['ocr']['textAngle']
          "textAngle": 0
        }
        response = requests.post(f"{validateUrl}/document/validate?side={side}", json=payload)
        responseJson = json.loads(response.text)
        documentValidation[key] = responseJson
        responseJsonCopy = responseJson.copy()
        if 'image' in responseJsonCopy:
          del responseJsonCopy['image']
        documentDataStore[key] = responseJsonCopy

      response = requests.post(f"{validateUrl}/validation/revalidacion", json={
        "front": documentValidation['front'],
        "back": documentValidation['back'],
        "validationPercent": validationPercent,
        "documentType": documentType
      })

      resJson = json.loads(response.text)
      state = resJson['state']
      checkValues = resJson['checkValues']
      checkValues['documentValidation'] = documentDataStore

      # Recortes: se reaprovechan las coordenadas ya obtenidas en getLabelCrop,
      # que se calcularon sobre la imagen original de cada lado. Antes se volvia a
      # detectar sobre documentValidation['image'], que ya es un recorte del
      # documento, produciendo recortes doblemente recortados.
      recorteResult = persistirRecortes(sides, country, signerId, RECORTES_DIR,
                                        contexto=f"revalidacion {id}")
      recortesGuardados = len(recorteResult['archivos'])

      columns = ('revalidacion_registro.revalidacion', 'revalidacion_registro.id_recortes', 'revalidacion_registro.estado', 'revalidacion_registro.id_entidad', 'estado_original', 'id_firmador', 'ocr_yolo')
      table = 'pki_validacion.revalidacion_registro'
      revalidacion_value = json.dumps(checkValues, ensure_ascii=False)
      ocrValue = json.dumps(ocr, ensure_ascii=False)
      id_recortes_value = id
      estado_value = state
      values = (revalidacion_value, id_recortes_value, estado_value, entityId, originalState, signerId, ocrValue)
      controlador_db.insertTabla(columns, table, values)
      logs.addLog(logs.checkLogsFile(), f"finalizada revalidacion id: {id}")
      results_list.append({"id": id, "estado": state, "recortes": recortesGuardados, "pais": country, "idFirmador": signerId})

      endTime = time.time()
      print(f"Tiempo transcurrido para la revalidación id {id}: {endTime - initTime:.2f} segundos")

    return jsonify({"procesados": len(results_list), "resultados": results_list, "directorioRecortes": RECORTES_DIR})


def _readTestRecortesBody():
  """
  Normaliza el cuerpo de POST /validation/test-recortes.

  Acepta dos formatos en el mismo handler:
    - application/json: subconjunto de type-3 (info.anverso / info.reverso,
      signInfo.pais). Es lo que manda el front.
    - multipart/form-data: anverso y reverso como ficheros, mas los campos de
      texto. Es lo comodo desde Postman o curl.

  Returns:
    dict con 'pais', 'idUsuario', 'idFirmador' e 'imagenes' {lado: dataURL|None}.
  Raises:
    ValueError con mensaje legible para el cliente.
  """
  imagenes = {'front': None, 'back': None}
  campos = {}

  contentType = (request.content_type or '').lower()

  if contentType.startswith('multipart/form-data'):
    campos = request.form.to_dict()
    for lado, key in (('front', 'anverso'), ('back', 'reverso')):
      archivo = request.files.get(key)
      if archivo is not None and archivo.filename:
        # Se reenvuelve como data URL para reutilizar readDataURL y no duplicar
        # la decodificacion CV.
        bytesImagen = archivo.read()
        if not bytesImagen:
          raise ValueError(f"el archivo '{key}' llego vacio")
        imagenes[lado] = f"data:image/jpeg;base64,{base64.b64encode(bytesImagen).decode('utf-8')}"

  else:
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
      raise ValueError("el cuerpo debe ser un JSON valido o multipart/form-data")

    campos = data

    info = data.get('info') or {}
    signInfo = data.get('signInfo') or {}

    if not isinstance(info, dict) or not isinstance(signInfo, dict):
      raise ValueError("'info' y 'signInfo' deben ser objetos")

    for lado, key in (('front', 'anverso'), ('back', 'reverso')):
      valor = info.get(key)
      if valor:
        imagenes[lado] = valor

    # signInfo.pais es el que usa type-3; se acepta 'pais' plano como atajo.
    if not campos.get('pais') and signInfo.get('pais'):
      campos = dict(campos, pais=signInfo['pais'])

  def _entero(valor, nombre, porDefecto):
    if valor is None or valor == '':
      return porDefecto
    try:
      return int(valor)
    except (TypeError, ValueError):
      raise ValueError(f"'{nombre}' debe ser un entero, se recibio {valor!r}")

  paddingBruto = request.args.get('padding', campos.get('padding'))

  try:
    padding = float(paddingBruto) if paddingBruto not in (None, '') else 0.0
  except (TypeError, ValueError):
    raise ValueError(f"'padding' debe ser numerico, se recibio {paddingBruto!r}")

  if not 0.0 <= padding < 1.0:
    raise ValueError("'padding' debe estar en el rango [0, 1)")

  idUsuario = _entero(request.args.get('idUsuario', campos.get('idUsuario')), 'idUsuario', 0)
  # El firmador es el segundo nivel de la ruta; si no viene se cae al idUsuario
  # para que una llamada de prueba no necesite dos identificadores.
  idFirmador = _entero(request.args.get('idFirmador', campos.get('idFirmador')), 'idFirmador', idUsuario)

  return {
    'pais': (request.args.get('pais') or campos.get('pais') or '').strip().upper(),
    'idUsuario': idUsuario,
    'idFirmador': idFirmador,
    'padding': padding,
    'imagenes': imagenes
  }


@validation_bp.route('/test-recortes', methods=['POST'])
def testRecortes():
  """
  Ruta auxiliar para probar el recorte YOLO de un solo firmador.

  Recibe el pais, los ids y las imagenes en el cuerpo con la misma forma que
  POST /validation/type-3 (info.anverso / info.reverso, signInfo.pais), o bien
  multipart/form-data con los ficheros, y persiste los recortes en el mismo
  RECORTES_DIR que usa el lote.

  Sin autenticacion, por decision explicita. Al no estar protegida y disparar
  inferencia YOLO escribiendo en disco, conviene no exponerla fuera de la red
  interna.

  La deteccion se ejecuta en proceso con document_detection.detection(), no por
  HTTP contra /document/detection: esa ruta exige token y llamarla exigiria
  fabricar un JWT para hablar consigo mismo. El resultado es identico, misma
  funcion y mismo modelo cacheado.
  """
  initTime = time.time()

  try:
    params = _readTestRecortesBody()
  except ValueError as e:
    return jsonify({"ok": False, "error": str(e)}), 400

  country = params['pais']

  if not country:
    return jsonify({"ok": False, "error": "falta el pais (signInfo.pais o el parametro pais)"}), 400

  if country not in document_detection.documentDetection:
    return jsonify({"ok": False,
                    "error": f"pais no soportado: {country}",
                    "paisesSoportados": sorted(document_detection.documentDetection.keys())}), 400

  if not any(params['imagenes'].values()):
    return jsonify({"ok": False, "error": "se requiere al menos una imagen: info.anverso o info.reverso"}), 400

  countryData = controlador_db.selectData(
    'SELECT yolo_labels FROM pki_validacion.pais as pais WHERE pais.codigo = %s', (country,))

  if not countryData:
    return jsonify({"ok": False, "error": f"no hay yolo_labels configurados para {country}"}), 400

  yoloLabels = [label.strip() for label in str(countryData[0]).upper().split(',') if label.strip()]

  arrays = {'front': None, 'back': None}
  errores = {}

  for side, imagen in params['imagenes'].items():
    if not imagen:
      continue

    try:
      array = readDataURL(imagen)
    except Exception as e:
      errores[side] = f"no se pudo decodificar la imagen: {e}"
      continue

    if array is None:
      errores[side] = "la imagen no se pudo decodificar a un array de OpenCV"
      continue

    arrays[side] = array

  if not any(a is not None for a in arrays.values()):
    return jsonify({"ok": False,
                    "error": "ninguna imagen pudo procesarse",
                    "detalle": errores}), 400

  sides, erroresDetectados = detectarLadosParaRecorte(arrays, yoloLabels, country)
  errores.update(erroresDetectados)

  if not any(side.get('array') is not None for side in sides.values()):
    return jsonify({"ok": False,
                    "error": "ninguna imagen pudo procesarse",
                    "detalle": errores}), 400

  recorteResult = persistirRecortes(sides, country, params['idFirmador'], RECORTES_DIR,
                                   padding=params['padding'],
                                   contexto=f"test-recortes {params['idUsuario']}")

  tiempoMs = int((time.time() - initTime) * 1000)

  return jsonify({
    "ok": True,
    "pais": country,
    "idUsuario": params['idUsuario'],
    "idFirmador": params['idFirmador'],
    "modelo": document_detection.documentDetection[country]['modelPath'],
    "directorio": os.path.join(RECORTES_DIR, country, str(params['idFirmador'])),
    "tiempoMs": tiempoMs,
    "lados": recorteResult['lados'],
    "archivos": recorteResult['archivos'],
    "totalRecortes": len(recorteResult['archivos']),
    **({"errores": errores} if errores else {})
  }), 200
