import re
from ultralytics import YOLO
from utilities.check_result import testingCountry, testingType
from ocr import  validateDocumentCountry, validateDocumentType
from PIL import Image
import base64
from io import BytesIO
import numpy as np

countryHash = {
  'COL': 'COLOMBIA',
  'HND': 'HONDURAS'
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
    "modelPath":'./models/colombia-v0.1.pt',
    "hasModel":True,
    "CEDULA DE CIUDADANIA": {
      "anverso": "CEDULA_CIUDADANIA_FRONTAL CEDULA_DIGITAL_FRONTAL",
      "reverso": "CEDULA_CIUDADANIA_REVERSO CEDULA_CIUDADANIA_REVERSOs CEDULA_DIGITAL_REVERSO CEDULA_DIGITAL_REVERSOs",
      "hasModel": True
    },
    "CEDULA DE EXTRANJERIA": {
      "anverso": "CEDULA_EXTRANJERIA_FRONTAL",
      "reverso": "CEDULA_EXTRANJERIA_REVERSO CEDULA_EXTRANJERIA_REVERSOs ",
      "hasModel": True
    },
    "CEDULA DIGITAL": {
      "anverso": "CEDULA_DIGITAL_FRONTAL",
      "reverso": "CEDULA_DIGITAL_REVERSOs CEDULA_DIGITAL_REVERSO",
      "hasModel": True
    },
    "PASAPORTE": {
      "anverso": "PASAPORTE",
      "reverso": "",
      "hasModel": True
    }
  },
  "HND": {
    "modelPath": "./models/honduras-v0.1.pt",
    "hasModel": True,
    "DNI":{
      "anverso": "dni_anverso",
      "reverso": "dni_reverso",
      "hasModel": True
    },
    "PASAPORTE": {
      "anverso": "",
      "reverso": "",
      "hasModel": False
    }
  }
}

def getLabelContent(data,labelName):

    for item in data:

        if item['label'] in labelName:
            return item['text']

    return 'no se pudo detectar'

def searchDocumentSelfie(yoloLabels, img, useCountry, documentType):
  """
  Detecta y recorta la fotografía del documento de identidad.

  Cascada de fallbacks (PUNTO 1.2 del plan de mejora):
    1. YOLO (label 'foto' / 'foto_persona')  — rápido y preciso cuando funciona
    2. InsightFace                            — robusto ante documentos deteriorados
    3. DeepFace (retinaface)                 — segundo fallback si InsightFace falla
    4. Imagen completa                       — último recurso (comportamiento original)

  El crop incluye un padding del 15% para evitar cortar frente/barbilla.
  """
  from reconocimiento import app as insightface_app  # importar el modelo ya cargado

  # Convertir a numpy si es PIL
  if isinstance(img, Image.Image):
    img_np = np.array(img)
  else:
    img_np = img

  def _crop_con_padding(img_arr: np.ndarray, x1: int, y1: int, x2: int, y2: int, padding: float = 0.15) -> np.ndarray:
    """Recorta la región con un padding proporcional para no cortar bordes del rostro."""
    h, w = img_arr.shape[:2]
    bw, bh = x2 - x1, y2 - y1
    pad_x = int(bw * padding)
    pad_y = int(bh * padding)
    x1c = max(0, x1 - pad_x)
    y1c = max(0, y1 - pad_y)
    x2c = min(w, x2 + pad_x)
    y2c = min(h, y2 + pad_y)
    return img_arr[y1c:y2c, x1c:x2c]

  # ── Paso 1: Detección YOLO ─────────────────────────────────────────────────
  modelPath = documentDetection[useCountry]['modelPath']
  if not hasattr(yoloLabels, "boxes"):
    results = yoloReader(img=img_np, modelPath=modelPath)
  else:
    results = yoloLabels

  for i, (box, cls) in enumerate(zip(results.boxes.xyxy, results.boxes.cls)):
    class_idx = int(cls)
    if hasattr(results, "names"):
      label = results.names[class_idx]
    elif isinstance(yoloLabels, dict) and 'names' in yoloLabels:
      label = yoloLabels['names'][class_idx]
    else:
      label = str(class_idx)

    if label.lower() in ["foto", "foto_persona"]:
      x1, y1, x2, y2 = map(int, box)
      cropped = _crop_con_padding(img_np, x1, y1, x2, y2)
      print("[searchDocumentSelfie] Rostro detectado con YOLO (paso 1).")
      return cropped

  # ── Paso 2: InsightFace como fallback ──────────────────────────────────────
  print("[searchDocumentSelfie] YOLO no detectó 'foto_persona'. Intentando con InsightFace (paso 2)...")
  try:
    import cv2 as _cv2
    img_bgr = _cv2.cvtColor(img_np, _cv2.COLOR_RGB2BGR) if img_np.shape[2] == 3 else img_np
    faces = insightface_app.get(img_bgr)
    if faces:
      # Tomar la cara con mayor det_score
      best_face = max(faces, key=lambda f: f.det_score)
      bbox = best_face.bbox.astype(int)
      x1, y1, x2, y2 = bbox[0], bbox[1], bbox[2], bbox[3]
      cropped = _crop_con_padding(img_np, x1, y1, x2, y2)
      print(f"[searchDocumentSelfie] Rostro detectado con InsightFace (paso 2). det_score={best_face.det_score:.3f}")
      return cropped
  except Exception as e:
    print(f"[searchDocumentSelfie] InsightFace fallback falló: {e}")

  # ── Paso 3: DeepFace como segundo fallback ─────────────────────────────────
  print("[searchDocumentSelfie] InsightFace falló. Intentando con DeepFace/retinaface (paso 3)...")
  try:
    from deepface import DeepFace
    import cv2 as _cv2
    img_bgr = _cv2.cvtColor(img_np, _cv2.COLOR_RGB2BGR) if img_np.shape[2] == 3 else img_np
    detected = DeepFace.extract_faces(
      img_path=img_bgr,
      detector_backend='retinaface',
      enforce_detection=False,
      align=False
    )
    if detected and detected[0].get('face') is not None:
      area = detected[0]['facial_area']
      x1 = area.get('x', 0)
      y1 = area.get('y', 0)
      x2 = x1 + area.get('w', 0)
      y2 = y1 + area.get('h', 0)
      if x2 > x1 and y2 > y1:
        cropped = _crop_con_padding(img_np, x1, y1, x2, y2)
        print("[searchDocumentSelfie] Rostro detectado con DeepFace/retinaface (paso 3).")
        return cropped
  except Exception as e:
    print(f"[searchDocumentSelfie] DeepFace fallback falló: {e}")

  # ── Paso 4: Último recurso — imagen completa ───────────────────────────────
  print("[searchDocumentSelfie] Todos los métodos fallaron. Devolviendo imagen completa (paso 4).")
  return img_np


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

    cropImage = None

    # Decide si el país tiene un modelo de detección basado en la configuración.
    has_model = documentDetection[user_country]["hasModel"]
    modelPath = documentDetection[user_country]['modelPath']
    documentHasModel = documentDetection[user_country][tipo_documento]["hasModel"]

    if has_model and documentHasModel:
        # Usar detectModel (flujo tipo COL)
        document_type, document_validation, country_code, country_detected, isCountry, croppedDocument, documentLabel = detectDocument(
            img=documento_data, countryCode=user_country, side=lado_documento, type=tipo_documento, yoloLabels=yoloLabels, modelPath=modelPath
        )

        if documentLabel is not None:
            labelLower = documentLabel.lower()
            labelSplit = labelLower.split('_')
            documentLabelNormalized = ' '.join(labelSplit)
        else:
            documentLabelNormalized = 'no detectado'
        # requieredSide ='reverso' if labelSplit[-1] == 'reverso' else 'frontal'
        documentSide = 'frontal' if lado_documento == 'anverso' else 'reverso'
        

        cropImage = croppedDocument

        documentSection = {
            'type': documentLabelNormalized.upper(),
            'typeCheck': document_validation,
            'isExpired': None,
            'code': country_code,
            'country': country_detected,
            'countryCheck': isCountry
        }

        checkSide['documentValidation'] = document_validation

        if not document_validation:
            messages.append(f'El tipo de documento no coincide con el seleccionado, documento detectado: {documentLabelNormalized}. se requiere {tipo_documento.lower()} {documentSide}')
            # if(requieredSide != documentSide):
            #   messages.append(f'se requiere que suba el {requieredSide} de su documento')
        if not isCountry:
          messages.append('El pais del documento no se encontro en el documento.')
        # if not isCountry:
        #     country_code_pre, country_detected_pre, doc_country_validation_pre = validateDocumentCountry(ocr, country=user_country)
        #     code_c, country_name, country_validation = testingCountry([
        #         {'country': country_code_pre, 'countryDetected': country_detected_pre, 'validation': doc_country_validation_pre}
        #     ])

        #     documentSection.update({'code': code_c, 'country': country_name, 'countryCheck': country_validation})
        #     checkSide['countryValidation'] = country_validation


        # else:
        #     documentSection.update({'code': country_code, 'country': country_detected, 'countryCheck': isCountry})
        #     checkSide['countryValidation'] = isCountry

        #     if documentSection['countryCheck'] != True:
        #         messages.append('El pais del documento no se encontro en el documento.')


    else:
        # Modo genérico basado en OCR/detección por texto
        type_detected_pre, document_type_validation_pre = validateDocumentType(
            tipo_documento, lado_documento, ocr, detectionData=ocr_data
        )
        document_type, document_validation = testingType([
            {'type': type_detected_pre, 'validation': document_type_validation_pre}
        ])
        country_code_pre, country_detected_pre, doc_country_validation_pre = validateDocumentCountry(ocr, country=user_country)
        code_c, country_name, country_validation = testingCountry([
                {'country': country_code_pre, 'countryDetected': country_detected_pre, 'validation': doc_country_validation_pre}
            ])

        checkSide['documentValidation'] = document_validation
        checkSide['countryValidation'] = country_validation

        documentSection = {
            'type': document_type,
            'typeCheck': document_validation,
            'isExpired': None,
            'code': code_c, 'country': country_name, 'countryCheck': country_validation
        }

        if not country_validation and tipo_documento != "PASAPORTE":
          messages.append('El pais del documento no se encontro en el documento.')

        if not document_validation and tipo_documento != "PASAPORTE":
            messages.append('El tipo de documento no coincide con el seleccionado.')

    return documentSection, checkSide, messages, cropImage

def checkModel(country):
  
  
  hasModel = documentDetection[country]["hasModel"]
  modelPath = documentDetection[country]["modelPath"]
  return hasModel, modelPath

def yoloReader(img, modelPath):
  yoloModel = YOLO(modelPath)

  results = yoloModel(img)[0]

  return results

def yoloTesting(img, modelPath, yoloLabels):
  results = yoloReader(img, modelPath)

  detected_classes = []
  data = []

  for i, (box, cls) in enumerate(zip(results.boxes.xyxy, results.boxes.cls)):
    class_idx = int(cls)
    label = yoloLabels[class_idx] if class_idx < len(yoloLabels) else str(class_idx)

    # Crop the image using the bounding box
    x1, y1, x2, y2 = map(int, box)
    cropped_img = None
    if hasattr(img, 'shape'):  # numpy array
      if img.shape[-1] == 3:
        cropped_img = Image.fromarray(img[y1:y2, x1:x2][..., ::-1])  # BGR to RGB
      else:
        cropped_img = Image.fromarray(img[y1:y2, x1:x2])
    else:
      if isinstance(img, Image.Image):
        cropped_img = img.crop((x1, y1, x2, y2))

    if cropped_img is not None:
      buffered = BytesIO()
      cropped_img.save(buffered, format="PNG")
      img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
      data_url = f"data:image/png;base64,{img_str}"
    else:
      data_url = None

    detected_classes.append(label)
    data.append({"label": label, "crop": data_url})

  return data, detected_classes

def detectDocument(img, countryCode: str, side: str, type: str, yoloLabels: list[str], modelPath: str):
  documentClass = documentDetection[countryCode][type][side]
  documentClass = documentClass.split(" ")

  country = countryHash[countryCode]

  results = yoloReader(img=img, modelPath=modelPath)

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

      return type, True, countryCode, country, True, data_url, classes

  # Si no se detectó ninguna clase exacta, buscar etiquetas que comiencen con CEDULA o PASAPORTE
  for detected in detected_classes:
    if detected.upper().startswith("CEDULA") or detected.upper().startswith("PASAPORTE"):
      return detected, False, countryCode, country, True, None, detected

  return "no detectado", False, "no detectado", "no detectado", False, None, None

def detectDocumentStand(img, countryCode: str, side: str, type: str, yoloLabels: list[str], modelPath: str):

  documentClass = documentDetection[countryCode][type][side]
  documentClass = documentClass.split(" ")

  country = countryHash[countryCode]

  results = yoloReader(img=img, modelPath=modelPath)

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

      return type, True, countryCode, country, True, data_url, classes

  # Si no se detectó ninguna clase exacta, buscar etiquetas que comiencen con CEDULA o PASAPORTE
  for detected in detected_classes:
    if detected.upper().startswith("CEDULA") or detected.upper().startswith("PASAPORTE"):
      return type, False, countryCode, country, True, None, detected

  return "no detectado", False, "no detectado", "no detectado", False, None, None


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

def detection(img, classes:list[str], country):
  """
  Detects objects in an image using a YOLO model and returns their labels and crop coordinates.
  Args:
    img: The input image to process.
    classes (list[str]): List of class names corresponding to the model's output classes.
    country: The country key used to select the appropriate YOLO model path from `documentDetection`.
  Returns:
    list[dict]: A list of dictionaries, each containing:
      - "label": The detected class label (str).
      - "crop": The coordinates of the crop as [[y1, y2], [x1, x2]], where:
        - x1, y1: Top-left corner of the bounding box.
        - x2, y2: Bottom-right corner of the bounding box.
        - The width of the box is (x2 - x1).
        - The height of the box is (y2 - y1).
  """

  modelPath = documentDetection[country]['modelPath']

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
