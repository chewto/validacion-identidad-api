import requests
import base64
import json

from ocr import extraerPorcentaje

user = {
    "login": "clinpays_ekyctest",
    "password":"zdU62r{Z._9jYQNa"
}

videoURL = 'https://ekycvideoapiwest-test.lleida.net/api/rest/auth/get_video_token'

sessionURL = 'https://ekycvideoapiwest-test.lleida.net/api/rest/standalone/create_session'

adminURL = 'https://ekycvideoapiwest-test.lleida.net/api/rest/auth/get_admin_token'

mediURL = 'https://ekycvideoapiwest-test.lleida.net/api/rest/admin/get_media'

def getRequest(url):
  try:
    res = requests.get(url=url)
    
    return res.json()

  except requests.RequestException as e:
    print(e)
    return {

    }

def postRequest(url, headers, data):

  try:
    res = requests.post(url=url, json=data, headers=headers)
    return res.json()
  except requests.RequestException as e:
    print(e)
    return {

    }

def getAdminToken():

  adminRes = postRequest(url=adminURL, data=user, headers={})

  token = adminRes['adminToken']

  if(len(token) <= 0):
    return ''
  
  return token

def getValidationMedia(callId, externalId, mediaType, auth):

  errorCodes = ['400.0', '404.0']

  header = {
    'Authorization': f"Bearer {auth}"
  }

  callData = {
    "callId": callId,
    "externalId": externalId,
    "mediaType": mediaType
  }

  validationRes = postRequest(url=mediURL, data=callData, headers=header)

  if(validationRes['status'] in errorCodes and validationRes['code'] in errorCodes):
    return 'no se encontro la validación'

  data = {
    "dataFormat": validationRes['dataFormat'],
    "data": validationRes['data']
  }

  decodedData = getDecodedData(data)

  return decodedData

def getDecodedData(encodedData):

  if(len(encodedData) <= 0):
    return 'no se encontro'

  base64EncodedData = encodedData['data']

  dataFormat = encodedData['dataFormat']
  decodedData = base64.b64decode(base64EncodedData)

  if(dataFormat == None):
    stringData = decodedData.decode("utf-8")

    return stringData

  return decodedData

def getVideoToken():
  videoRes = postRequest(url=videoURL,data=user, headers={})

  token = videoRes['adminToken']

  if(len(token) <= 0):
    return ''

  return token

def getSession(sessionData, sessionHeaders):

  sessionRes = postRequest(url=sessionURL, data=sessionData, headers=sessionHeaders)

  if(len(sessionRes) <= 0):
    return {
      "riuSessionId": "",
      "callToken": "",
      "mediaServerUrl": "",
      "riuCoreUrl": ""
    }

  return sessionRes

def ekycData(validationDataRaw, userSignData):

  print(len(validationDataRaw), validationDataRaw)

  if(len(validationDataRaw) <= 28):
    return {
      "faceResult": 'Pendiente revision',
      "name": {
        "ocrData": 'no encontrado',
        "ocrPercent": 0
      },
      "surname":{
        "ocrData": 'no encontrado',
        "ocrPercent": 0
      },
      "document": {
        "ocrData": 'no encontrado',
        "ocrPercent": 0
      },
      "authenticity": ''
    }

  dataDict = json.loads(validationDataRaw)

  data = {

  }

  face = dataDict['face_m4']['standard_fields']

  ocr = dataDict['ocr_m2']['standard_fields']

  validationExtra = dataDict['validation_m2']['standard_fields']

  if('test_face_recognition_ratio' in face):

    data['faceResult'] = 'Verificado' if face['test_face_recognition_ratio'] >= 0.5 else 'Pendiente revisión'
  else:
    data['faceResult'] = 'Pendiente revisión'

  if('name' in ocr):

    OCRname:str = ocr['name']
    OCRname = OCRname.lower()

    name = userSignData['nombre']
    name = name.lower()

    coincidence = extraerPorcentaje(OCRname, name)

    data['name'] = {
      "ocrData": OCRname,
      "ocrPercent": int(coincidence)
    }

  else:
    data['name'] = {
      "ocrData": '',
      "ocrPercent": 0
    }

  if('surname' in ocr):

    OCRsurnames = ocr['surname']

    normalizeSurname = ''

    if(len(OCRsurnames) >= 1):
      for surname in OCRsurnames:
        surnameLower:str = surname.lower()
        normalizeSurname += f"{surnameLower} "

    OCRsurname = normalizeSurname.strip()

    surname = userSignData['apellido']
    surname = surname.lower()

    coincidence = extraerPorcentaje(OCRsurname,surname)

    data['surname'] = {
      "ocrData": OCRsurname,
      "ocrPercent": int(coincidence)
    }

  else:
    data['surname'] =   {
      "ocrData": '',
      "ocrPercent": 0
    }


  if('document_number' in ocr):
    OCRdocument = ocr['document_number']
    document = userSignData['documento']

    coincidence = extraerPorcentaje(OCRdocument, document)

    data['document'] = {
      'ocrData': OCRdocument,
      'ocrPercent': int(coincidence)
    }
  else:
    data['document'] = {
      "ocrData": '',
      "ocrPercent": 0
    }


  if('test_global_authenticity_value' in validationExtra):
    aunthenticity = validationExtra['test_global_authenticity_value']

    data['authenticity'] = aunthenticity
  else:
    data['authenticity'] = ''

  return data