import re
from ultralytics import YOLO
from check_result import testingCountry, testingType
from ocr import ocr, validateDocumentCountry, validateDocumentType
from PIL import Image
import base64
from io import BytesIO

countryHash = {
  'COL': 'COLOMBIA'
}

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



documentDetection = {
  "COL":{
    "hasModel":True,
    "CEDULA DE CIUDADANIA": {
      "anverso": "CEDULA_CIUDADANIA_FRONTAL CEDULA_DIGITAL_FRONTAL",
      "reverso": "CEDULA_CIUDADANIA_REVERSO CEDULA_CIUDADANIA_REVERSOs CEDULA_DIGITAL_REVERSO CEDULA_DIGITAL_REVERSOs"
    },
    "CEDULA DE EXTRANJERIA": {
      "anverso": "CEDULA_EXTRANJERIA_FRONTAL",
      "reverso": "CEDULA_EXTRANJERIA_REVERSO CEDULA_EXTRANJERIA_REVERSOs "
    },
    "CEDULA DIGITAL": {
      "anverso": "CEDULA_DIGITAL_FRONTAL",
      "reverso": "CEDULA_DIGITAL_REVERSOs CEDULA_DIGITAL_REVERSO"
    },
    "PASAPORTE": {
      "anverso": "PASAPORTE",
      "reverso": ""
    }
  },
  "HND": {
    "hasModel": False
  }
}


modelPath = './models/colombia-v0.1.pt'

def validateDocument(documento_data, ocr, tipo_documento, lado_documento, user_country, ocr_data, yoloLabels):
    """Función unificada para detección y validación de documentos.

    - Si `country_config` está presente y para `user_country` tiene `has_model=True`,
      se usa `detectDocument` (modelo de detección) y se realiza validación de país
      y tipo similar al flujo antiguo de COL.
    - Si `has_model` es False (o no hay country_config), se cae al modo genérico
      que valida el tipo de documento con OCR/`validateDocumentType` y `testingType`.

    Devuelve: (document_section_dict, check_side_updates, messages_list)
    """
    messages = []
    checkSide = {}

    # Decide si el país tiene un modelo de detección basado en la configuración.
    has_model = documentDetection[user_country]["hasModel"]


    if has_model:
        # Usar detectModel (flujo tipo COL)
        document_type, document_validation, country_code, country_detected, isCountry, _ = detectDocument(
            img=documento_data, countryCode=user_country, side=lado_documento, type=tipo_documento, yoloLabels=yoloLabels
        )

        documentSection = {
            'type': document_type,
            'typeCheck': document_validation,
            'isExpired': None,
        }

        print(document_type, document_validation)

        checkSide['documentValidation'] = document_validation

        if isCountry != 'OK':
            country_code_pre, country_detected_pre, doc_country_validation_pre = validateDocumentCountry(ocr, country=user_country)
            code_c, country_name, country_validation = testingCountry([
                {'country': country_code_pre, 'countryDetected': country_detected_pre, 'validation': doc_country_validation_pre}
            ])

            documentSection.update({'code': code_c, 'country': country_name, 'countryCheck': country_validation})
            checkSide['countryValidation'] = country_validation

            if country_validation != 'OK':
                messages.append('El pais del documento no se encontro en el documento.')

        else:
            documentSection.update({'code': country_code, 'country': country_detected, 'countryCheck': isCountry})
            checkSide['countryValidation'] = isCountry

            if documentSection['countryCheck'] != 'OK':
                messages.append('El pais del documento no se encontro en el documento.')

        if document_validation != 'OK':
            messages.append('El tipo de documento no coincide con el seleccionado.')

    else:
        # Modo genérico basado en OCR/detección por texto
        type_detected_pre, document_type_validation_pre = validateDocumentType(
            tipo_documento, lado_documento, ocr, detectionData=ocr_data
        )
        document_type, document_validation = testingType([
            {'type': type_detected_pre, 'validation': document_type_validation_pre}
        ])

        checkSide['documentValidation'] = document_validation

        documentSection = {
            'type': document_type,
            'typeCheck': document_validation,
            'isExpired': None
        }

        if document_validation != 'OK':
            messages.append('El tipo de documento no coincide con el seleccionado.')

    return documentSection, checkSide, messages

def checkModel(country):
  return documentDetection[country]["hasModel"]

def detectDocument(img, countryCode: str, side: str, type: str, yoloLabels: list[str]):
  documentClass = documentDetection[countryCode][type][side]
  documentClass = documentClass.split(" ")

  country = countryHash[countryCode]

  # Cargar el modelo YOLO
  yoloModel = YOLO(modelPath)

  # Definir las clases a detectar
  # labels = [
  #   "CEDULA_CIUDADANIA_FRONTAL",
  #   "NUMERO_DOCUMENTO",
  #   "APELLIDOS",
  #   "NOMBRES",
  #   "FIRMA",
  #   "FOTO",
  #   "ENCABEZADO",
  #   "CEDULA_CIUDADANIA_REVERSO",
  #   "CODIGO_BARRAS",
  #   "HUELLA",
  #   "FECHA_NACIMIENTO",
  #   "LUGAR_NACIMIENTO",
  #   "ESTATURA",
  #   "GRUPO_SANGUINEO",
  #   "SEXO",
  #   "FECHA_EXPEDICION",
  #   "CODIGO",
  #   "CEDULA_EXTRANJERIA_FRONTAL",
  #   "NACIONALIDAD",
  #   "FECHA_EXPIRACION",
  #   "GHOST",
  #   "CEDULA_EXTRANJERIA_REVERSO",
  #   "MRZ",
  #   "CEDULA_DIGITAL_FRONTAL",
  #   "CEDULA_DIGITAL_REVERSO",
  #   "PASAPORTE",
  #   "NUMERO_PERSONAL",
  #   "AUTORIDAD",
  #   "CODIGO_PAIS",
  #   "TIPO",
  #   "CODIG_BARRAS_LATERAL",
  #   "NUMERO_LATERAL",
  #   "NUMERO_PASAPORTE"
  # ]

  results = yoloModel(img)[0]

  detected_classes = set()
  cropped_img = None

  for i, (box, cls) in enumerate(zip(results.boxes.xyxy, results.boxes.cls)):
    class_idx = int(cls)
    label = yoloLabels[class_idx] if class_idx < len(yoloLabels) else str(class_idx)
    detected_classes.add(label)
    if label in documentClass and cropped_img is None:
      # Recortar la imagen usando las coordenadas del bounding box
      x1, y1, x2, y2 = map(int, box)
      # Si img es un path, cargar con cv2 o PIL
      if hasattr(img, 'shape'):  # numpy array
        # Convertir a RGB si es necesario
        if img.shape[-1] == 3:
          cropped_img = Image.fromarray(img[y1:y2, x1:x2][..., ::-1])  # BGR a RGB
        else:
          cropped_img = Image.fromarray(img[y1:y2, x1:x2])
      else:
        try:
          if isinstance(img, Image.Image):
            cropped_img = img.crop((x1, y1, x2, y2))
        except ImportError:
          cropped_img = None

  for classes in documentClass:
    if classes in detected_classes:
      if cropped_img is not None:
        # Convert cropped_img to PIL Image if it's a numpy array
        if not isinstance(cropped_img, Image.Image):
          cropped_img = Image.fromarray(cropped_img)
        buffered = BytesIO()
        cropped_img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        data_url = f"data:image/png;base64,{img_str}"
      else:
        data_url = None

      return type, "OK", countryCode, country, "OK", data_url

  return "no detectado", "!OK", "no detectado", "no detectado", "!OK", None

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
    return '', False

  foreName = foreName[0]
  foreName = foreName['dataOcr']

  cleanName = cleanNames(foreName)

  return cleanName, True

def getSurname(data):

  surName = [entry for entry in data if entry["class"] == 'apellido']
  if(len(surName) <= 0):
    return '', False
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
    return '', False
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
  print(expiry)

  expiryCleaned = cleanExpiry(expiry)

  return expiryCleaned

def cleanExpiry(input):

  patterns = re.findall(r"\b\d{2}[- ]\d{2}[- ]\d{4}\b", input)

  if not patterns:
    patterns = re.findall(r"\b\d{2}\s*[-]\s*\d{2}\s*\d{4}\b", input)

  if not patterns:
    patterns = re.findall(r"\b\d{2}\s*[-]\s*\d{2}\s*[-]\s*\d{4}\b", input)

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
    return 'Requiere verificar – DATOS INCOMPLETOS', False
  mrz = mrz[0]
  mrz = mrz['dataOcr']
  return mrz, True

def detection(img, classes:list[str]):

  yoloModel = YOLO(modelPath)

  results = yoloModel(img)[0]

  data = []
  # labels = []

  for i, (box, score, cls) in enumerate(zip(results.boxes.xyxy, results.boxes.conf, results.boxes.cls)):
                x1, y1, x2, y2 = map(int, box)

                label = classes[int(cls)] if int(cls) < len(classes) else str(int(cls))

                cropImage = [[y1,y2],[ x1,x2]]

                data.append({"label": label, "crop": cropImage})

                # labels.append(label)
                # for ocrLabel in classesOcr:
                #   if(ocrLabel == label):

                #     ocrResult, ocrLines = ocr(cropImage, preprocesado=True)

                #     texts = ' '.join(ocrLines)

                #     data.append({"class": label, "dataOcr": texts, "coords":[x1,y1,x2,y2]})


  return data
  # return labels, data
