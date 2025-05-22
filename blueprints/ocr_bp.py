
import json
from flask import Blueprint, request, jsonify
from lector_codigo import barcodeReader, barcodeSide, rotateBarcode
from name_search import searchId, searchName
from ocr import comparacionOCR, ocr, validacionOCR, validarLadoDocumento, validateDocumentCountry, validateDocumentType, preprocessing
from mrz import MRZSide, extractMRZ, mrzInfo, comparisonMRZInfo
from expiry import expiryDateOCR, hasExpiryDate
from reconocimiento import orientacionImagen, verifyFaces
from utilidades import readDataURL, textNormalize, imageToDataURL, fileCv2
from check_result import testingCountry, testingType, results
import time
import controlador_db
import cv2

ocr_bp = Blueprint('ocr', __name__, url_prefix='/ocr')

messages = {
  "ocr":{
    "name":"",
    "lastName": "",
    "document": ""
  },
  "mrz":{
    "code":"",
    "name":"",
    "lastName": ""
  },
  "face":"",
  "document":{
    "country": "",
    "type": "",
    "expiracy": ""
  },
  "barcode": {
    "code": ""
  }
}

@ocr_bp.route('/anverso', methods=['POST'])
def verificarAnverso():

    confidenceValue = 0.6

    reqBody = request.get_json()

    efirmaId = reqBody['id']
    imagenPersona = reqBody['imagenPersona']
    imagenDocumento = reqBody['imagen']
    ladoDocumento = reqBody['ladoDocumento']
    tipoDocumento = reqBody['tipoDocumento']
    nombre = reqBody['nombre']
    apellido = reqBody['apellido']
    numeroDocumento = reqBody['documento']
    userCountry = reqBody['country']
    tries = reqBody['tries']
    personaData = readDataURL(imagenPersona)
    documentoData = readDataURL(imagenDocumento)

    # efirmaId = request.form.get('id')
    # imagenPersona = request.files.get('imagenPersona')
    # imagenDocumento = request.files.get('imagen')
    # ladoDocumento = request.form.get('ladoDocumento')
    # tipoDocumento = request.form.get('tipoDocumento')
    # nombre = request.form.get('nombre')
    # apellido = request.form.get('apellido')
    # numeroDocumento = request.form.get('documento')
    # userCountry = 

    # personaData = fileCv2(imagenPersona)
    # documentoData = fileCv2(imagenDocumento)

    resolution = 600 if tries <=1 else 1080

    countryData = controlador_db.selectData(f'''
      SELECT * FROM pki_validacion.pais as pais 
      WHERE pais.codigo = "{userCountry}"''', ())

    mrzData = json.loads(countryData[3])
    barcodeData = json.loads(countryData[4])
    ocrData = json.loads(countryData[5])

    selfieOrientada, carasImagenPersona = orientacionImagen(personaData)

    documentoOrientado, carasImagenDocumento = orientacionImagen(documentoData)

    preprocessedDocument = preprocessing(documentoOrientado, resolution, filters='sharp')

    _, confidence, _ = verifyFaces(selfieOrientada, documentoOrientado)

    timeOcrInit = time.time()
    ocrResult, documentoOCRPre = ocr(preprocessedDocument)
    timeOcrEnd = time.time()
    print(f"{timeOcrInit - timeOcrEnd} tiempo ocr")

    validarLadoPre = validarLadoDocumento(tipoDocumento, ladoDocumento, documentoOCRPre, ocrData)
    totalValidacionLado = validarLadoPre 
    checkSide = {
      'validation': 'OK'if totalValidacionLado >= 3 else '!OK',
      'face': 'OK' if confidence <= confidenceValue else '!OK'
    }

    messages = []

    if(confidence >= confidenceValue):
      messages.append('Los rostros no coincidén.')

    typeDetectedPre, documentTypeValidationPre = validateDocumentType(tipoDocumento, ladoDocumento, documentoOCRPre, detectionData=ocrData)


    countryCodePre, countryDetectedPre, documentCountryValidationPre = validateDocumentCountry( documentoOCRPre, country=userCountry)

    documentType, documentValidation = testingType([{'type':typeDetectedPre, 'validation':documentTypeValidationPre}])
    codeC, country, countryValidation = testingCountry([{'country': countryCodePre, 'countryDetected': countryDetectedPre, 'validation': documentCountryValidationPre}])

    isExpired = None

    # hasExpiry, namedMonth, datePosition, keywords, dateFormat = hasExpiryDate(tipoDocumento, ladoDocumento, country=userCountry)
    # if(hasExpiry):
    #   isExpired = expiryDateOCR(ocrResult,datePosition,keywords,namedMonth,dateFormat)

    #   checkSide['expiracy'] = 'OK' if (not isExpired) else '!OK'

    #   if(isExpired):
    #     messages.append('El documento esta expirado.')

    if(documentValidation != 'OK'):
      messages.append('El tipo de documento no coincide con el seleccionado.')
    
    if(countryValidation != 'OK'):
      messages.append('El país del documento no coincide.')

    if(codeC == 'HND' or country == 'HONDURAS' and tipoDocumento != 'Pasaporte' and numeroDocumento is not None):
      idLength = len(numeroDocumento)
      firstNums = numeroDocumento[0:4]
      middleNums = numeroDocumento[4:8]
      lastNums = numeroDocumento[8:idLength]

      numeroDocumento = f"{firstNums} {middleNums} {lastNums}"

    nombre = textNormalize(nombre)
    apellido = textNormalize(apellido)


    nombrePreOCR, porcentajeNombrePre = validacionOCR(documentoOCRPre, nombre)
    apellidoPreOCR, porcentajeApellidoPre = validacionOCR(documentoOCRPre, apellido)
    numeroDocumentoPreOCR, porcentajeDocumentoPre = validacionOCR(documentoOCRPre, numeroDocumento)


    checkSide['documentValidation'] = documentValidation
    checkSide['countryValidation'] = countryValidation
    checkSide['percentName'] = 'OK' if porcentajeNombrePre >= 50 else '!OK'
    checkSide['percentLastname'] = 'OK' if porcentajeApellidoPre >= 50 else '!OK'
    checkSide['percentID'] ='OK' if porcentajeDocumentoPre >= 50 else '!OK'

    if(porcentajeNombrePre <= 50):
      messages.append('El nombre no se ha encontrado en el documento.')

    if(porcentajeApellidoPre <= 50):
      messages.append('El apellido no se ha encontrado en el documento.')

    if(porcentajeDocumentoPre <= 50):
      messages.append('El número del identificación no se ha encontrado en el documento.')

    image = imageToDataURL(documentoOrientado)

    resultsDict = {
      'image': image,
      'ocr': {
        'data':{
          'name': nombrePreOCR,
          'lastName': apellidoPreOCR,
          'ID': numeroDocumentoPreOCR
        },
        'percentage': {
          'name': porcentajeNombrePre,
          'lastName': porcentajeApellidoPre,
          'ID': porcentajeDocumentoPre
        }
      },
      'face': True if confidence <= confidenceValue else False,
      'confidence': confidence,
      'document':{
        'code': codeC,
        'country': country,
        'countryCheck':countryValidation,
        'type':documentType,
        'typeCheck':documentValidation,
        'isExpired': isExpired
      }
    }

    codeTimeInit = time.time()

    hasbarcode,barcodeType,barcodetbr  = barcodeSide(documentType=tipoDocumento, documentSide=ladoDocumento, barcodeData=barcodeData)
    if(hasbarcode):
      detectedBarcodes = barcodeReader(preprocessedDocument, efirmaId, ladoDocumento, barcodeType, barcodetbr)
      detectedBarcodes = 'OK' if(len(detectedBarcodes) >= 1) else '!OK'
      resultsDict['barcode'] = detectedBarcodes
      checkSide['barcode'] = detectedBarcodes
      if(detectedBarcodes != 'OK'):
        messages.append('No se pudo detectar el código de barras del documento.')
      # if(detectedBarcodes != 'OK'):
        # messages.append('No se pudo detectar el código de barras del documento.')
    else:
      resultsDict['barcode'] = 'documento sin codigo de barras'

    mrzLetter, documentMRZ = MRZSide(documentType=tipoDocumento, documentSide=ladoDocumento, mrzData=mrzData)
    if(documentMRZ):
      mrz =  extractMRZ(ocr=documentoOCRPre, mrzStartingLetter=mrzLetter)

      if(mrz == 'Requiere verificar – DATOS INCOMPLETOS'):
        messages.append('No se pudo detecar el código mrz del documento.')

      extractName = mrzInfo(mrz=mrz, searchTerm=nombre)
      extractLastname = mrzInfo(mrz=mrz, searchTerm=apellido)

      nameMRZ = comparisonMRZInfo([extractName], nombre)
      lastNameMRZ = comparisonMRZInfo([extractLastname], apellido)

      # resultsDict['document']['isExpired'] = False

      resultsDict['mrz'] = {
        'code': mrz,
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

    codeTimeEnd = time.time()
    codeTime = codeTimeInit - codeTimeEnd
    print('codes time ', codeTime)

    resultsDict['messages'] = messages

    if(confidence <= 0.60 and validSide):
      resultsDict['validSide'] = 'OK' if(validSide and len(messages) <= 0) else '!OK'
      # resultsDict['validSide'] = 'OK' 

      return jsonify(resultsDict)

    resultsDict['validSide'] = '!OK'
    # resultsDict['validSide'] = 'OK' 
    return jsonify(resultsDict)



#rutas para el front
@ocr_bp.route('/reverso', methods=['POST'])
def verificarReverso():
    
    messages = []

    reqBody = request.get_json()

    efirmaId = reqBody['id']
    imagenDocumento = reqBody['imagen']
    ladoDocumento = reqBody['ladoDocumento']
    tipoDocumento = reqBody['tipoDocumento']
    nombre = reqBody['nombre']
    apellido = reqBody['apellido']
    numeroDocumento = reqBody['documento']
    imagenDocumento = readDataURL(imagenDocumento)
    userCountry = reqBody['country']
    tries = reqBody['tries']

    # print(nombre, apellido)

    # efirmaId = request.form.get('id')
    # imagenPersona = request.files.get('imagenPersona')
    # imagenDocumento = request.files.get('imagen')
    # ladoDocumento = request.form.get('ladoDocumento')
    # tipoDocumento = request.form.get('tipoDocumento')
    # nombre = request.form.get('nombre')
    # apellido = request.form.get('apellido')
    # numeroDocumento = request.form.get('documento')
    # userCountry = request.form.get('country')

    # imagenDocumento = fileCv2(imagenDocumento)

    resolution = 600 if tries <=1 else 1080

    print(tries)

    print(resolution)

    preprocessedDocument = preprocessing(imagenDocumento, resolution, filters='sharp')

    nombre = textNormalize(nombre)
    apellido = textNormalize(apellido)

    countryData = controlador_db.selectData(f'''
      SELECT * FROM pki_validacion.pais as pais 
    WHERE pais.codigo = "{userCountry}"''', ())

    mrzData = json.loads(countryData[3])
    barcodeData = json.loads(countryData[4])
    ocrData = json.loads(countryData[5])

    documentoData = None

    resultsDict = {

    }

    checkSide = {

    }

    temp = {
      'barcode': None,
      'mrz': None
    }

    documentBarcode, barcodeType, barcodetbr = barcodeSide(documentType=tipoDocumento, documentSide=ladoDocumento, barcodeData=barcodeData)
    if(documentBarcode):
      barcodes = barcodeReader(imagenDocumento, efirmaId, ladoDocumento, barcodeType, barcodetbr)

      rotatedImage = rotateBarcode(imagenDocumento, barcodes=barcodes)

      detectedBarcodes = 'OK' if(len(barcodes) >= 1) else '!OK'

      resultsDict['barcode'] = detectedBarcodes
      resultsDict['image'] = imageToDataURL(rotatedImage)

      if(tipoDocumento != 'CEDULA DE CIUDADANIA'):
        checkSide['barcode'] = detectedBarcodes

      if(tipoDocumento == 'CEDULA DE CIUDADANIA'):
        temp['barcode']= detectedBarcodes

      if(detectedBarcodes != 'OK' and tipoDocumento != 'CEDULA DE CIUDADANIA'):
        messages.append('No se pudo detectar el código de barras del documento.')
    else:
      resultsDict['barcode'] = 'documento sin codigo de barras'

    # rotatedImage = orientation(documentoData)

    timeOcrInit = time.time()

    ocrResult, documentoOCRPre = ocr(preprocessedDocument)

    # typeDetected, documentTypeValidation = validateDocumentType(tipoDocumento, ladoDocumento, documentoOCRSencillo)
    # countryCode, countryDetected, documentCountryValidation = validateDocumentCountry( documentoOCRSencillo)

    validarLadoPre = validarLadoDocumento(tipoDocumento, ladoDocumento, documentoOCRPre, ocrData)
    # validarLadoSencillo = validarLadoDocumento(tipoDocumento, ladoDocumento, documentoData, documentoOCRSencillo)
    totalValidacion = validarLadoPre

    checkSide['validation'] = 'OK'if totalValidacion >= 3 else '!OK'

    # typeDetected, documentTypeValidation = validateDocumentType(tipoDocumento, ladoDocumento, documentoOCRSencillo)
    typeDetectedPre, documentTypeValidationPre = validateDocumentType(tipoDocumento, ladoDocumento, documentoOCRPre, ocrData)

    # countryCode, countryDetected, documentCountryValidation = validateDocumentCountry( documentoOCRSencillo)
    countryCodePre, countryDetectedPre, documentCountryValidationPre = validateDocumentCountry( documentoOCRPre, country=userCountry)

    documentType, documentValidation = testingType([{'type':typeDetectedPre, 'validation':documentTypeValidationPre}])
    codeC, country, countryValidation = testingCountry([{'country': countryCodePre, 'countryDetected': countryDetectedPre, 'validation': documentCountryValidationPre}])

    timeOcrEnd = time.time()
    OCRtime = timeOcrInit - timeOcrEnd
    print('ocr time ', OCRtime)

    if(documentValidation != 'OK'):
      messages.append('El tipo de documento no coincide con el seleccionado.')
    
    if(countryValidation != 'OK'):
      messages.append('El país del documento no coincide.')

    checkSide['documentValidation'] = documentValidation
    checkSide['countryValidation'] = countryValidation

    # image = imageToDataURL(documentoData)

    resultsDict['document'] = {
        'code': codeC,
        'country': country,
        'countryCheck':countryValidation,
        'type':documentType,
        'typeCheck':documentValidation
    }

    codeTimeInit = time.time()


    mrzLetter, documentMRZ = MRZSide(documentType=tipoDocumento, documentSide=ladoDocumento, mrzData=mrzData)
    if(documentMRZ):

      nameHasK = nombre.find("k")
      lastNamehasK = apellido.find("k")

      mrz =  extractMRZ(ocr=documentoOCRPre, mrzStartingLetter=mrzLetter)

      if(nameHasK == -1 or lastNamehasK == -1):
        mrz = mrz.replace('K', ' ')

      if(mrz == 'Requiere verificar – DATOS INCOMPLETOS' and tipoDocumento != 'CEDULA DE CIUDADANIA'):
        messages.append('No se pudo detecar el código mrz del documento.')

      extractName = mrzInfo(mrz=mrz, searchTerm=nombre)
      extractLastname = mrzInfo(mrz=mrz, searchTerm=apellido)


      nameMRZ = comparisonMRZInfo([extractName], nombre)
      lastNameMRZ = comparisonMRZInfo([extractLastname], apellido)

      # resultsDict['document']['isExpired'] = False

      resultsDict['mrz'] = {
        'code': mrz,
        'data': {
          'name': nameMRZ['data'] if(len(nameMRZ['data']) >= 1) else '',
          'lastName': lastNameMRZ['data'] if(len(lastNameMRZ['data']) >= 1) else ''
        },
        'percentages': {
          'name': nameMRZ['percent'],
          'lastName': lastNameMRZ['percent']
        }
      }

      if(tipoDocumento != 'CEDULA DE CIUDADANIA'):
        checkSide['mrzNamePercent'] = 'OK' if nameMRZ['percent'] >= 50 else '!OK'
        checkSide['mrzLastNamePercent'] = 'OK' if lastNameMRZ['percent'] >= 50 else '!OK'
      
      if(tipoDocumento == 'CEDULA DE CIUDADANIA'):
        temp['mrz']= {
          'mrzNamePercent': 'OK' if nameMRZ['percent'] >= 50 else '!OK',
          'mrzLastNamePercent': 'OK' if lastNameMRZ['percent'] >= 50 else '!OK'
        }

      if(nameMRZ['percent']<= 50 and tipoDocumento != 'CEDULA DE CIUDADANIA'):
        messages.append('No se encontró el nombre en el codigo mrz.')
      if(lastNameMRZ['percent']<= 50 and tipoDocumento != 'CEDULA DE CIUDADANIA'):
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

    if(tipoDocumento == 'CEDULA DE CIUDADANIA' and documentMRZ and documentBarcode):
      if (temp['barcode'] != None):
        checkSide['barcode'] =temp['barcode']
        messages.append('No se pudo detectar el código de barras del documento.')
      if(temp['mrz'] != None):
        messages.append('No se encontró el codigo mrz.')
        checkSide['mrzNamePercent'] = temp['mrz']['mrzNamePercent']
        checkSide['mrzLastNamePercent'] = temp['mrz']['mrzLastNamePercent']


    validSide, _, _ = results(51, 'AUTOMATICA', checkSide)

    codeTimeEnd = time.time()
    codeTime = codeTimeInit - codeTimeEnd
    print('codes time ', codeTime)

    resultsDict['messages'] = messages

    resultsDict['validSide'] = 'OK' if(validSide and len(messages) <= 0) else '!OK'

    return jsonify(resultsDict)

@ocr_bp.route('/barcode-reader', methods=['POST'])
def reader():

  id = request.args.get('id')
  reqBody = request.get_json()
  image = reqBody['image']
  documentType = reqBody['documentType']
  documentSide = reqBody['documentSide']
  imageData = readDataURL(image)

  print(id, documentType, documentSide)

  documentBarcode, barcodeType, barcodetbr = barcodeSide(documentType=documentType, documentSide=documentSide)

  barcodes = barcodeReader(imageData, id, documentSide, barcodeType, barcodetbr)

  print(barcodes)

  return jsonify({
    'image': image,
    'barcodeData': barcodes
  })
