
from flask import Blueprint, request, jsonify
from lector_codigo import barcodeReader, barcodeSide, rotateBarcode
from ocr import comparacionOCR, ocr, validacionOCR, validarLadoDocumento, validateDocumentCountry, validateDocumentType
from mrz import MRZSide, extractMRZ, mrzInfo, comparisonMRZInfo, expiracyDateMRZ
from reconocimiento import orientacionImagen, verifyFaces
from utilidades import readDataURL, resizeHandle, resizeImage, textNormalize, imageToDataURL
from check_result import testingCountry, testingType, results
import time
# import test_reglas?

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

@ocr_bp.route('/rotacion-test', methods=['POST'])
def rotacionTest():
    reqBody = request.get_json()
    imagen = reqBody['imagen']
    imagenData = readDataURL(imagen)

    # test =  test_reglas.correct_orientation(imagenData)

    # print(test)

    return jsonify({'testing': 'testing'})


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
    testing = reqBody['test']

    if(testing):
      nombre = 'test'
      apellido = 'test'
      numeroDocumento = '9999'
      ladoDocumento = 'anverso'
      imagenPersona = imagenDocumento
      tipoDocumento = 'DNI'

    nombre = textNormalize(nombre)
    apellido = textNormalize(apellido)
    documentoData = readDataURL(imagenDocumento)
    personaData = readDataURL(imagenPersona)
    # documentoData = resizeHandle(documentoData, max_dimension=1200)


    selfieOrientada, carasImagenPersona = orientacionImagen(personaData)

    documentoOrientado, carasImagenDocumento = orientacionImagen(documentoData)

    # faceCoords = carasImagenDocumento[0][1] if (len(carasImagenDocumento) >= 1) else (0,0)
  
    timerOrientacion = time.time()
    # documentoOrientado = (documentoData, reference=faceCoords, documentType=tipoDocumento, documentSide=ladoDocumento)
    # documentoOrientado, carasImagenDocumento = orientacionImagen(documentoData)
    timerOrientacionEnd = time.time()
    orientacionTime = timerOrientacion - timerOrientacionEnd
    print(orientacionTime)

    timeRecognitionInit = time.time()
    _, confidence, _ = verifyFaces(selfieOrientada, documentoOrientado)
    timeRecognitionEnd = time.time()
    recognitionTime = timeRecognitionInit - timeRecognitionEnd
    print('recognition timing ', recognitionTime)


    timeOcrInit = time.time()
    documentoOCRPre = ocr(documentoOrientado, preprocesado=True)

    validarLadoPre = validarLadoDocumento(tipoDocumento, ladoDocumento, documentoOrientado, documentoOCRPre)
    totalValidacionLado = validarLadoPre 
    checkSide = {
      'validation': 'OK'if totalValidacionLado >= 3 else '!OK',
      'face': 'OK' if confidence <= confidenceValue else '!OK'
    }

    messages = []

    #REVISION
    # isExpired = expiracyDateOCR([*documentoOCRPre, *documentoOCRSencillo], tipoDocumento)

    # checkSide['expiracy'] = 'OK' if (not isExpired) else '!OK'

    # if(isExpired):
    #   messages.append('El documento esta expirado.')

    if(confidence >= confidenceValue):
      messages.append('Los rostros no coincidén.')

    typeDetectedPre, documentTypeValidationPre = validateDocumentType(tipoDocumento, ladoDocumento, documentoOCRPre)


    countryCodePre, countryDetectedPre, documentCountryValidationPre = validateDocumentCountry( documentoOCRPre)

    documentType, documentValidation = testingType([{'type':typeDetectedPre, 'validation':documentTypeValidationPre}])
    codeC, country, countryValidation = testingCountry([{'country': countryCodePre, 'countryDetected': countryDetectedPre, 'validation': documentCountryValidationPre}])

    if(documentValidation != 'OK'):
      messages.append('El tipo de documento no coincide con el seleccionado.')
    
    if(countryValidation != 'OK'):
      messages.append('El país del documento no coincide.')

    if(codeC == 'HND' or country == 'HONDURAS' and tipoDocumento != 'Pasaporte'):
      idLength = len(numeroDocumento)
      firstNums = numeroDocumento[0:4]
      middleNums = numeroDocumento[4:8]
      lastNums = numeroDocumento[8:idLength]

      numeroDocumento = f"{firstNums} {middleNums} {lastNums}"


    nombrePreOCR, porcentajeNombrePre = validacionOCR(documentoOCRPre, nombre)
    apellidoPreOCR, porcentajeApellidoPre = validacionOCR(documentoOCRPre, apellido)
    numeroDocumentoPreOCR, porcentajeDocumentoPre = validacionOCR(documentoOCRPre, numeroDocumento)

    # nombreComparado, porcentajeNombreComparado = comparacionOCR(porcentajePre=porcentajeNombrePre, porcentajeSencillo=porcentajeNombre, ocrPre=nombrePreOCR, ocrSencillo=nombreOCR)
    # apellidoComparado, porcentajeApellidoComparado = comparacionOCR(porcentajePre=porcentajeApellidoPre, porcentajeSencillo=porcentajeApellido, ocrPre=apellidoPreOCR, ocrSencillo=apellidoOCR)
    # documentoComparado, porcentajeDocumentoComparado = comparacionOCR(porcentajePre=porcentajeDocumentoPre, porcentajeSencillo=porcentajeDocumento, ocrPre=numeroDocumentoPreOCR, ocrSencillo=numeroDocumentoOCR)

    timeOcrEnd = time.time()
    OCRtime = timeOcrInit - timeOcrEnd
    print('ocr time ', OCRtime)

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

    image = resizeImage(documentoOrientado, 95)
    image = imageToDataURL(image)

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
        'isExpired': False
      }
    }

    codeTimeInit = time.time()

    hasbarcode,barcodeType,barcodetbr  = barcodeSide(documentType=tipoDocumento, documentSide=ladoDocumento)
    if(hasbarcode):
      detectedBarcodes = barcodeReader(imagenDocumento, efirmaId, ladoDocumento, barcodeType, barcodetbr)
      resultsDict['barcode'] = detectedBarcodes
      checkSide['barcode'] = detectedBarcodes
      # if(detectedBarcodes != 'OK'):
        # messages.append('No se pudo detectar el código de barras del documento.')
    else:
      resultsDict['barcode'] = 'documento sin codigo de barras'

    mrzLetter, documentMRZ = MRZSide(documentType=tipoDocumento, documentSide=ladoDocumento)
    if(documentMRZ):
      # mrz = extractMRZ(ocr=documentoOCRSencillo, mrzStartingLetter=mrzLetter)
      mrzPre =  extractMRZ(ocr=documentoOCRPre, mrzStartingLetter=mrzLetter)

      if(mrzPre == 'Requiere verificar – DATOS INCOMPLETOS'):
        messages.append('No se pudo detecar el código mrz del documento.')


      extractNamePre = mrzInfo(mrz=mrzPre, searchTerm=nombre)
      extractLastnamePre = mrzInfo(mrz=mrzPre, searchTerm=apellido)

      nameMRZ = comparisonMRZInfo([ extractNamePre], nombre)
      lastNameMRZ = comparisonMRZInfo([ extractLastnamePre], apellido)

    

      resultsDict['mrz'] = {
        'code':  mrzPre,
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
    # imagenDocumento = resizeHandle(imagenDocumento, max_dimension=1200)


    nombre = textNormalize(nombre)
    apellido = textNormalize(apellido)
    # documentoData = readDataURL(imagenDocumento)
    documentoData = None

    resultsDict = {

    }

    checkSide = {

    }

    documentBarcode, barcodeType, barcodetbr = barcodeSide(documentType=tipoDocumento, documentSide=ladoDocumento)
    if(documentBarcode):
      barcodes = barcodeReader(imagenDocumento, efirmaId, ladoDocumento, barcodeType, barcodetbr)

      rotatedImage = rotateBarcode(imagenDocumento, barcodes=barcodes)
      rotatedImage = resizeImage(rotatedImage, 95)
      detectedBarcodes = 'OK' if(len(barcodes) >= 1) else '!OK'
  
      documentoData = rotatedImage
      resultsDict['barcode'] = detectedBarcodes
      # resultsDict['image'] = imageToDataURL(rotatedImage)
      checkSide['barcode'] = detectedBarcodes
      if(detectedBarcodes != 'OK'):
        messages.append('No se pudo detectar el código de barras del documento.')
    else:
      resultsDict['barcode'] = 'documento sin codigo de barras'

    # rotatedImage = orientation(documentoData)

    timeOcrInit = time.time()

    # documentoOCRSencillo = ocr(documentoData, preprocesado=False)
    documentoOCRPre = ocr(documentoData, preprocesado=True)

    # typeDetected, documentTypeValidation = validateDocumentType(tipoDocumento, ladoDocumento, documentoOCRSencillo)
    # countryCode, countryDetected, documentCountryValidation = validateDocumentCountry( documentoOCRSencillo)

    validarLadoPre = validarLadoDocumento(tipoDocumento, ladoDocumento, documentoData, documentoOCRPre)
    # validarLadoSencillo = validarLadoDocumento(tipoDocumento, ladoDocumento, documentoData, documentoOCRSencillo)
    totalValidacion = validarLadoPre

    checkSide['validation'] = 'OK'if totalValidacion >= 3 else '!OK'

    # typeDetected, documentTypeValidation = validateDocumentType(tipoDocumento, ladoDocumento, documentoOCRSencillo)
    typeDetectedPre, documentTypeValidationPre = validateDocumentType(tipoDocumento, ladoDocumento, documentoOCRPre)

    # countryCode, countryDetected, documentCountryValidation = validateDocumentCountry( documentoOCRSencillo)
    countryCodePre, countryDetectedPre, documentCountryValidationPre = validateDocumentCountry( documentoOCRPre)

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

    # documentBarcode = barcodeSide(documentType=tipoDocumento, documentSide=ladoDocumento)
    # if(documentBarcode):
    #   detectedBarcodes = barcodeReader(imagenDocumento, efirmaId, ladoDocumento)
    #   resultsDict['barcode'] = detectedBarcodes
    #   checkSide['barcode'] = detectedBarcodes
    #   if(detectedBarcodes != 'OK'):
    #     messages.append('No se pudo detectar el código de barras del documento.')
    # else:
    #   resultsDict['barcode'] = 'documento sin codigo de barras'

    mrzLetter, documentMRZ = MRZSide(documentType=tipoDocumento, documentSide=ladoDocumento)
    if(documentMRZ):


      nameHasK = nombre.find("k")
      lastNamehasK = apellido.find("k")

      # mrz = extractMRZ(ocr=documentoOCRSencillo, mrzStartingLetter=mrzLetter)
      mrzPre =  extractMRZ(ocr=documentoOCRPre, mrzStartingLetter=mrzLetter)

      if(nameHasK == -1 or lastNamehasK == -1):
        # mrz = mrz.replace('K', ' ')
        mrzPre = mrzPre.replace('K', ' ')

      if(mrzPre == 'Requiere verificar – DATOS INCOMPLETOS'):
        messages.append('No se pudo detecar el código mrz del documento.')

      # extractName = mrzInfo(mrz=mrz, searchTerm=nombre)
      # extractLastname = mrzInfo(mrz=mrz, searchTerm=apellido)

      extractNamePre = mrzInfo(mrz=mrzPre, searchTerm=nombre)
      extractLastnamePre = mrzInfo(mrz=mrzPre, searchTerm=apellido)


      nameMRZ = comparisonMRZInfo([extractNamePre], nombre)
      lastNameMRZ = comparisonMRZInfo([extractLastnamePre], apellido)

      #REVISION
      # isExpired = expiracyDateMRZ([*documentoOCRSencillo, *documentoOCRPre])

      # checkSide['expiracy'] = 'OK' if (not isExpired) else '!OK'

      # if(isExpired):
      #   messages.append('El documento esta expirado.')

      resultsDict['document']['isExpired'] = False

      resultsDict['mrz'] = {
        'code': mrzPre,
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

    resultsDict['validSide'] = 'OK' if(validSide and len(messages) <= 0) else '!OK'

    # resultsDict['validSide'] = 'OK' 

    return jsonify(resultsDict)