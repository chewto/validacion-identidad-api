import json
from flask import Blueprint, request, jsonify
from ultralytics import YOLO
from check_result import results, testingCountry
import controlador_db
from expiry import expiryDateDetection, expiryDateOCR, hasExpiryDate
from formatter import _formatDocumentNumber
from lector_codigo import barcodeReader, barcodeSide, rotateBarcode
from mrz import MRZSide, comparisonMRZInfo, extractMRZ, mrzInfo
from ocr import validacionOCR, validateDocumentCountry, validateDocumentType
from reconocimiento import orientacionImagen, verifyFaces
from request_parser import _parse_request
from utilidades import fileCv2, readDataURL, textNormalize
import document_detection
import numpy as np

document_detection_bp = Blueprint('document', __name__, url_prefix="/document")

confidenceValue = 0.6

@document_detection_bp.route('/detection', methods=['POST', 'GET'])
def documentDetection():

  if(request.method == 'GET'):
    return 'vayase pal diablo'

  testing = request.args.get("testing", "false").lower() == "true"

  if testing:
    image = request.files.get("image", None)
    labels = request.form.get('labels', None)
    labels = labels.split(",")
    country = request.form.get('country')
    imageData = fileCv2(image)
  else:
    data = request.get_json()
    labels = data["labels"]
    labels = labels.split(",")
    country = data['country']
    imageData = readDataURL(data["image"])

  results =  document_detection.detection(imageData, labels, country)

  return results

@document_detection_bp.route('/validate', methods=['POST', 'GET'])
def validate():

  parsed = _parse_request(request)

  selfie = parsed['persona_data']
  documentImage = parsed['documento_data']
  efirmaId = parsed['efirma_id']
  name = parsed['nombre']
  surname = parsed['apellido']
  documentType = parsed['tipo_documento']
  country = parsed["user_country"]
  tries = parsed["tries"]
  ocr = parsed["ocr"]

  confidenceThreshold = 0.7 if tries >= 1 else 0.6
  


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
      WHERE pais.codigo = "COL"''', ())
  
  

  barcodeData = json.loads(countryData[0])
  mrzData = json.loads(countryData[1])
  yoloLabels = countryData[2]
  yoloLabels = yoloLabels.split(',')

  if(documentSide == 'anverso'):
    print('es un anverso')
    _, confidence, _ = verifyFaces(selfie, documentImage)
    resultsDict['face'] = True if confidence <= confidenceThreshold else False
    resultsDict['confidence'] = confidence

    numeroDocumento = _formatDocumentNumber(numeroDocumento)

    nombre = textNormalize(nombre)
    apellido = textNormalize(apellido)

    # nombreOcr, pctNombre = validacionOCR(ocr, nombre, onlyNumbers=False)
    # apellidoOcr, pctApellido = validacionOCR(ocr, apellido, onlyNumbers=False)
    # numeroOcr, pctNumero = validacionOCR(ocr, numeroDocumento, onlyNumbers=True)

    # checkSide['percentName'] = 'OK' if pctNombre >= 50 else '!OK'
    # checkSide['percentLastname'] = 'OK' if pctApellido >= 50 else '!OK'
    # checkSide['percentID'] = 'OK' if pctNumero >= 50 else '!OK'

  countryHasModel = document_detection.checkModel(country=country)

  print(countryHasModel)

  if(countryHasModel):
    documentType, documentValidation, countryCode, countryDetected, isCountry, croppedImage = document_detection.detectDocument(
        img=documentImage, countryCode=country, side=documentSide, type=documentType, yoloLabels=yoloLabels
      )

    checkSide['documentValidation'] = documentValidation

    resultsDict['document'] = {
        'type': documentType,
        'typeCheck': documentValidation,
        'isExpired': None,
        "code": countryCode,
        "country": countryDetected,
        "countryCheck": isCountry,
    }
    
    resultsDict['image'] = croppedImage


  hasbarcode,barcodeType,barcodetbr  = barcodeSide(documentType=documentType, documentSide=documentSide, barcodeData=barcodeData)
  barcodeIsOptional = None

  for key, value in barcodeData.items():
    barcodeIsOptional = value['optional']

  if(hasbarcode):
      print(barcodeIsOptional)
      detectedBarcodes = barcodeReader(documentImage, efirmaId, documentSide, barcodeType, barcodetbr)
      detectedBarcodes = 'OK' if(len(detectedBarcodes) >= 1) else '!OK'
      # checkSide['barcode'] = detectedBarcodes
      if(not barcodeIsOptional or detectedBarcodes == 'OK'):
        resultsDict['barcode'] = detectedBarcodes
      if(detectedBarcodes != 'OK' and not barcodeIsOptional):
        messages.append('No se pudo detectar el código de barras del documento.')
  # else:
  #     # resultsDict['barcode'] = None
  #     print("no tiene codigo")


  mrzLetter, documentMRZ = MRZSide(documentType=documentType, documentSide=documentSide, mrzData=mrzData)

  mrzIsOptional = None
  for key, value in mrzData.items():
    mrzIsOptional = value['optional']

  if(documentMRZ):

    nameHasK = name.find("k")
    lastNamehasK = surname.find("k")

    mrz =  extractMRZ(documentImage)

    if(mrz == "No se pudo detectar MRZ válido en la imagen." and not mrzIsOptional):
      messages.append('No se pudo detecar el código mrz del documento.')

    if('valid_score' in mrz):
        if mrz['valid_score'] >= 51:
            extractName = mrzInfo(mrz=mrz['raw_text'].replace("\n", "") if 'raw_text' in mrz else '', searchTerm=name)
            extractLastname = mrzInfo(mrz=mrz['raw_text'].replace("\n", "") if 'raw_text' in mrz else '', searchTerm=surname)

            nameMRZ = comparisonMRZInfo([extractName], name, 'name')
            lastNameMRZ = comparisonMRZInfo([extractLastname], surname, 'surname')

            #APLICA PARA AMBOS CODIGO DE BARAS Y MRZ ASI ELIMINAMOS CODIGO ESPAGUETTI
            #PARA ASIGNAR VERIFICA QUE SEA OPTIONAL Y QUE SEA VALIDO, EN TAL CASO SE ASIGNA
            #SI NO SE DETECTO NO SE VA A AGREGAR
            #SI SE DETECTO SE AGREGA 
            #PARA LOS NO OPCIONAL SE AGREGA EN CUALQUIER CASO


            #not optional 

            print(mrzIsOptional)
            # Asigna siempre que MRZ no es opcional, o si es opcional pero existe 'raw_text' en mrz
            if (not mrzIsOptional) or (mrzIsOptional and 'raw_text' in mrz):
              resultsDict['mrz'] = {
                'code': mrz['raw_text'] if 'raw_text' in mrz else 'No se pudo detectar MRZ válido en la imagen.',
                'data': {
                  'name': nameMRZ['data'] if(len(nameMRZ['data']) >= 1) else '',
                  'lastName': lastNameMRZ['data'] if(len(lastNameMRZ['data']) >= 1) else ''
                },
                'percentages': {
                  'name': nameMRZ['percent'],
                  'lastName': lastNameMRZ['percent']
                }
              }


            if(nameMRZ['percent']<= 50 and not mrzIsOptional and 'raw_text' in mrz):
              messages.append('No se encontró el nombre en el codigo mrz.')
            if(lastNameMRZ['percent']<= 50 and not mrzIsOptional and'raw_text' in mrz):
              messages.append('No se encontró el apellido en el codigo mrz.')
  # else:
  #   print()

  resultsDict['messages'] = messages

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