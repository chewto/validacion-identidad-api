
from flask import Blueprint, request, jsonify
from lector_codigo import barcodeReader, barcodeSide
from ocr import comparacionOCR, ocr, validacionOCR, validarLadoDocumento, validateDocumentCountry, validateDocumentType, expiracyDateOCR
from mrz import MRZSide, extractMRZ, mrzInfo, comparisonMRZInfo, expiracyDateMRZ
from reconocimiento import orientacionImagen, verifyFaces
from utilidades import readDataURL, textNormalize
from check_result import testingCountry, testingType, results

import time

ocr_bp = Blueprint('ocr', __name__, url_prefix='/ocr')

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

    nombre = textNormalize(nombre)
    apellido = textNormalize(apellido)
    documentoData = readDataURL(imagenDocumento)
    personaData = readDataURL(imagenPersona)

    selfieOrientada, carasImagenPersona = orientacionImagen(personaData)
    documentoOrientado, carasImagenDocumento = orientacionImagen(documentoData)

    timeRecognitionInit = time.time()
    _, confidence, _ = verifyFaces(selfieOrientada, documentoOrientado)
    timeRecognitionEnd = time.time()
    recognitionTime = timeRecognitionInit - timeRecognitionEnd
    print('recognition timing ', recognitionTime)


    timeOcrInit = time.time()
    documentoOCRSencillo = ocr(documentoOrientado, preprocesado=False)
    documentoOCRPre = ocr(documentoOrientado, preprocesado=True)

    validarLadoPre = validarLadoDocumento(tipoDocumento, ladoDocumento, documentoOrientado, preprocesado=True)
    validarLadoSencillo = validarLadoDocumento(tipoDocumento, ladoDocumento, documentoOrientado, preprocesado=False)
    totalValidacionLado = validarLadoPre + validarLadoSencillo
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

    typeDetected, documentTypeValidation = validateDocumentType(tipoDocumento, ladoDocumento, documentoOCRSencillo)
    typeDetectedPre, documentTypeValidationPre = validateDocumentType(tipoDocumento, ladoDocumento, documentoOCRPre)

    countryCode, countryDetected, documentCountryValidation = validateDocumentCountry( documentoOCRSencillo)
    countryCodePre, countryDetectedPre, documentCountryValidationPre = validateDocumentCountry( documentoOCRPre)

    documentType, documentValidation = testingType([{'type':typeDetected, 'validation':documentTypeValidation},{'type':typeDetectedPre, 'validation':documentTypeValidationPre}])
    codeC, country, countryValidation = testingCountry([{'country': countryCode, 'countryDetected': countryDetected, 'validation': documentCountryValidation}, {'country': countryCodePre, 'countryDetected': countryDetectedPre, 'validation': documentCountryValidationPre}])

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

    nombreOCR, porcentajeNombre = validacionOCR(documentoOCRSencillo, nombre)
    apellidoOCR, porcentajeApellido = validacionOCR(documentoOCRSencillo, apellido)
    numeroDocumentoOCR, porcentajeDocumento = validacionOCR(documentoOCRSencillo, numeroDocumento)

    nombrePreOCR, porcentajeNombrePre = validacionOCR(documentoOCRPre, nombre)
    apellidoPreOCR, porcentajeApellidoPre = validacionOCR(documentoOCRPre, apellido)
    numeroDocumentoPreOCR, porcentajeDocumentoPre = validacionOCR(documentoOCRPre, numeroDocumento)

    nombreComparado, porcentajeNombreComparado = comparacionOCR(porcentajePre=porcentajeNombrePre, porcentajeSencillo=porcentajeNombre, ocrPre=nombrePreOCR, ocrSencillo=nombreOCR)
    apellidoComparado, porcentajeApellidoComparado = comparacionOCR(porcentajePre=porcentajeApellidoPre, porcentajeSencillo=porcentajeApellido, ocrPre=apellidoPreOCR, ocrSencillo=apellidoOCR)
    documentoComparado, porcentajeDocumentoComparado = comparacionOCR(porcentajePre=porcentajeDocumentoPre, porcentajeSencillo=porcentajeDocumento, ocrPre=numeroDocumentoPreOCR, ocrSencillo=numeroDocumentoOCR)

    timeOcrEnd = time.time()
    OCRtime = timeOcrInit - timeOcrEnd
    print('ocr time ', OCRtime)

    checkSide['documentValidation'] = documentValidation
    checkSide['countryValidation'] = countryValidation
    checkSide['percentName'] = 'OK' if porcentajeNombreComparado >= 50 else '!OK'
    checkSide['percentLastname'] = 'OK' if porcentajeApellidoComparado >= 50 else '!OK'
    checkSide['percentID'] ='OK' if porcentajeDocumentoComparado >= 50 else '!OK'

    if(porcentajeNombreComparado <= 50):
      messages.append('El nombre no se ha encontrado en el documento.')

    if(porcentajeApellidoComparado <= 50):
      messages.append('El apellido no se ha encontrado en el documento.')

    if(porcentajeDocumentoComparado <= 50):
      messages.append('El numero del identificación no se ha encontrado en el documento.')

    resultsDict = {
      'ocr': {
        'data':{
          'name': nombreComparado,
          'lastName': apellidoComparado,
          'ID': documentoComparado
        },
        'percentage': {
          'name': porcentajeNombreComparado,
          'lastName': porcentajeApellidoComparado,
          'ID': porcentajeDocumentoComparado
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

    documentBarcode = barcodeSide(documentType=tipoDocumento, documentSide=ladoDocumento)
    if(documentBarcode):
      detectedBarcodes = barcodeReader(imagenDocumento, efirmaId, ladoDocumento)
      resultsDict['barcode'] = detectedBarcodes
      checkSide['barcode'] = detectedBarcodes
      if(detectedBarcodes != 'OK'):
        messages.append('No se pudo detectar el código de barras del documento.')
    else:
      resultsDict['barcode'] = 'documento sin codigo de barras'

    mrzLetter, documentMRZ = MRZSide(documentType=tipoDocumento, documentSide=ladoDocumento)
    if(documentMRZ):
      mrz = extractMRZ(ocr=documentoOCRSencillo, mrzStartingLetter=mrzLetter)
      mrzPre =  extractMRZ(ocr=documentoOCRPre, mrzStartingLetter=mrzLetter)

      if(mrz == 'Requiere verificar – DATOS INCOMPLETOS' and mrzPre == 'Requiere verificar – DATOS INCOMPLETOS'):
        messages.append('No se pudo detecar el código mrz del documento.')

      extractName = mrzInfo(mrz=mrz, searchTerm=nombre)
      extractLastname = mrzInfo(mrz=mrz, searchTerm=apellido)

      extractNamePre = mrzInfo(mrz=mrzPre, searchTerm=nombre)
      extractLastnamePre = mrzInfo(mrz=mrzPre, searchTerm=apellido)

      nameMRZ = comparisonMRZInfo([extractName, extractNamePre], nombre)
      lastNameMRZ = comparisonMRZInfo([extractLastname, extractLastnamePre], apellido)

    

      resultsDict['mrz'] = {
        'code': {
          'raw': mrz,
          'preprocessed': mrzPre
        },
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
        'code': {
          'raw':'',
          'preprocessed': ''
        },
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
      resultsDict['validSide'] = 'OK' if(validSide) else '!OK'
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

    nombre = textNormalize(nombre)
    apellido = textNormalize(apellido)
    documentoData = readDataURL(imagenDocumento)

    timeOcrInit = time.time()

    documentoOCRSencillo = ocr(documentoData, preprocesado=False)
    documentoOCRPre = ocr(documentoData, preprocesado=True)

    typeDetected, documentTypeValidation = validateDocumentType(tipoDocumento, ladoDocumento, documentoOCRSencillo)
    countryCode, countryDetected, documentCountryValidation = validateDocumentCountry( documentoOCRSencillo)

    validarLadoPre = validarLadoDocumento(tipoDocumento, ladoDocumento, documentoData, preprocesado=True)
    validarLadoSencillo = validarLadoDocumento(tipoDocumento, ladoDocumento, documentoData, preprocesado=False)
    totalValidacion = validarLadoPre + validarLadoSencillo

    checkSide = {
      'validation': 'OK'if totalValidacion >= 3 else '!OK'
    }

    typeDetected, documentTypeValidation = validateDocumentType(tipoDocumento, ladoDocumento, documentoOCRSencillo)
    typeDetectedPre, documentTypeValidationPre = validateDocumentType(tipoDocumento, ladoDocumento, documentoOCRPre)

    countryCode, countryDetected, documentCountryValidation = validateDocumentCountry( documentoOCRSencillo)
    countryCodePre, countryDetectedPre, documentCountryValidationPre = validateDocumentCountry( documentoOCRPre)

    documentType, documentValidation = testingType([{'type':typeDetected, 'validation':documentTypeValidation},{'type':typeDetectedPre, 'validation':documentTypeValidationPre}])
    codeC, country, countryValidation = testingCountry([{'country': countryCode, 'countryDetected': countryDetected, 'validation': documentCountryValidation}, {'country': countryCodePre, 'countryDetected': countryDetectedPre, 'validation': documentCountryValidationPre}])

    timeOcrEnd = time.time()
    OCRtime = timeOcrInit - timeOcrEnd
    print('ocr time ', OCRtime)

    if(documentValidation != 'OK'):
      messages.append('El tipo de documento no coincide con el seleccionado.')
    
    if(countryValidation != 'OK'):
      messages.append('El país del documento no coincide.')

    checkSide['documentValidation'] = documentValidation
    checkSide['countryValidation'] = countryValidation

    resultsDict = {
      'document':{
        'code': codeC,
        'country': country,
        'countryCheck':countryValidation,
        'type':documentType,
        'typeCheck':documentValidation
      }

    }

    codeTimeInit = time.time()

    documentBarcode = barcodeSide(documentType=tipoDocumento, documentSide=ladoDocumento)
    if(documentBarcode):
      detectedBarcodes = barcodeReader(imagenDocumento, efirmaId, ladoDocumento)
      resultsDict['barcode'] = detectedBarcodes
      checkSide['barcode'] = detectedBarcodes
      if(detectedBarcodes != 'OK'):
        messages.append('No se pudo detectar el código de barras del documento.')
    else:
      resultsDict['barcode'] = 'documento sin codigo de barras'

    mrzLetter, documentMRZ = MRZSide(documentType=tipoDocumento, documentSide=ladoDocumento)
    if(documentMRZ):
      mrz = extractMRZ(ocr=documentoOCRSencillo, mrzStartingLetter=mrzLetter)
      mrzPre =  extractMRZ(ocr=documentoOCRPre, mrzStartingLetter=mrzLetter)

      if(mrz == 'Requiere verificar – DATOS INCOMPLETOS' and mrzPre == 'Requiere verificar – DATOS INCOMPLETOS'):
        messages.append('No se pudo detecar el código mrz del documento.')

      extractName = mrzInfo(mrz=mrz, searchTerm=nombre)
      extractLastname = mrzInfo(mrz=mrz, searchTerm=apellido)

      extractNamePre = mrzInfo(mrz=mrzPre, searchTerm=nombre)
      extractLastnamePre = mrzInfo(mrz=mrzPre, searchTerm=apellido)

      nameMRZ = comparisonMRZInfo([extractName, extractNamePre], nombre)
      lastNameMRZ = comparisonMRZInfo([extractLastname, extractLastnamePre], apellido)

      #REVISION
      # isExpired = expiracyDateMRZ([*documentoOCRSencillo, *documentoOCRPre])

      # checkSide['expiracy'] = 'OK' if (not isExpired) else '!OK'

      # if(isExpired):
      #   messages.append('El documento esta expirado.')

      resultsDict['document']['isExpired'] = False

      resultsDict['mrz'] = {
        'code': {
          'raw': mrz,
          'preprocessed': mrzPre
        },
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
        'code': {
          'raw':'',
          'preprocessed': ''
        },
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

    resultsDict['validSide'] = 'OK' if(validSide) else '!OK'

    # resultsDict['validSide'] = 'OK' 

    return jsonify(resultsDict)