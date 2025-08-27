import json
from flask import Blueprint, request, jsonify
from ultralytics import YOLO
from check_result import results, testingCountry
import controlador_db
from expiry import expiryDateDetection, expiryDateOCR, hasExpiryDate
from lector_codigo import barcodeReader, barcodeSide, rotateBarcode
from mrz import MRZSide, comparisonMRZInfo, extractMRZ, mrzInfo
from ocr import validateDocumentCountry, validateDocumentType
from reconocimiento import orientacionImagen, verifyFaces
from request_parser import _parse_request
from utilidades import fileCv2, imageToDataURL, readDataURL
import document_detection
from flask import render_template
import cv2
import numpy as np
import base64

document_detection_bp = Blueprint('document', __name__, url_prefix="/document")

confidenceValue = 0.6

@document_detection_bp.route('/detection', methods=['POST', 'GET'])
def documentDetection():

  if(request.method == 'GET'):
    return 'vayase pal diablo'

  image = request.files.get("image", None)

  imageData = fileCv2(image)

  results =  document_detection.detection(imageData, [
  "CEDULA_CIUDADANIA_FRONTAL",
  "NUMERO_DOCUMENTO",
  "APELLIDOS",
  "NOMBRES",
  "FIRMA",
  "FOTO",
  "ENCABEZADO",
  "CEDULA_CIUDADANIA_REVERSO",
  "CODIGO_BARRAS",
  "HUELLA",
  "FECHA_NACIMIENTO",
  "LUGAR_NACIMIENTO",
  "ESTATURA",
  "GRUPO_SANGUINEO",
  "SEXO",
  "FECHA_EXPEDICION",
  "CODIGO",
  "CEDULA_EXTRANJERIA_FRONTAL",
  "NACIONALIDAD",
  "FECHA_EXPIRACION",
  "GHOST",
  "CEDULA_EXTRANJERIA_REVERSO",
  "MRZ",
  "CEDULA_DIGITAL_FRONTAL",
  "CEDULA_DIGITAL_REVERSO",
  "PASAPORTE",
  "NUMERO_PERSONAL",
  "AUTORIDAD",
  "CODIGO_PAIS",
  "TIPO",
  "CODIG_BARRAS_LATERAL",
  "NUMERO_LATERAL",
  "NUMERO_PASAPORTE"
])

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


  documentSide = request.args.get("side", None)

  countryData = controlador_db.selectData(f'''
      SELECT * FROM pki_validacion.pais as pais 
      WHERE pais.codigo = "COL"''', ())
  

  mrzData = json.loads(countryData[3])
  barcodeData = json.loads(countryData[4])
  # ocrData = json.loads(countryData[5])

  for key, value in barcodeData.items():
    print("barcode")
    print(value['optional'], value['tbr'])

  for key, value in mrzData.items():
    print("mrz")
    print(value['optional'])


  if(documentSide == 'front'):
    print('es un anverso')
    _, confidence, _ = verifyFaces(selfie, documentImage)

    print(confidence)

  hasbarcode,barcodeType,barcodetbr  = barcodeSide(documentType=documentType, documentSide=documentSide, barcodeData=barcodeData)
  if(hasbarcode):
      print("tiene codigo")
      detectedBarcodes = barcodeReader(documentImage, efirmaId, documentSide, barcodeType, barcodetbr)
      detectedBarcodes = 'OK' if(len(detectedBarcodes) >= 1) else '!OK'
      # resultsDict['barcode'] = detectedBarcodes
      # checkSide['barcode'] = detectedBarcodes
      # if(detectedBarcodes != 'OK'):
      #   messages.append('No se pudo detectar el código de barras del documento.')
  else:
      # resultsDict['barcode'] = None
      print("no tiene codigo")


  mrzLetter, documentMRZ = MRZSide(documentType=documentType, documentSide=documentSide, mrzData=mrzData)
  if(documentMRZ):

    nameHasK = name.find("k")
    lastNamehasK = surname.find("k")

    mrz =  extractMRZ(documentImage)

    print(mrz)

      # if(nameHasK == -1 or lastNamehasK == -1):
      #   mrz = mrz['raw_text'].replace('K', ' ')

    if(mrz == "No se pudo detectar MRZ válido en la imagen."):
      print('')
        # messages.append('No se pudo detecar el código mrz del documento.')

    if('valid_score' in mrz):
        if mrz['valid_score'] >= 51:
            extractName = mrzInfo(mrz=mrz['raw_text'].replace("\n", "") if 'raw_text' in mrz else '', searchTerm=name)
            extractLastname = mrzInfo(mrz=mrz['raw_text'].replace("\n", "") if 'raw_text' in mrz else '', searchTerm=surname)

            nameMRZ = comparisonMRZInfo([extractName], name, 'name')
            lastNameMRZ = comparisonMRZInfo([extractLastname], surname, 'surname')

            # if(nameMRZ['percent']<= 50 and tipoDocumento != 'CEDULA DE CIUDADANIA'):
            #   messages.append('No se encontró el nombre en el codigo mrz.')
            # if(lastNameMRZ['percent']<= 50 and tipoDocumento != 'CEDULA DE CIUDADANIA'):
            #   messages.append('No se encontró el apellido en el codigo mrz.')

            if 'country' in mrz:
                countryCodePre, countryDetectedPre, documentCountryValidationPre = validateDocumentCountry([mrz['country']], country="COL")
                codeC, country, countryValidation = testingCountry([{'country': countryCodePre, 'countryDetected': countryDetectedPre, 'validation': documentCountryValidationPre}])

                if(countryValidation != 'OK'):
                    # messages.append('El país del documento no coincide.')
                    print()
            else:
                print()
        else:
            print()
            print()
    else:

        print()
  else:
    print()

  return ''



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