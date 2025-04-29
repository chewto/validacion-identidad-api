import json
from flask import Blueprint, request, jsonify
from check_result import results
import controlador_db
from expiry import expiryDateDetection, expiryDateOCR, hasExpiryDate
from lector_codigo import barcodeReader, barcodeSide
from mrz import MRZSide, comparisonMRZInfo, extractMRZ, mrzInfo
from ocr import validateDocumentCountry, validateDocumentType
from reconocimiento import orientacionImagen, verifyFaces
from utilidades import fileCv2, imageToDataURL, readDataURL
import document_detection

document_bp = Blueprint('document', __name__, url_prefix="/document")

confidenceValue = 0.6

@document_bp.route('/front', methods=['POST'])
def front():

  # efirmaId = request.form.get('id')
  # selfieImage = request.files.get('selfie')
  # documentImage = request.files.get('document')
  # documentSide = request.form.get('documentSide')
  # documentType = request.form.get('documentType')
  # userCountry = request.form.get('country')

  reqBody = request.get_json()

  efirmaId = reqBody['id']
  selfieImage = reqBody['imagenPersona']
  documentImage = reqBody['imagen']
  documentSide = reqBody['ladoDocumento']
  documentType = reqBody['tipoDocumento']
  userCountry = reqBody['country']
  selfieData = readDataURL(selfieImage)
  documentImageData = readDataURL(documentImage)

  countryData = controlador_db.selectData(f'''
      SELECT * FROM pki_validacion.pais as pais 
      WHERE pais.codigo = "{userCountry}"''', ())
  
  print(countryData)

  mrzData = json.loads(countryData[3])
  barcodeData = json.loads(countryData[4])
  ocrData = json.loads(countryData[5])

  messages = []

  #Face comparison
  # selfieData = fileCv2(selfieImage)
  # documentImageData = fileCv2(documentImage)

  orientedSelfie, _ = orientacionImagen(selfieData)

  orientedDocument, _ = orientacionImagen(documentImageData)

  _, confidence, _ = verifyFaces(orientedSelfie, orientedDocument)

  if(confidence >= confidenceValue):
      messages.append('Los rostros no coincidén.')

  #YOLO usage
  classes, side, ocr, val = document_detection.getClasses(userCountry, documentSide, documentType)
  labels, data = document_detection.detection(documentImageData, classes=classes, classesOcr=ocr)


  documentVerify, typeCoincidence = document_detection.verifyDocument(classes=val, labels=labels, side=side)

  getName, detectedName = document_detection.getForename(data)
  getSurname, detectedSurName = document_detection.getSurname(data)
  getID, detectedID = document_detection.getID(data)
  getExpiryDate = document_detection.getExpiry(data)
  getCountry = document_detection.getCountry(data)

  countryCode, countryName, countryCheck= validateDocumentCountry(getCountry.split(' '), userCountry)
  documentTypeDetected, _ = validateDocumentType(documentType, documentSide, getCountry.split(' '), ocrData)

  if(not documentVerify):
      messages.append('El tipo de documento no coincide con el seleccionado.')

  if(not typeCoincidence):
      messages.append('El tipo de documento no coincide con el seleccionado.')

  if(countryCheck != 'OK'):
      messages.append('El país del documento no coincide.')

  checkSide = {
      'validation': 'OK'if documentVerify else '!OK',
      'face': 'OK' if confidence <= confidenceValue else '!OK',
      'documentValidation': 'OK' if typeCoincidence else '!OK',
      'countryValidation': countryCheck,
      'percentName': 'OK' if detectedName else '!OK',
      'percentLastname': 'OK' if detectedSurName else '!OK',
      'percentID': 'OK' if detectedID else '!OK'
    }

  if(not detectedName):
    messages.append('El nombre no se ha encontrado en el documento.')

  if(not detectedSurName):
    messages.append('El apellido no se ha encontrado en el documento.')

  if(not detectedID):
    messages.append('El número del identificación no se ha encontrado en el documento.')


  isExpired = None

  hasExpiry, namedMonth,  position, keyword, dateFormat = hasExpiryDate(documentType=documentType, documentSide=documentSide, country=userCountry)
  if(hasExpiry):
      isExpired = expiryDateDetection(getExpiryDate,namedMonth,dateFormat)

      checkSide['expiracy'] = 'OK' if (not isExpired) else '!OK'

      if(isExpired):
        messages.append('El documento esta expirado.')

  image = imageToDataURL(orientedDocument)

  resultsDict = {
      'image': image,
      'ocr': {
        'data':{
          'name': getName,
          'lastName': getSurname,
          'ID': getID
        },
        'percentage': {
          'name': 100 if detectedName and len(getName) >= 1 else 0,
          'lastName': 100 if detectedSurName and len(getSurname) >= 1 else 0,
          'ID': 100 if detectedID and len(getID) >= 1 else 0
        }
      },
      'face': True if confidence <= confidenceValue else False,
      'confidence': confidence,
      'document':{
        'code': countryCode,
        'country': countryName,
        'countryCheck':countryCheck,
        'type':documentTypeDetected,
        'typeCheck':documentVerify,
        'isExpired': isExpired
      }
    }
  
  hasbarcode,barcodeType,barcodetbr  = barcodeSide(documentType=documentType, documentSide=documentSide, barcodeData=barcodeData)
  if(hasbarcode):
      detectedBarcodes = barcodeReader(orientedDocument, efirmaId, documentSide, barcodeType, barcodetbr)
      detectedBarcodes = 'OK' if(len(detectedBarcodes) >= 1) else '!OK'
      resultsDict['barcode'] = detectedBarcodes
      checkSide['barcode'] = detectedBarcodes
      if(detectedBarcodes != 'OK'):
        messages.append('No se pudo detectar el código de barras del documento.')
  else:
      resultsDict['barcode'] = 'documento sin codigo de barras'

  
  mrzLetter, documentMRZ = MRZSide(documentType=documentType, documentSide=documentSide, mrzData=mrzData)
  if(documentMRZ):
      # mrz = extractMRZ(ocr=documentoOCRSencillo, mrzStartingLetter=mrzLetter)
      mrzCode =  document_detection.getMrz(data=data)

      if(mrzCode == 'Requiere verificar – DATOS INCOMPLETOS'):
        messages.append('No se pudo detecar el código mrz del documento.')


      extractNamePre = mrzInfo(mrz=mrzCode, searchTerm=getName)
      extractLastnamePre = mrzInfo(mrz=mrzCode, searchTerm=getSurname)

      nameMRZ = comparisonMRZInfo([ extractNamePre], getName)
      lastNameMRZ = comparisonMRZInfo([ extractLastnamePre], getSurname)

    

      resultsDict['mrz'] = {
        'code':  mrzCode,
        'data': {
          'name': nameMRZ['data'] if(len(nameMRZ['data']) >= 1) else '',
          'lastName': lastNameMRZ['data'] if(len(lastNameMRZ['data']) >= 1) else ''
        },
        'percentages': {
          'name': nameMRZ['percent'],
          'lastName': lastNameMRZ['percent']
        }
      }

      checkSide['mrzNamePercent'] = 'OK' if nameMRZ['percent'] >= 50 else '!OK'
      checkSide['mrzLastNamePercent'] = 'OK' if lastNameMRZ['percent'] >= 50 else '!OK'

      if(nameMRZ['percent']<= 50):
        messages.append('No se encontró el nombre en el codigo mrz.')
      if(lastNameMRZ['percent']<= 50):
        messages.append('No se encontró el apellido en el codigo mrz.')


  else:
      resultsDict['mrz'] = {
        'code': '',
        'data': {
          'name': '',
          'lastName': ''
        },
        'percentages': {
          'name': 0,
          'lastName': 0
        }
      }

  validSide, _, _ = results(51, 'AUTOMATICA', checkSide)

  resultsDict['messages'] = messages

  if(confidence <= 0.60 and validSide):
      resultsDict['validSide'] = 'OK' if(validSide and len(messages) <= 0) else '!OK'

      return jsonify(resultsDict)

  resultsDict['validSide'] = '!OK'
  return jsonify(resultsDict)
