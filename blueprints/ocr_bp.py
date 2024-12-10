
from flask import Blueprint, request, jsonify
from lector_codigo import barcodeReader, barcodeSide
from ocr import comparacionOCR, ocr, validacionOCR, validarLadoDocumento, validateDocumentCountry, validateDocumentType
from mrz import MRZSide, extractMRZ, mrzInfo, comparisonMRZInfo
from reconocimiento import orientacionImagen, verifyFaces
from utilidades import readDataURL, textNormalize
from check_result import testingCountry, testingType, results

ocr_bp = Blueprint('ocr', __name__, url_prefix='/ocr')

@ocr_bp.route('/anverso', methods=['POST'])
def verificarAnverso():

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

    _, confidence, _ = verifyFaces(selfieOrientada, documentoOrientado)

    documentoOCRSencillo = ocr(documentoOrientado, preprocesado=False)
    documentoOCRPre = ocr(documentoOrientado, preprocesado=True)

    validarLadoPre = validarLadoDocumento(tipoDocumento, ladoDocumento, documentoOrientado, preprocesado=True)
    validarLadoSencillo = validarLadoDocumento(tipoDocumento, ladoDocumento, documentoOrientado, preprocesado=False)
    totalValidacionLado = validarLadoPre + validarLadoSencillo

    checkSide = {
      'validation': 'OK'if totalValidacionLado >= 1 else '!OK',
      'face': 'OK' if confidence <= 0.6 else '!OK'
    }

    typeDetected, documentTypeValidation = validateDocumentType(tipoDocumento, ladoDocumento, documentoOCRSencillo)
    typeDetectedPre, documentTypeValidationPre = validateDocumentType(tipoDocumento, ladoDocumento, documentoOCRPre)

    countryCode, countryDetected, documentCountryValidation = validateDocumentCountry( documentoOCRSencillo)
    countryCodePre, countryDetectedPre, documentCountryValidationPre = validateDocumentCountry( documentoOCRPre)

    documentType, documentValidation = testingType([{'type':typeDetected, 'validation':documentTypeValidation},{'type':typeDetectedPre, 'validation':documentTypeValidationPre}])
    codeC, country, countryValidation = testingCountry([{'country': countryCode, 'countryDetected': countryDetected, 'validation': documentCountryValidation}, {'country': countryCodePre, 'countryDetected': countryDetectedPre, 'validation': documentCountryValidationPre}])

    nombreOCR, porcentajeNombre = validacionOCR(documentoOCRSencillo, nombre)
    apellidoOCR, porcentajeApellido = validacionOCR(documentoOCRSencillo, apellido)
    numeroDocumentoOCR, porcentajeDocumento = validacionOCR(documentoOCRSencillo, numeroDocumento)

    nombrePreOCR, porcentajeNombrePre = validacionOCR(documentoOCRPre, nombre)
    apellidoPreOCR, porcentajeApellidoPre = validacionOCR(documentoOCRPre, apellido)
    numeroDocumentoPreOCR, porcentajeDocumentoPre = validacionOCR(documentoOCRPre, numeroDocumento)

    nombreComparado, porcentajeNombreComparado = comparacionOCR(porcentajePre=porcentajeNombrePre, porcentajeSencillo=porcentajeNombre, ocrPre=nombrePreOCR, ocrSencillo=nombreOCR)
    apellidoComparado, porcentajeApellidoComparado = comparacionOCR(porcentajePre=porcentajeApellidoPre, porcentajeSencillo=porcentajeApellido, ocrPre=apellidoPreOCR, ocrSencillo=apellidoOCR)
    documentoComparado, porcentajeDocumentoComparado = comparacionOCR(porcentajePre=porcentajeDocumentoPre, porcentajeSencillo=porcentajeDocumento, ocrPre=numeroDocumentoPreOCR, ocrSencillo=numeroDocumentoOCR)

    checkSide['documentValidation'] = documentValidation
    checkSide['countryValidation'] = countryValidation
    checkSide['percentName'] = 'OK' if porcentajeNombreComparado >= 50 else '!OK'
    checkSide['percentLastname'] = 'OK' if porcentajeApellidoComparado >= 50 else '!OK'
    checkSide['percentID'] ='OK' if porcentajeDocumentoComparado >= 50 else '!OK'

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
      'face': True if(confidence <= 0.60) else False,
      'document':{
        'code': codeC,
        'country': country,
        'countryCheck':countryValidation,
        'type':documentType,
        'typeCheck':documentValidation
      }
    }

    documentBarcode = barcodeSide(documentType=tipoDocumento, documentSide=ladoDocumento)
    if(documentBarcode):
      detectedBarcodes = barcodeReader(imagenDocumento, efirmaId, ladoDocumento)
      resultsDict['barcode'] = detectedBarcodes
      checkSide['barcode'] = detectedBarcodes
    else:
      resultsDict['barcode'] = 'documento sin codigo de barras'

    mrzLetter, documentMRZ = MRZSide(documentType=tipoDocumento, documentSide=ladoDocumento)
    if(documentMRZ):
      mrz = extractMRZ(ocr=documentoOCRSencillo, mrzStartingLetter=mrzLetter)
      mrzPre =  extractMRZ(ocr=documentoOCRPre, mrzStartingLetter=mrzLetter)

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

    if(confidence <= 0.60 and validSide):
      resultsDict['validSide'] = 'OK' if(validSide) else '!OK'
      return jsonify(resultsDict)

    resultsDict['validSide'] = '!OK'
    return jsonify(resultsDict)



#rutas para el front
@ocr_bp.route('/reverso', methods=['POST'])
def verificarReverso():

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

    documentoOCRSencillo = ocr(documentoData, preprocesado=False)
    documentoOCRPre = ocr(documentoData, preprocesado=True)

    typeDetected, documentTypeValidation = validateDocumentType(tipoDocumento, ladoDocumento, documentoOCRSencillo)
    countryCode, countryDetected, documentCountryValidation = validateDocumentCountry( documentoOCRSencillo)

    validarLadoPre = validarLadoDocumento(tipoDocumento, ladoDocumento, documentoData, preprocesado=True)
    validarLadoSencillo = validarLadoDocumento(tipoDocumento, ladoDocumento, documentoData, preprocesado=False)
    totalValidacion = validarLadoPre + validarLadoSencillo

    checkSide = {
      'validation': 'OK'if totalValidacion >= 1 else '!OK'
    }

    typeDetected, documentTypeValidation = validateDocumentType(tipoDocumento, ladoDocumento, documentoOCRSencillo)
    typeDetectedPre, documentTypeValidationPre = validateDocumentType(tipoDocumento, ladoDocumento, documentoOCRPre)


    countryCode, countryDetected, documentCountryValidation = validateDocumentCountry( documentoOCRSencillo)
    countryCodePre, countryDetectedPre, documentCountryValidationPre = validateDocumentCountry( documentoOCRPre)

    documentType, documentValidation = testingType([{'type':typeDetected, 'validation':documentTypeValidation},{'type':typeDetectedPre, 'validation':documentTypeValidationPre}])
    codeC, country, countryValidation = testingCountry([{'country': countryCode, 'countryDetected': countryDetected, 'validation': documentCountryValidation}, {'country': countryCodePre, 'countryDetected': countryDetectedPre, 'validation': documentCountryValidationPre}])

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

    documentBarcode = barcodeSide(documentType=tipoDocumento, documentSide=ladoDocumento)
    if(documentBarcode):
      detectedBarcodes = barcodeReader(imagenDocumento, efirmaId, ladoDocumento)
      resultsDict['barcode'] = detectedBarcodes
      checkSide['barcode'] = detectedBarcodes
    else:
      resultsDict['barcode'] = 'documento sin codigo de barras'

    mrzLetter, documentMRZ = MRZSide(documentType=tipoDocumento, documentSide=ladoDocumento)
    if(documentMRZ):
      mrz = extractMRZ(ocr=documentoOCRSencillo, mrzStartingLetter=mrzLetter)
      mrzPre =  extractMRZ(ocr=documentoOCRPre, mrzStartingLetter=mrzLetter)

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

    resultsDict['validSide'] = 'OK' if(validSide) else '!OK'

    return jsonify(resultsDict), 200