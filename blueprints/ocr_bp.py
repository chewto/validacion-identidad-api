
import json
from flask import Blueprint, request, jsonify
from lector_codigo import barcodeReader, barcodeSide, rotateBarcode
from name_search import searchId, searchName
from ocr import comparacionOCR, ocr, validacionOCR, validarLadoDocumento, validateDocumentCountry, validateDocumentType, preprocessing
from mrz import MRZSide, extractMRZ, mrzInfo, comparisonMRZInfo
from expiry import expiryDateOCR, hasExpiryDate
from reconocimiento import orientacionImagen, verifyFaces
from utilidades import readDataURL, textNormalize, imageToDataURL, fileCv2, orientation
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
    is_testing = request.args.get('testing', 'false').lower() == 'true'

    if is_testing:
      efirmaId = request.form.get('id')
      imagenPersona = request.files.get('imagenPersona')
      imagenDocumento = request.files.get('imagen')
      ladoDocumento = request.form.get('ladoDocumento')
      tipoDocumento = request.form.get('tipoDocumento')
      nombre = request.form.get('nombre')
      apellido = request.form.get('apellido')
      numeroDocumento = request.form.get('documento')
      userCountry = request.form.get('country')
      tries = request.form.get('tries')
      tries = int(tries)
      personaData = fileCv2(imagenPersona)
      documentoData = fileCv2(imagenDocumento)
    else:
      reqBody = request.get_json()
      efirmaId = reqBody.get('id')
      imagenPersona = reqBody.get('imagenPersona')
      imagenDocumento = reqBody.get('imagen')
      ladoDocumento = reqBody.get('ladoDocumento')
      tipoDocumento = reqBody.get('tipoDocumento')
      nombre = reqBody.get('nombre')
      apellido = reqBody.get('apellido')
      numeroDocumento = reqBody.get('documento')
      userCountry = reqBody.get('country')
      tries = reqBody.get('tries')
      tries = int(tries)
      personaData = readDataURL(imagenPersona)
      documentoData = readDataURL(imagenDocumento)

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
    documentType, documentValidation = testingType([{'type':typeDetectedPre, 'validation':documentTypeValidationPre}])

    if(documentValidation != 'OK'):
      messages.append('El tipo de documento no coincide con el seleccionado.')

    isExpired = None

    # hasExpiry, namedMonth, datePosition, keywords, dateFormat = hasExpiryDate(tipoDocumento, ladoDocumento, country=userCountry)
    # if(hasExpiry):
    #   isExpired = expiryDateOCR(ocrResult,datePosition,keywords,namedMonth,dateFormat)

    #   checkSide['expiracy'] = 'OK' if (not isExpired) else '!OK'

    #   if(isExpired):
    #     messages.append('El documento esta expirado.')

  

    if(userCountry == 'HND' and tipoDocumento != 'PASAPORTE' and numeroDocumento is not None):
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
    checkSide['percentName'] = 'OK' if porcentajeNombrePre >= 50 else '!OK'
    checkSide['percentLastname'] = 'OK' if porcentajeApellidoPre >= 50 else '!OK'
    checkSide['percentID'] ='OK' if porcentajeDocumentoPre >= 50 else '!OK'

    if(porcentajeNombrePre <= 50):
      messages.append('El nombre no se ha encontrado en el documento.')

    if(porcentajeApellidoPre <= 50):
      messages.append('El apellido no se ha encontrado en el documento.')

    if(porcentajeDocumentoPre <= 50):
      messages.append('El número del identificación no se ha encontrado en el documento.')


  
    image = imageToDataURL(preprocessedDocument)

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
      mrz =  extractMRZ(documentoData)

      print(mrz)

      if(mrz == "No se pudo detectar MRZ válido en la imagen."):
        messages.append('No se pudo detecar el código mrz del documento.')

      extractName = mrzInfo(mrz=mrz['raw_text'].replace("\n", "") if 'raw_text' in mrz else '', searchTerm=nombre)
      extractLastname = mrzInfo(mrz=mrz['raw_text'].replace("\n", "") if 'raw_text' in mrz else '', searchTerm=apellido)

      nameMRZ = comparisonMRZInfo([extractName], nombre, 'name')
      lastNameMRZ = comparisonMRZInfo([extractLastname], apellido, 'surname')

      # resultsDict['document']['isExpired'] = False

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

      checkSide['mrzNamePercent'] = 'OK' if nameMRZ['percent'] >= 50 else '!OK'
      checkSide['mrzLastNamePercent'] = 'OK' if lastNameMRZ['percent'] >= 50 else '!OK'

      if(nameMRZ['percent']<= 50):
        messages.append('No se encontró el nombre en el codigo mrz.')
      if(lastNameMRZ['percent']<= 50):
        messages.append('No se encontró el apellido en el codigo mrz.')

      if 'country' in mrz:
        countryCodePre, countryDetectedPre, documentCountryValidationPre = validateDocumentCountry( [mrz['country']], country=userCountry)
        codeC, country, countryValidation = testingCountry([{'country': countryCodePre, 'countryDetected': countryDetectedPre, 'validation': documentCountryValidationPre}])

        if(countryValidation != 'OK'):
          messages.append('El país del documento no coincide.')

        resultsDict['document']['code'] = codeC
        resultsDict['document']['country'] = country
        resultsDict['document']['countryCheck'] = countryValidation

        checkSide['countryValidation'] = countryValidation
      else:
        countryCodePre, countryDetectedPre, documentCountryValidationPre = validateDocumentCountry( documentoOCRPre, country=userCountry)
        codeC, country, countryValidation = testingCountry([{'country': countryCodePre, 'countryDetected': countryDetectedPre, 'validation': documentCountryValidationPre}])

        if(countryValidation != 'OK'):
          messages.append('El país del documento no coincide.')

        resultsDict['document']['code'] = codeC
        resultsDict['document']['country'] = country
        resultsDict['document']['countryCheck'] = countryValidation

        checkSide['countryValidation'] = countryValidation

    else:

      countryCodePre, countryDetectedPre, documentCountryValidationPre = validateDocumentCountry( documentoOCRPre, country=userCountry)
      codeC, country, countryValidation = testingCountry([{'country': countryCodePre, 'countryDetected': countryDetectedPre, 'validation': documentCountryValidationPre}])

      if(countryValidation != 'OK'):
        messages.append('El país del documento no coincide.')

      resultsDict['document']['code'] = codeC
      resultsDict['document']['country'] = country
      resultsDict['document']['countryCheck'] = countryValidation

      checkSide['countryValidation'] = countryValidation

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

    is_testing = request.args.get('testing', 'false').lower() == 'true'

    if is_testing:
      efirmaId = request.form.get('id')
      imagenPersona = request.files.get('imagenPersona')
      imagenDocumento = request.files.get('imagen')
      ladoDocumento = request.form.get('ladoDocumento')
      tipoDocumento = request.form.get('tipoDocumento')
      nombre = request.form.get('nombre')
      apellido = request.form.get('apellido')
      numeroDocumento = request.form.get('documento')
      userCountry = request.form.get('country')
      tries = request.form.get('tries')
      tries = int(tries)
      imagenDocumento = fileCv2(imagenDocumento)
    else:
      reqBody = request.get_json()
      efirmaId = reqBody.get('id')
      imagenPersona = None  # Not used in non-testing
      imagenDocumento = reqBody.get('imagen')
      ladoDocumento = reqBody.get('ladoDocumento')
      tipoDocumento = reqBody.get('tipoDocumento')
      nombre = reqBody.get('nombre')
      apellido = reqBody.get('apellido')
      numeroDocumento = reqBody.get('documento')
      userCountry = reqBody.get('country')
      tries = reqBody.get('tries')
      tries = int(tries)
      imagenDocumento = readDataURL(imagenDocumento)


    resolution = 600 if tries <=1 else 1080

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

      detectedBarcodes = 'OK' if(len(barcodes) >= 1) else '!OK'

      rotatedImage = orientation(preprocessedDocument) if detectedBarcodes == '!OK' else rotateBarcode(preprocessedDocument, barcodes=barcodes)

      resultsDict['barcode'] = detectedBarcodes
      resultsDict['image'] = imageToDataURL(rotatedImage)

      if(tipoDocumento != 'CEDULA DE CIUDADANIA'):
        checkSide['barcode'] = detectedBarcodes

      if(tipoDocumento == 'CEDULA DE CIUDADANIA'):
        temp['barcode']= detectedBarcodes


      if(detectedBarcodes == '!OK' and tipoDocumento != 'CEDULA DE CIUDADANIA'):
        messages.append('No se pudo detectar el código de barras del documento.')
    else:
      rotatedImage = orientation(imagenDocumento)
      resultsDict['image'] = imageToDataURL(rotatedImage)
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

    typeDetectedPre, documentTypeValidationPre = validateDocumentType(tipoDocumento, ladoDocumento, documentoOCRPre, ocrData)
    documentType, documentValidation = testingType([{'type':typeDetectedPre, 'validation':documentTypeValidationPre}])

    timeOcrEnd = time.time()
    OCRtime = timeOcrInit - timeOcrEnd
    print('ocr time ', OCRtime)

    if(documentValidation != 'OK'):
      messages.append('El tipo de documento no coincide con el seleccionado.')

    checkSide['documentValidation'] = documentValidation

    # image = imageToDataURL(documentoData)

    resultsDict['document'] = {
        # 'code': codeC,
        # 'country': country,
        # 'countryCheck':countryValidation,
        'type':documentType,
        'typeCheck':documentValidation
    }

    codeTimeInit = time.time()


    mrzLetter, documentMRZ = MRZSide(documentType=tipoDocumento, documentSide=ladoDocumento, mrzData=mrzData)
    if(documentMRZ):

      nameHasK = nombre.find("k")
      lastNamehasK = apellido.find("k")

      mrz =  extractMRZ(imagenDocumento)

      print(mrz)

      # if(nameHasK == -1 or lastNamehasK == -1):
      #   mrz = mrz['raw_text'].replace('K', ' ')

      if(mrz == "No se pudo detectar MRZ válido en la imagen." and tipoDocumento != 'CEDULA DE CIUDADANIA'):
        messages.append('No se pudo detecar el código mrz del documento.')

      extractName = mrzInfo(mrz=mrz['raw_text'].replace("\n", "") if 'raw_text' in mrz else '', searchTerm=nombre)
      extractLastname = mrzInfo(mrz=mrz['raw_text'].replace("\n", "") if 'raw_text' in mrz else '', searchTerm=apellido)


      nameMRZ = comparisonMRZInfo([extractName], nombre, 'name')
      lastNameMRZ = comparisonMRZInfo([extractLastname], apellido, 'surname')

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

      if(tipoDocumento != 'CEDULA DE CIUDADANIA'):
        checkSide['mrzNamePercent'] = 'OK' if nameMRZ['percent'] >= 50 else '!OK'
        checkSide['mrzLastNamePercent'] = 'OK' if lastNameMRZ['percent'] >= 50 else '!OK'
      
      if(tipoDocumento == 'CEDULA DE CIUDADANIA'):
        temp['mrz']= {
          'mrz': 'OK' if 'raw_text' in mrz else '!OK',
          'mrzNamePercent': 'OK' if nameMRZ['percent'] >= 50 else '!OK',
          'mrzLastNamePercent': 'OK' if lastNameMRZ['percent'] >= 50 else '!OK'
        }

      if(nameMRZ['percent']<= 50 and tipoDocumento != 'CEDULA DE CIUDADANIA'):
        messages.append('No se encontró el nombre en el codigo mrz.')
      if(lastNameMRZ['percent']<= 50 and tipoDocumento != 'CEDULA DE CIUDADANIA'):
        messages.append('No se encontró el apellido en el codigo mrz.')

      if 'country' in mrz:
        countryCodePre, countryDetectedPre, documentCountryValidationPre = validateDocumentCountry( [mrz['country']], country=userCountry)
        codeC, country, countryValidation = testingCountry([{'country': countryCodePre, 'countryDetected': countryDetectedPre, 'validation': documentCountryValidationPre}])

        if(countryValidation != 'OK'):
          messages.append('El país del documento no coincide.')

        resultsDict['document']['code'] = codeC
        resultsDict['document']['country'] = country
        resultsDict['document']['countryCheck'] = countryValidation

        checkSide['countryValidation'] = countryValidation
      else:
        countryCodePre, countryDetectedPre, documentCountryValidationPre = validateDocumentCountry( documentoOCRPre, country=userCountry)
        codeC, country, countryValidation = testingCountry([{'country': countryCodePre, 'countryDetected': countryDetectedPre, 'validation': documentCountryValidationPre}])

        if(countryValidation != 'OK'):
          messages.append('El país del documento no coincide.')

        resultsDict['document']['code'] = codeC
        resultsDict['document']['country'] = country
        resultsDict['document']['countryCheck'] = countryValidation

        checkSide['countryValidation'] = countryValidation
      
    else:
      countryCodePre, countryDetectedPre, documentCountryValidationPre = validateDocumentCountry( documentoOCRPre, country=userCountry)
      codeC, country, countryValidation = testingCountry([{'country': countryCodePre, 'countryDetected': countryDetectedPre, 'validation': documentCountryValidationPre}])
      if(countryValidation != 'OK'):
        messages.append('El país del documento no coincide.')

      resultsDict['document']['code'] = codeC
      resultsDict['document']['country'] = country
      resultsDict['document']['countryCheck'] = countryValidation

      checkSide['countryValidation'] = countryValidation

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

      print(temp)

      # Si se detecta MRZ y no código de barras, solo usar MRZ
      # Si se detecta MRZ y no código de barras, solo usar MRZ
      if temp['mrz'] is not None and (temp['barcode'] is None or temp['barcode'] == '!OK'):
        checkSide['mrzNamePercent'] = temp['mrz']['mrzNamePercent']
        checkSide['mrzLastNamePercent'] = temp['mrz']['mrzLastNamePercent']

        if temp['mrz']['mrz'] == 'OK':
          if temp['mrz']['mrzNamePercent'] != 'OK':
            messages.append('El nombre en el mrz no alcanzó el porcentaje minimo.')
          if temp['mrz']['mrzLastNamePercent'] != 'OK':
            messages.append('El apellido en el mrz no alcanzó el porcentaje minimo.')
        else:
          messages.append('No se pudo detectar el código de mrz del documento.')

      # Si se detecta código de barras y no MRZ, solo usar código de barras
      if temp['barcode'] is not None and (temp['mrz'] is None or temp['mrz']['mrz'] != 'OK'):
        checkSide['barcode'] = temp['barcode']
        if temp['barcode'] == '!OK':
          messages.append('No se pudo detectar el código de barras del documento.')

      # Si se detectan ambos, agregarlos al checkSide pero no mostrar mensajes
      if temp['mrz'] is not None and temp['mrz']['mrz'] == 'OK' and temp['barcode'] is not None and temp['barcode'] == 'OK':
        checkSide['mrzNamePercent'] = temp['mrz']['mrzNamePercent']
        checkSide['mrzLastNamePercent'] = temp['mrz']['mrzLastNamePercent']
        checkSide['barcode'] = temp['barcode']
        # Agregar mensajes si los porcentajes de nombre o apellido son bajos
        if temp['mrz']['mrzNamePercent'] != 'OK':
          messages.append('El nombre en el mrz no alcanzó el porcentaje minimo.')
        if temp['mrz']['mrzLastNamePercent'] != 'OK':
          messages.append('El apellido en el mrz no alcanzó el porcentaje minimo.')

      # Si no se detecta ninguno, agregar ambos mensajes
      if (temp['barcode'] is None or temp['barcode'] == '!OK') and (temp['mrz'] is None or temp['mrz']['mrz'] != 'OK'):
        messages.append('No se pudo detectar el código de barras del documento.')
        messages.append('No se pudo detectar el código de mrz del documento.')

    validSide, _, _ = results(51, 'AUTOMATICA', checkSide)

    codeTimeEnd = time.time()
    codeTime = codeTimeInit - codeTimeEnd
    print('codes time ', codeTime)

    resultsDict['messages'] = messages

    resultsDict['validSide'] = 'OK' if(validSide and len(messages) <= 0) else '!OK'

    return jsonify(resultsDict)


@ocr_bp.route('/mrz', methods=['POST'])
def mrzReader():
  image = request.files.get('image')
  imageData = fileCv2(image)

  result = extractMRZ(imageData)

  return jsonify(result)


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
