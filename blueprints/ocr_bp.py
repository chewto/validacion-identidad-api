
from flask import Blueprint, request, jsonify

from lector_codigo import barcodeReader, barcodeSide
from ocr import comparacionOCR, ocr, validacionOCR, validarLadoDocumento, validateDocumentCountry, validateDocumentType
from mrz import MRZSide, extractMRZ
from reconocimiento import extractFaces, orientacionImagen, verifyFaces
from utilidades import readDataURL, textNormalize

ocr_bp = Blueprint('ocr', __name__, url_prefix='/ocr')

#rutas para el front
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

    _, _, verifyDocument = verifyFaces(selfieOrientada, documentoOrientado)

    documentoOCRSencillo = ocr(documentoOrientado, preprocesado=False)
    documentoOCRPre = ocr(documentoOrientado, preprocesado=True)

    validarLadoPre = validarLadoDocumento(tipoDocumento, ladoDocumento, documentoOrientado, preprocesado=True)
    validarLadoSencillo = validarLadoDocumento(tipoDocumento, ladoDocumento, documentoOrientado, preprocesado=False)
    totalValidacionLado = validarLadoPre + validarLadoSencillo

    typeDetected, documentTypeValidation = validateDocumentType(tipoDocumento, ladoDocumento, documentoOCRSencillo)
    countryCode, countryDetected, documentCountryValidation = validateDocumentCountry( documentoOCRSencillo)

    ladoValido = '!OK'

    if(totalValidacionLado >=1 and documentCountryValidation == 'OK' and documentCountryValidation == 'OK'):
      ladoValido = 'OK'

    nombreOCR, porcentajeNombre = validacionOCR(documentoOCRSencillo, nombre)
    apellidoOCR, porcentajeApellido = validacionOCR(documentoOCRSencillo, apellido)
    numeroDocumentoOCR, porcentajeDocumento = validacionOCR(documentoOCRSencillo, numeroDocumento)

    nombrePreOCR, porcentajeNombrePre = validacionOCR(documentoOCRPre, nombre)
    apellidoPreOCR, porcentajeApellidoPre = validacionOCR(documentoOCRPre, apellido)
    numeroDocumentoPreOCR, porcentajeDocumentoPre = validacionOCR(documentoOCRPre, numeroDocumento)

    nombreComparado, porcentajeNombreComparado = comparacionOCR(porcentajePre=porcentajeNombrePre, porcentajeSencillo=porcentajeNombre, ocrPre=nombrePreOCR, ocrSencillo=nombreOCR)
    apellidoComparado, porcentajeApellidoComparado = comparacionOCR(porcentajePre=porcentajeApellidoPre, porcentajeSencillo=porcentajeApellido, ocrPre=apellidoPreOCR, ocrSencillo=apellidoOCR)
    documentoComparado, porcentajeDocumentoComparado = comparacionOCR(porcentajePre=porcentajeDocumentoPre, porcentajeSencillo=porcentajeDocumento, ocrPre=numeroDocumentoPreOCR, ocrSencillo=numeroDocumentoOCR)

    results = {
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
      'face': verifyDocument,
      'validSide': ladoValido,
      'document':{
        'correspond': ladoValido, 
        'code': countryCode,
        'country': countryDetected,
        'countryCheck':documentCountryValidation,
        'type':typeDetected,
        'typeCheck':documentTypeValidation
      }
    }

    documentBarcode = barcodeSide(documentType=tipoDocumento, documentSide=ladoDocumento)
    if(documentBarcode):
      detectedBarcodes = barcodeReader(imagenDocumento, efirmaId, ladoDocumento)
      results['barcode'] = detectedBarcodes
    else:
      results['barcode'] = 'documento sin codigo de barras'

    mrzLetter, documentMRZ = MRZSide(documentType=tipoDocumento, documentSide=ladoDocumento)
    extractedMRZ = ''
    if(documentMRZ):
      mrz = extractMRZ(ocr=documentoOCRSencillo, mrzStartingLetter=mrzLetter)
      mrzPre =  extractMRZ(ocr=documentoOCRPre, mrzStartingLetter=mrzLetter)
      extractedMRZ += f"{mrz} {mrzPre} mrz extraido desde el {ladoDocumento}"
      results['mrz'] = extractedMRZ
    else:
      results['mrz'] = 'documento sin codigo mrz'

    return jsonify(results)


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

    ladoValido = '!OK'

    if(totalValidacion >= 1 and documentCountryValidation == 'OK' and documentCountryValidation == 'OK'):
      ladoValido = 'OK'

    results = {
      'validSide': ladoValido,
      'document':{
        'correspond': ladoValido,
        'code': countryCode,
        'country': countryDetected,
        'countryCheck':documentCountryValidation,
        'type':typeDetected,
        'typeCheck':documentTypeValidation
      }
    }

    documentBarcode = barcodeSide(documentType=tipoDocumento, documentSide=ladoDocumento)
    if(documentBarcode):
      detectedBarcodes = barcodeReader(imagenDocumento, efirmaId, ladoDocumento)
      results['barcode'] = detectedBarcodes
    else:
      results['barcode'] = 'documento sin codigo de barras'

    mrzLetter, documentMRZ = MRZSide(documentType=tipoDocumento, documentSide=ladoDocumento)
    extractedMRZ = ''
    if(documentMRZ):
      mrz = extractMRZ(ocr=documentoOCRSencillo, mrzStartingLetter=mrzLetter)
      mrzPre =  extractMRZ(ocr=documentoOCRPre, mrzStartingLetter=mrzLetter)
      extractedMRZ += f"{mrz} {mrzPre}"
      results['mrz'] = extractedMRZ
    else:
      results['mrz'] = 'documento sin codigo mrz'

    return jsonify(results), 200