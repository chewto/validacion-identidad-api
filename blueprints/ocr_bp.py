
from flask import Blueprint, request, jsonify

from lector_codigo import barcodeReader, hasBarcode
from ocr import comparacionOCR, ocr, validacionOCR, validarLadoDocumento
from mrz import hasMRZ, extractMRZ
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

    verifyDocument = verifyFaces(selfieOrientada, documentoOrientado)

    #ocr

    validarLadoPre = validarLadoDocumento(tipoDocumento, ladoDocumento, documentoOrientado, preprocesado=True)
    validarLadoSencillo = validarLadoDocumento(tipoDocumento, ladoDocumento, documentoOrientado, preprocesado=False)
    totalValidacionLado = validarLadoPre + validarLadoSencillo

    ladoValido = False

    if(totalValidacionLado >=1):
      ladoValido = True

    documentoOCRSencillo = ocr(documentoOrientado, preprocesado=False)
    documentoOCRPre = ocr(documentoOrientado, preprocesado=True)

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
          'nombreOCR': nombreComparado,
          'apellidoOCR': apellidoComparado,
          'documentoOCR': documentoComparado
      },
      'porcentajesOCR': {
          'porcentajeNombreOCR': porcentajeNombreComparado,
          'porcentajeApellidoOCR': porcentajeApellidoComparado,
          'porcentajeDocumentoOCR': porcentajeDocumentoComparado
        },
      'rostro': verifyDocument,
      'ladoValido': ladoValido
    }

    documentBarcode = hasBarcode(documentType=tipoDocumento, documentSide=ladoDocumento)
    if(documentBarcode):
      detectedBarcodes = barcodeReader(imagenDocumento, efirmaId, ladoDocumento)
      results['codigoBarras'] = detectedBarcodes
    else:
      results['codigoBarras'] = 'documento sin codigo de barras'

    mrzLetter, documentMRZ = hasMRZ(documentType=tipoDocumento, documentSide=ladoDocumento)
    extractedMRZ = ''
    if(documentMRZ):
      mrz = extractMRZ(ocr=documentoOCRSencillo, mrzStartingLetter=mrzLetter)
      mrzPre =  extractMRZ(ocr=documentoOCRPre, mrzStartingLetter=mrzLetter)
      extractedMRZ += f"{mrz} {mrzPre} mrz extraido desde el {ladoDocumento}"
      results['mrz'] = extractedMRZ
    else:
      results['mrz'] = 'documento sin codigo mrz'

    return jsonify(results), 200


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

    validarLadoPre = validarLadoDocumento(tipoDocumento, ladoDocumento, documentoData, preprocesado=True)
    validarLadoSencillo = validarLadoDocumento(tipoDocumento, ladoDocumento, documentoData, preprocesado=False)
    totalValidacion = validarLadoPre + validarLadoSencillo

    ladoValido = False

    if(totalValidacion >= 1):
      ladoValido = True

    results = {
      'ladoValido': ladoValido
    }

    documentBarcode = hasBarcode(documentType=tipoDocumento, documentSide=ladoDocumento)
    if(documentBarcode):
      detectedBarcodes = barcodeReader(imagenDocumento, efirmaId, ladoDocumento)
      results['codigoBarras'] = detectedBarcodes
    else:
      results['codigoBarras'] = 'documento sin codigo de barras'

    mrzLetter, documentMRZ = hasMRZ(documentType=tipoDocumento, documentSide=ladoDocumento)
    extractedMRZ = ''
    if(documentMRZ):
      mrz = extractMRZ(ocr=documentoOCRSencillo, mrzStartingLetter=mrzLetter)
      mrzPre =  extractMRZ(ocr=documentoOCRPre, mrzStartingLetter=mrzLetter)
      extractedMRZ += f"{mrz} {mrzPre}"
      results['mrz'] = extractedMRZ
    else:
      results['mrz'] = 'documento sin codigo mrz'

    return jsonify(results), 200