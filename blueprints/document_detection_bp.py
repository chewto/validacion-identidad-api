import json
from flask import Blueprint, request, jsonify
from ultralytics import YOLO
from utilities.check_result import results, testingCountry
import request.controlador_db as controlador_db
from expiry import expiryDateDetection, expiryDateOCR, hasExpiryDate
from utilities.formatter import _formatDocumentNumber
from lector_codigo import barcodeReader, barcodeSide, rotateBarcode
from mrz import MRZSide, comparisonMRZInfo, extractMRZ, mrzInfo
from ocr import validacionOCR, validateDocumentCountry, validateDocumentType
from reconocimiento import extractFaces, orientacionImagen, verifyFaces
from utilities.request_parser import _parse_request
from utilities.utilidades import fileCv2, imageToDataURL, readDataURL, textNormalize
import document_detection
import numpy as np

document_detection_bp = Blueprint('document', __name__, url_prefix="/document")

confidenceValue = 0.6


@document_detection_bp.route('/detection', methods=['POST', 'GET'])
def documentDetection():

    testing = request.args.get("testing", "false").lower() == "true"

    documentType = request.args.get("documento")
    documentSide = request.args.get("lado")


    if (documentType == 'PASAPORTE'):
        document = 'PASAPORTE'

    if testing:
        image = request.files.get("image", None)
        country = request.form.get('country')
        imageData = fileCv2(image)
    else:
        data = request.get_json()
        country = data['country']
        imageData = readDataURL(data["image"])

    if (country == "HND"):
        if (documentSide == 'FRONTAL'):
            documentSide = 'ANVERSO'

    document = f'{documentType}_{documentSide}'.upper()

    if ('PASAPORTE' in documentType):
        return jsonify({
          "documentoValido": True,
        }), 200

    print(document)

    countryData = controlador_db.selectData(f'''
        SELECT yolo_labels, tipo_documento_validacion  FROM pki_validacion.pais as pais
        WHERE pais.codigo = "{country}"''', ())

    yoloLabels = countryData[0]
    # documents = countryData[1]
    yoloLabels = yoloLabels.upper()
    yoloLabels = yoloLabels.split(',')

    results = document_detection.detection(imageData, yoloLabels, country)

    crops = []
    labels = []
    isDocument = False

    for result in results:
        labels.append(result['label'])

        if 'CEDULA_DIGITAL' in result['label'] and documentType in 'CEDULA_CIUDADANIA':
            document = f'CEDULA_DIGITAL_{documentSide}'

        if document in result['label'] or 'FOTO' in result['label']:

            crop = {
              "left": int(result['crop'][1][0]),
              "right": int(result['crop'][1][1]),
              "top": int(result['crop'][0][0]),
              "bottom": int(result['crop'][0][1])
            }
            # Recortar la imagen y convertir a base64

            crops.append({
              "etiqueta": result['label'],
              "recorte": crop,
            })

    if document in labels:
        isDocument = True

    return jsonify({
        "documentoValido": isDocument,
        "etiquetas": labels,
        "recortes": crops
    }), 200

@document_detection_bp.route('/validate', methods=['POST', 'GET'])
def validate():

  parsed = _parse_request(request)

  selfie = parsed['persona_data']
  documentImage = parsed['documento_data']
  efirmaId = parsed['efirma_id']
  name = parsed['nombre']
  surname = parsed['apellido']
  documentNumber = parsed['numero_documento']
  documentType = parsed['tipo_documento']
  documentSide = parsed['lado_documento']
  country = parsed["user_country"]
  tries = parsed["tries"]
  ocr = parsed["ocr"]

  print(country)


  confidenceThreshold = 0.65
  


  documentSide = request.args.get("side", None)


  resultsDict = {
    "barcode": None,
    # "confidence": 0.99,
    "document": {
        "code": "",
        "country": "",
        "countryCheck": "",
        "isExpired": None,
        "type": "",
        "typeCheck": ""
    },
    # "face": False,
    "image": "",
    "mrz": {
        "code": None,
        "data": {
            "lastName": "",
            "name": ""
        },
        "percentages": {
            "lastName": 0,
            "name": 0
        }
    },
    "ocr": {
        "data": {
            "ID": "",
            "lastName": "",
            "name": ""
        },
        "percentage": {
            "ID": 0,
            "lastName": 0,
            "name": 0
        }
    },
  }
  messages = []
  checkSide = {}

  countryData = controlador_db.selectData(f'''
      SELECT barcode, mrz, yolo_labels FROM pki_validacion.pais as pais 
      WHERE pais.codigo = "{country}"''', ())
  
  
  barcodeData = json.loads(countryData[0])
  mrzData = json.loads(countryData[1])
  yoloLabels = countryData[2]
  yoloLabels = yoloLabels.split(',')

  face = False

  if(documentSide == 'anverso'):
    print('es un anverso')

    documentSelfie = document_detection.searchDocumentSelfie(yoloLabels=yoloLabels,img=documentImage, useCountry=country, documentType=documentType)
    _, confidence, _ = verifyFaces(selfie, documentSelfie)
    resultsDict['face'] = True if confidence <= confidenceThreshold else False
    face = True if confidence <= confidenceThreshold else False
    resultsDict['confidence'] = confidence

    extractFace = extractFaces(documentImage, anti_spoofing=False)

    if (extractFace):
      for face in extractFace:
        faceDetected = face.get('detected')
        resultsDict['faceDetected'] = faceDetected
        checkSide['faceDetected'] = faceDetected

    formatedDocumentNumber = _formatDocumentNumber(documentNumber)
    documentNumberExtracted = document_detection.getLabelContent(data=ocr, labelName='NUMERO_DOCUMENTO')

    name = textNormalize(name)
    nameExtracted = document_detection.getLabelContent(data=ocr, labelName='NOMBRES NOMBRESs')

    surname = textNormalize(surname)
    surnameExtracted = document_detection.getLabelContent(data=ocr, labelName='APELLIDOS APELLIDOSs')

    nameOcr, pctName = validacionOCR(nameExtracted, name, onlyNumbers=False)
    surnameOcr, pctSurname = validacionOCR(surnameExtracted, surname, onlyNumbers=False)
    IdNumberOcr, pctNumber = validacionOCR(documentNumberExtracted, formatedDocumentNumber, onlyNumbers=True)

    checkSide['percentName'] = True if pctName >= 50 else False
    checkSide['percentLastname'] = True if pctSurname >= 50 else False
    checkSide['percentID'] = True if pctNumber >= 50 else False

    resultsDict['ocr']['data']['ID'] = IdNumberOcr
    resultsDict['ocr']['data']['lastName'] =surnameOcr
    resultsDict['ocr']['data']['name'] =nameOcr

    resultsDict['ocr']['percentage']['ID'] = pctNumber
    resultsDict['ocr']['percentage']['lastName'] = pctSurname
    resultsDict['ocr']['percentage']['name'] = pctName


  countryHasModel, modelPath = document_detection.checkModel(country=country)

  if(countryHasModel):
    documentTypeDetected, documentValidation, countryCode, countryDetected, isCountry, croppedImage,documentLabel = document_detection.detectDocumentStand(
        img=documentImage, countryCode=country, side=documentSide, type=documentType, yoloLabels=yoloLabels, modelPath=modelPath
      )
    
    checkSide['countryValidation'] = isCountry
    checkSide['documentValidation'] = documentValidation

    resultsDict['document'] = {
        'type': documentTypeDetected,
        'typeCheck': documentValidation,
        'isExpired': None,
        "code": countryCode,
        "country": countryDetected,
        "countryCheck": isCountry,
    }
    
    resultsDict['image'] = croppedImage if croppedImage is not None else imageToDataURL(documentImage)


  hasbarcode,barcodeType,barcodetbr  = barcodeSide(documentType=documentType, documentSide=documentSide, barcodeData=barcodeData)
  barcodeIsOptional = barcodeData[documentType]["optional"]

  if hasbarcode:
      detectedBarcodes = barcodeReader(documentImage, efirmaId, documentSide, barcodeType, barcodetbr)
      detectedBarcodes = True if (len(detectedBarcodes) >= 1) else False

      if barcodeIsOptional:
        if detectedBarcodes:
          resultsDict['barcode'] = detectedBarcodes
          checkSide['barcode'] = detectedBarcodes
      else:
        resultsDict['barcode'] = detectedBarcodes
        checkSide['barcode'] = detectedBarcodes
        if not detectedBarcodes:
          messages.append('No se pudo detectar el código de barras del documento.')

  mrzLetter, documentMRZ = MRZSide(documentType=documentType, documentSide=documentSide, mrzData=mrzData)

  mrzIsOptional = mrzData[documentType]['optional']

  if documentMRZ:
      mrz = extractMRZ(documentImage)

      if (mrz == "No se pudo detectar MRZ válido en la imagen." and not mrzIsOptional):
        messages.append('No se pudo detecar el código mrz del documento.')

      if 'valid_score' in mrz:
        if mrz['valid_score'] >= 51:
          extractName = mrzInfo(mrz=mrz['raw_text'].replace("\n", "") if 'raw_text' in mrz else '', searchTerm=name)
          extractLastname = mrzInfo(mrz=mrz['raw_text'].replace("\n", "") if 'raw_text' in mrz else '', searchTerm=surname)

          nameMRZ = comparisonMRZInfo([extractName], name, 'name')
          lastNameMRZ = comparisonMRZInfo([extractLastname], surname, 'surname')

          # Si MRZ no es opcional, siempre se agrega. Si es opcional, solo si se detecta.
          if (not mrzIsOptional) or (mrzIsOptional and 'raw_text' in mrz):
            resultsDict['mrz'] = {
              'code': mrz['raw_text'] if 'raw_text' in mrz else 'No se pudo detectar MRZ válido en la imagen.',
              'data': {
                'name': nameMRZ['data'] if len(nameMRZ['data']) >= 1 else '',
                'lastName': lastNameMRZ['data'] if len(lastNameMRZ['data']) >= 1 else ''
              },
              'percentages': {
                'name': nameMRZ['percent'],
                'lastName': lastNameMRZ['percent']
              }
            }

          # Si MRZ no es opcional, siempre se agregan los checks y mensajes
          if not mrzIsOptional:
            checkSide['nameMrz'] = True if nameMRZ['percent'] >= 51 else False
            checkSide['lastNameMrz'] = True if lastNameMRZ['percent'] >= 51 else False
            if nameMRZ['percent'] <= 50 and 'raw_text' in mrz:
              messages.append('No se encontró el nombre en el codigo mrz.')
            if lastNameMRZ['percent'] <= 50 and 'raw_text' in mrz:
              messages.append('No se encontró el apellido en el codigo mrz.')
          # Si MRZ es opcional, solo se agregan los checks si cumplen el porcentaje, no se agregan mensajes
          elif mrzIsOptional and 'raw_text' in mrz:
            if nameMRZ['percent'] >= 51:
              checkSide['nameMrz'] = True
            if lastNameMRZ['percent'] >= 51:
              checkSide['lastNameMrz'] = True
        else:
          # Si MRZ no es opcional, siempre se agrega aunque el score sea bajo
          if not mrzIsOptional:
            resultsDict['mrz'] = {
              'code': "No se pudo detectar MRZ válido en la imagen.",
              'data': {
                'name': '',
                'lastName': ''
              },
              'percentages': {
                'name': 0,
                'lastName': 0
              }
            }

            messages.append('No se pudo detecar el código mrz del documento.')
            checkSide['nameMrz'] = False
            checkSide['lastNameMrz'] = False
  # else:
  #   print()

  resultsDict['messages'] = messages

  validSide, _, _ = results(49, 'AUTOMATICA', checkSide)

  if(documentSide == 'anverso'):
    resultsDict['validSide'] = validSide if face else False 
  else:
    resultsDict['validSide'] = validSide

  return resultsDict



# @document_bp.route('/front', methods=['POST'])
# def front():

#   # efirmaId = request.form.get('id')
#   # selfieImage = request.files.get('selfie')
#   # documentImage = request.files.get('document')
#   # documentSide = request.form.get('documentSide')
#   # documentType = request.form.get('documentType')
#   # userCountry = request.form.get('country')
#   # selfieData = fileCv2(selfieImage)
#   # documentImageData = fileCv2(documentImage)

#   reqBody = request.get_json()

#   efirmaId = reqBody['id']
#   selfieImage = reqBody['imagenPersona']
#   documentImage = reqBody['imagen']
#   documentSide = reqBody['ladoDocumento']
#   documentType = reqBody['tipoDocumento']
#   userCountry = reqBody['country']
#   selfieData = readDataURL(selfieImage)
#   documentImageData = readDataURL(documentImage)

#   countryData = controlador_db.selectData(f'''
#       SELECT * FROM pki_validacion.pais as pais 
#       WHERE pais.codigo = "{userCountry}"''', ())
  
#   print(countryData)

#   mrzData = json.loads(countryData[3])
#   barcodeData = json.loads(countryData[4])
#   ocrData = json.loads(countryData[5])

#   messages = []

#   #Face comparison

#   orientedSelfie, _ = orientacionImagen(selfieData)

#   orientedDocument, _ = orientacionImagen(documentImageData)

#   _, confidence, _ = verifyFaces(orientedSelfie, orientedDocument)

#   if(confidence >= confidenceValue):
#       messages.append('Los rostros no coincidén.')

#   #YOLO usage
#   classes, side, ocr, val = document_detection.getClasses(userCountry, documentSide, documentType)
#   labels, data = document_detection.detection(documentImageData, classes=classes, classesOcr=ocr)


#   documentVerify, typeCoincidence = document_detection.verifyDocument(classes=val, labels=labels, side=side)

#   getName, detectedName = document_detection.getForename(data)
#   getSurname, detectedSurName = document_detection.getSurname(data)
#   getID, detectedID = document_detection.getID(data)
#   getExpiryDate = document_detection.getExpiry(data)
#   getCountry = document_detection.getCountry(data)

#   countryCode, countryName, countryCheck= validateDocumentCountry(getCountry.split(' '), userCountry)
#   documentTypeDetected, _ = validateDocumentType(documentType, documentSide, getCountry.split(' '), ocrData)

#   if(not documentVerify):
#       messages.append('El tipo de documento no coincide con el seleccionado.')

#   if(not typeCoincidence):
#       messages.append('El tipo de documento no coincide con el seleccionado.')

#   if(countryCheck != 'OK'):
#       messages.append('El país del documento no coincide.')

#   checkSide = {
#       'validation': 'OK'if documentVerify else '!OK',
#       'face': 'OK' if confidence <= confidenceValue else '!OK',
#       'documentValidation': 'OK' if typeCoincidence else '!OK',
#       'countryValidation': countryCheck,
#       'percentName': 'OK' if detectedName else '!OK',
#       'percentLastname': 'OK' if detectedSurName else '!OK',
#       'percentID': 'OK' if detectedID else '!OK'
#     }

#   if(not detectedName):
#     messages.append('El nombre no se ha encontrado en el documento.')

#   if(not detectedSurName):
#     messages.append('El apellido no se ha encontrado en el documento.')

#   if(not detectedID):
#     messages.append('El número del identificación no se ha encontrado en el documento.')


#   isExpired = None

#   hasExpiry, namedMonth,  position, keyword, dateFormat = hasExpiryDate(documentType=documentType, documentSide=documentSide, country=userCountry)
#   if(hasExpiry):
#       isExpired = expiryDateDetection(getExpiryDate,namedMonth,dateFormat)

#       checkSide['expiracy'] = 'OK' if (not isExpired) else '!OK'

#       if(isExpired):
#         messages.append('El documento esta expirado.')

#   image = imageToDataURL(orientedDocument)

#   resultsDict = {
#       'image': image,
#       'ocr': {
#         'data':{
#           'name': getName,
#           'lastName': getSurname,
#           'ID': getID
#         },
#         'percentage': {
#           'name': 100 if detectedName and len(getName) >= 1 else 0,
#           'lastName': 100 if detectedSurName and len(getSurname) >= 1 else 0,
#           'ID': 100 if detectedID and len(getID) >= 1 else 0
#         }
#       },
#       'face': True if confidence <= confidenceValue else False,
#       'confidence': confidence,
#       'document':{
#         'code': countryCode,
#         'country': countryName,
#         'countryCheck':countryCheck,
#         'type':documentTypeDetected,
#         'typeCheck':documentVerify,
#         'isExpired': isExpired
#       }
#     }
  
#   hasbarcode,barcodeType,barcodetbr  = barcodeSide(documentType=documentType, documentSide=documentSide, barcodeData=barcodeData)
#   if(hasbarcode):
#       detectedBarcodes = barcodeReader(orientedDocument, efirmaId, documentSide, barcodeType, barcodetbr)
#       detectedBarcodes = 'OK' if(len(detectedBarcodes) >= 1) else '!OK'
#       resultsDict['barcode'] = detectedBarcodes
#       checkSide['barcode'] = detectedBarcodes
#       if(detectedBarcodes != 'OK'):
#         messages.append('No se pudo detectar el código de barras del documento.')
#   else:
#       resultsDict['barcode'] = 'documento sin codigo de barras'

  
#   mrzCode, _ =  document_detection.getMrz(data=data)
#   mrzLetter, documentMRZ = MRZSide(documentType=documentType, documentSide=documentSide, mrzData=mrzData)
#   if(documentMRZ):
     
#     mrz, codeDetected =  extractMRZ(documentImageData)

#     if(codeDetected == 'Requiere verificar – DATOS INCOMPLETOS'):
#         messages.append('No se pudo detecar el código mrz del documento.')

#     nameMRZ = comparisonMRZInfo([mrz['name']], getName)
#     lastNameMRZ = comparisonMRZInfo([mrz['surname']], getSurname)

#     resultsDict['mrz'] = {
#         'code': mrz['code'] if(codeDetected) else 'Requiere verificar – DATOS INCOMPLETOS',
#         'data': {
#           'name': nameMRZ['data'] if(len(nameMRZ['data']) >= 1) else '',
#           'lastName': lastNameMRZ['data'] if(len(lastNameMRZ['data']) >= 1) else ''
#         },
#         'percentages': {
#           'name': nameMRZ['percent'],
#           'lastName': lastNameMRZ['percent']
#         }
#       }

#     checkSide['mrzNamePercent'] = 'OK' if nameMRZ['percent'] >= 50 else '!OK'
#     checkSide['mrzLastNamePercent'] = 'OK' if lastNameMRZ['percent'] >= 50 else '!OK'

#     if(nameMRZ['percent']<= 50):
#       messages.append('No se encontró el nombre en el codigo mrz.')
#     if(lastNameMRZ['percent']<= 50):
#       messages.append('No se encontró el apellido en el codigo mrz.')

#   else:
#       resultsDict['mrz'] = {
#         'code': '',
#         'data': {
#           'name': '',
#           'lastName': ''
#         },
#         'percentages': {
#           'name': 0,
#           'lastName': 0
#         }
#       }

#   validSide, _, _ = results(51, 'AUTOMATICA', checkSide)

#   resultsDict['messages'] = messages

#   if(confidence <= 0.60 and validSide):
#       resultsDict['validSide'] = 'OK' if(validSide and len(messages) <= 0) else '!OK'

#       return jsonify(resultsDict)

#   resultsDict['validSide'] = '!OK'
#   return jsonify(resultsDict)


# @document_bp.route('/back', methods=['POST'])
# def back():

#   messages = []

#   reqBody = request.get_json()

#   efirmaId = reqBody['id']
#   documentImage = reqBody['imagen']
#   documentSide = reqBody['ladoDocumento']
#   documentType = reqBody['tipoDocumento']
#   userCountry = reqBody['country']
#   name = reqBody['nombre']
#   surname = reqBody['apellido']
#   numeroDocumento = reqBody['documento']
#   documentImageData = readDataURL(documentImage)

#   # efirmaId = request.form.get('id')
#   # documentImage = request.files.get('document')
#   # documentSide = request.form.get('documentSide')
#   # documentType = request.form.get('documentType')
#   # userCountry = request.form.get('country')
#   # name = request.form.get('nombre')
#   # surname = request.form.get('apellido')

#   # documentImageData = fileCv2(documentImage)

#   countryData = controlador_db.selectData(f'''
#       SELECT * FROM pki_validacion.pais as pais 
#     WHERE pais.codigo = "{userCountry}"''', ())

#   mrzData = json.loads(countryData[3])
#   barcodeData = json.loads(countryData[4])
#   ocrData = json.loads(countryData[5])

#   resultsDict = {

#   }

#   checkSide = {

#   }

#   hasbarcode,barcodeType,barcodetbr  = barcodeSide(documentType=documentType, documentSide=documentSide, barcodeData=barcodeData)
#   if(hasbarcode):
#     barcodes = barcodeReader(documentImageData, efirmaId, documentSide, barcodeType, barcodetbr)
#     detectedBarcodes = 'OK' if(len(barcodes) >= 1) else '!OK'
#     rotatedImage = rotateBarcode(documentImageData, barcodes=barcodes)

#     documentImageData = rotatedImage
#     resultsDict['barcode'] = detectedBarcodes
#     resultsDict['image'] = imageToDataURL(rotatedImage)
#     checkSide['barcode'] = detectedBarcodes
#     if(detectedBarcodes != 'OK'):
#       messages.append('No se pudo detectar el código de barras del documento.')
#   else:
#       resultsDict['barcode'] = 'documento sin codigo de barras'

#   classes, side, ocr, val = document_detection.getClasses(userCountry, documentSide, documentType)
#   labels, data = document_detection.detection(documentImageData, classes=classes, classesOcr=ocr)

#   documentVerify, typeCoincidence = document_detection.verifyDocument(classes=val, labels=labels, side=side)

#   mrzCode, mrzDetected =  document_detection.getMrz(data=data)

#   mrzLetter, documentMRZ = MRZSide(documentType=documentType, documentSide=documentSide, mrzData=mrzData)
#   if(documentMRZ):
#     countryCode, countryName, countryCheck= validateDocumentCountry(mrzCode.split(' '), userCountry)
#     documentTypeDetected, _ = validateDocumentType(documentType, documentSide, mrzCode.split(' '), ocrData)

#     if(not documentVerify):
#       messages.append('El tipo de documento no coincide con el seleccionado.')

#     if(not typeCoincidence):
#       messages.append('El tipo de documento no coincide con el seleccionado.')

#     if(countryCheck != 'OK'):
#       messages.append('El país del documento no coincide.')

#     checkSide['documentValidation'] = 'OK' if typeCoincidence else '!OK'
#     checkSide['countryValidation'] = countryCheck
#     checkSide['validation'] = 'OK'if documentVerify else '!OK'

#     resultsDict['document'] = {
#       'code': countryCode,
#       'country': countryName,
#       'countryCheck':countryCheck,
#       'type':documentTypeDetected,
#       'typeCheck':documentVerify
#     }

#     mrz, codeDetected =  extractMRZ(documentImageData)

#     if(codeDetected == 'Requiere verificar – DATOS INCOMPLETOS'):
#         messages.append('No se pudo detecar el código mrz del documento.')

#     nameMRZ = comparisonMRZInfo([mrz['name']], name)
#     lastNameMRZ = comparisonMRZInfo([mrz['surname']], surname)

#     resultsDict['mrz'] = {
#         'code': mrz['code'] if(codeDetected) else 'Requiere verificar – DATOS INCOMPLETOS',
#         'data': {
#           'name': nameMRZ['data'] if(len(nameMRZ['data']) >= 1) else '',
#           'lastName': lastNameMRZ['data'] if(len(lastNameMRZ['data']) >= 1) else ''
#         },
#         'percentages': {
#           'name': nameMRZ['percent'],
#           'lastName': lastNameMRZ['percent']
#         }
#       }

#     checkSide['mrzNamePercent'] = 'OK' if nameMRZ['percent'] >= 50 else '!OK'
#     checkSide['mrzLastNamePercent'] = 'OK' if lastNameMRZ['percent'] >= 50 else '!OK'

#     if(nameMRZ['percent']<= 50):
#       messages.append('No se encontró el nombre en el codigo mrz.')
#     if(lastNameMRZ['percent']<= 50):
#       messages.append('No se encontró el apellido en el codigo mrz.')


#   else:
#       resultsDict['mrz'] = {
#         'code': '',
#         'data': {
#           'name': '',
#           'lastName': ''
#         },
#         'percentages': {
#           'name': 0,
#           'lastName': 0
#         }
#       }
#   validSide, _, _ = results(51, 'AUTOMATICA', checkSide)

#   resultsDict['messages'] = messages

#   resultsDict['validSide'] = 'OK' if(validSide and len(messages) <= 0) else '!OK'

#   return jsonify(resultsDict)

# @document_bp.route('/test', methods=['GET', 'POST'])
# def test():
#     if request.method == 'POST':
#         img_file = request.files.get('image')
#         if not img_file:
#             return render_template('test.html', error='No se subió ninguna imagen')

#         # Procesar imagen
#         img = fileCv2(img_file)
#         yolo_model = YOLO('../models/colombia-v0.1.pt')
#         results = yolo_model(img)[0]

#         # Dibujar bounding boxes
#         img_with_boxes = img.copy()
#         class_names = yolo_model.names
#         for box, cls_id in zip(results.boxes.xyxy.cpu().numpy(), results.boxes.cls.cpu().numpy()):
#           x1, y1, x2, y2 = map(int, box[:4])
#           class_name = class_names[int(cls_id)]

#           cv2.rectangle(img_with_boxes, (x1, y1), (x2, y2), (0, 255, 0), 3)
#           cv2.putText(img_with_boxes,
#                       class_name,
#                       (x1, y1 - 10),
#                       cv2.FONT_HERSHEY_SIMPLEX,
#                       1,
#                       (0, 0, 0), 1)

#         # Convertir a base64 para mostrar en HTML
#         _, buffer = cv2.imencode('.jpg', img_with_boxes)
#         img_b64 = base64.b64encode(buffer).decode('utf-8')
#         img_data_url = f"data:image/jpeg;base64,{img_b64}"

#         return render_template('test.html',
#                                image=img_data_url,
#                                boxes=results.boxes.xyxy.cpu().numpy().tolist())

#     # GET method
#     return render_template('test.html')