import requests
import base64
import json

from ocr import extraerPorcentaje

user = {
    "login": "honducert_test",
    "password":"XaG7,9K.iR"
}
userBackOffice = {
  "login": "backoffice_test_hon",
  "password":"MmiA{uX44."
}

# # this will generate the admin token

# user = {
#     "login": "honducert_video",
#     "password":"tVR-R-!03U"
# }
# userBackOffice = {
#   "login": "agente_hchon",
#   "password":"{A3g(,fTN1"
# }

# this will generate the admin token

# user = {
#     "login": "clinpays_ekyctest",
#     "password":"zdU62r{Z._9jYQNa"
# }

# userBackOffice = {
#   "login": "clinpays_ekyctest",
#   "password":"zdU62r{Z._9jYQNa"
# }

baseURL = 'https://ekycvideoapiwest-test.lleida.net/api'

videoURL = f'{baseURL}/rest/auth/get_video_token'

sessionVideoURL = f'{baseURL}/rest/standalone/create_session'

adminURL = f'{baseURL}/rest/auth/get_admin_token'

mediURL = f'{baseURL}/rest/admin/get_media'

sessionURL = f'{baseURL}/rest/admin/get_session'

def getRequest(url):
  try:
    res = requests.get(url=url)
    
    return res.json()

  except requests.RequestException as e:
    return {

    }

def postRequest(url, headers, data):

  try:
    res = requests.post(url=url, json=data, headers=headers)
    return res.json()
  except requests.RequestException as e:
    return {

    }

def getAdminToken():

  adminRes = postRequest(url=adminURL, data=userBackOffice, headers={})

  errorCodes = ['400.0', '404.0','403.0']

  token = adminRes['adminToken']

  if(adminRes['status'] in errorCodes and adminRes['code'] in errorCodes):
    return False
  
  return token

def getSessionStatus(callId, auth):

  errorCodes = ['400.0', '404.0']

  headers = {
    'Content-Type': 'application/json',
    'Authorization': f"Bearer {auth}"
  }

  sessionRes = postRequest(url=sessionURL, data={"callId":callId}, headers=headers)

  if(sessionRes['status'] in errorCodes and sessionRes['code'] in errorCodes):
    return 'No verificado'

  if(sessionRes['data'][0]['status'] == 'POSITIVE'):
    return 'Verificado'
  else:
    return 'No verificado'


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
  errorCodes = ['400.0', '404.0', '401.0']

  videoRes = postRequest(url=videoURL,data=user, headers={})

  if(videoRes['status'] in errorCodes and videoRes['code'] in errorCodes):
    return 'invalido'

  token = videoRes['adminToken']

  if(len(token) <= 0):
    return ''

  return token

def getSession(sessionData, sessionHeaders):

  errorCodes = ['400.0', '404.0', '401.0']

  sessionRes = postRequest(url=sessionVideoURL, data=sessionData, headers=sessionHeaders)

  if(sessionRes['status'] in errorCodes and sessionRes['code'] in errorCodes):
    return {
      "riuSessionId": "",
      "callToken": "",
      "mediaServerUrl": "",
      "riuCoreUrl": ""
    }

  return sessionRes

def ekycDataDTO(validationDataRaw, userSignData):

  if(len(validationDataRaw) <= 28):
    return {
      "faceResult": False,
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
      }
    }

  dataDict = json.loads(validationDataRaw)

  data = {

  }

  face = dataDict['face_m4']['standard_fields']

  ocr = dataDict['ocr_m2']['standard_fields']

  if('test_face_recognition_ratio' in face):

    data['faceResult'] = True if face['test_face_recognition_ratio'] >= 0.5 else False
  else:
    data['faceResult'] = False

  if('name' in ocr):

    OCRname:str = ocr['name']
    OCRname = OCRname.lower()

    name = userSignData['nombre']
    name = name.lower()

    coincidence = extraerPorcentaje(OCRname, name)

    if(coincidence >= 50.0):
      data['name'] = {
        "ocrData": OCRname,
        "ocrPercent": int(coincidence)
      }
    else:
      data['name'] = {
        "ocrData": 'no encontrado',
        "ocrPercent": 0
      }

  else:
    data['name'] = {
      "ocrData": 'no encontrado',
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

    if(coincidence >= 50.0):

      data['surname'] = {
        "ocrData": OCRsurname,
        "ocrPercent": int(coincidence)
      }
    else:
      data['surname'] =   {
      "ocrData": 'no encontrado',
      "ocrPercent": 0
    }

  else:
    data['surname'] =   {
      "ocrData": 'no encontrado',
      "ocrPercent": 0
    }


  if('document_number' in ocr):
    OCRdocument = ocr['document_number']
    document = userSignData['documento']

    coincidence = extraerPorcentaje(OCRdocument, document)

    if(coincidence >= 50.0):
      data['document'] = {
        'ocrData': OCRdocument,
        'ocrPercent': int(coincidence)
      }

    else:
      data['document'] = {
        "ocrData": 'no encontrado',
        "ocrPercent": 0
      }
  else:
    data['document'] = {
      "ocrData": 'no encontrado',
      "ocrPercent": 0
    }

  return data

def ekycRules(rulesDict):

  if(rulesDict == 'no se encontro la validación'):
    return rulesDict, False

  rulesData = []

  approvedRulesCount = 0
  deniedRulesCount = 0

  dataDictionary = json.loads(rulesDict)

  rules = dataDictionary['validation_m2']
  standardFields = rules['standard_fields']

  rulesJson = json.dumps(rules)

  for key in standardFields:
    value = standardFields.get(key)

    if(isinstance(value, float)):
      floatValues = True if value >= 0.5 else False
      rulesData.append(floatValues)

    if(isinstance(value, int)):
      intValues = True if value >= 1 else False
      rulesData.append(intValues)

    if(isinstance(value, str)):
      strValues = True if value == 'OK' else False
      rulesData.append(strValues)

  for rule in rulesData:
    if(rule):
      approvedRulesCount += 1
    else:
      deniedRulesCount += 1

  if(approvedRulesCount >= deniedRulesCount):
    return rulesJson, True
  else:
    return rulesJson, False
  