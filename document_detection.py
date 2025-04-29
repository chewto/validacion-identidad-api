import re
from ultralytics import YOLO
from ocr import ocr

documentClasses = {
  "HND": {
    "DNI": {
          "classes": ['dni_anverso','nombre','apellido','numero_documento',
               'fecha_nacimiento','fecha_expiracion','tipo_documento',
               'foto_persona','firma','nacionalidad','lugar_nacimiento','ghost',"dni_reverso", "codigo_datamatrix","codigo_barras","codigo_qr","domicilio","mrz"],
          "sides":{
            "anverso": {"class": "dni_anverso", "valClasses": ['dni_anverso','nombre','apellido','numero_documento',
               'fecha_nacimiento','fecha_expiracion','tipo_documento',
               'foto_persona','firma','nacionalidad','lugar_nacimiento','ghost']},
            "reverso": {"class":"dni_reverso","valClasses": ["dni_reverso", "codigo_datamatrix","codigo_barras","codigo_qr","domicilio","mrz"]}
          },
          "classesOcr": [
            "nombre", "apellido", "numero_documento", "fecha_expiracion", "tipo_documento","mrz"
          ]
    }
  }
}


modelPath = '../models/modelo-m-uni.pt'

def getClasses(country:str ,side:str, type:str):
  
  documentClass = documentClasses[country][type]['classes']
  documentOcr = documentClasses[country][type]['classesOcr']
  documentSide = documentClasses[country][type]['sides'][side]['class']
  documentVal = documentClasses[country][type]['sides'][side]['valClasses']

  return documentClass, documentSide, documentOcr, documentVal

def verifyDocument(classes:list[str], labels:list[str], side:str):
  classesLength = len(classes)
  coincidence = False
  if labels == 0:
      return False

  matchedLabels = set(labels) & set(classes)
  percentage = (len(matchedLabels) / classesLength) * 100

  for label in labels:
    if(label == side):
      coincidence = True

  if(percentage >= 80 and coincidence):
    return True, coincidence
  else:
    return False, coincidence


def getForename(data):
  
  foreName = [entry for entry in data if entry["class"] == 'nombre']

  if(len(foreName) <= 0):
    return None, False

  foreName = foreName[0]
  foreName = foreName['dataOcr']

  cleanName = cleanNames(foreName)

  return cleanName, True

def getSurname(data):

  surName = [entry for entry in data if entry["class"] == 'apellido']
  if(len(surName) <= 0):
    return None, False
  surName = surName[0]
  surName = surName['dataOcr']

  cleanSurname = cleanNames(surName)

  return cleanSurname, True

def cleanNames(input):
  parts = input.split()
  if len(parts) < 2:
    return input
  return ' '.join(parts[-2:])

def getID(data):

  iD = [entry for entry in data if entry["class"] == 'numero_documento']
  if(len(iD) <= 0):
    return None, False
  iD = iD[0]
  iD = iD['dataOcr']

  cleanID = cleanId(iD)
    
  return cleanID, True

def cleanId(input_text):
    patterns = re.findall(r'\s\d+', input_text)

    arrayTerms = []

    for pattern in patterns:
      pattern = pattern.strip()
      if(len(pattern) == 4 or len(pattern) == 5):
        arrayTerms.append(pattern)

    clean = ' '.join(arrayTerms)

    return clean

def getExpiry(data):
    
  expiry = [entry for entry in data if entry["class"] == 'fecha_expiracion']
  if(len(expiry) <= 0):
    return ''
  expiry = expiry[0]
  expiry = expiry['dataOcr']

  expiryCleaned = cleanExpiry(expiry)

  return expiryCleaned

def cleanExpiry(input):

  patterns = re.findall(r"\b\d{2}[- ]\d{2}[- ]\d{4}\b", input)

  return patterns

def getCountry(data):
  country = [entry for entry in data if entry["class"] == "tipo_documento"]
  if(len(country) <= 0):
    return ''
  country = country[0]
  country = country['dataOcr']
  return country

def getMrz(data):
  mrz = [entry for entry in data if entry["class"] == "mrz"]
  if(len(mrz) <= 0):
    return 'Requiere verificar – DATOS INCOMPLETOS'
  mrz = mrz[0]
  mrz = mrz['dataOcr']
  return mrz

def detection(img, classes:list[str], classesOcr:list[str]):

  yoloModel = YOLO(modelPath)

  results = yoloModel(img)[0]

  data = []
  labels = []

  for i, (box, score, cls) in enumerate(zip(results.boxes.xyxy, results.boxes.conf, results.boxes.cls)):
                x1, y1, x2, y2 = map(int, box)

                label = classes[int(cls)] if int(cls) < len(classes) else str(int(cls))
                labels.append(label)

                cropImage = img[y1:y2, x1:x2]

                for ocrLabel in classesOcr:
                  if(ocrLabel == label):

                    ocrResult, ocrLines = ocr(cropImage, preprocesado=True)

                    texts = ' '.join(ocrLines)

                    data.append({"class": label, "dataOcr": texts, "coords":[x1,y1,x2,y2]})

  return labels, data
