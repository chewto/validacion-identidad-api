
from flask import Blueprint, request, jsonify

from ocr import comparacionOCR, ocr, validacionOCR, validarLadoDocumento
from reconocimiento import extractFaces, orientacionImagen, verifyFaces
from utilidades import readDataURL, textNormalize

ocr_bp = Blueprint('ocr', __name__, url_prefix='/ocr')

@ocr_bp.route('/ocr-test', methods=['POST'])
def prueba():
  return 'test'


#rutas para el front
@ocr_bp.route('/anverso', methods=['POST'])
def verificarAnverso():

    documento = request.get_json()

    imagenPersona = documento['imagenPersona']

    imagenDocumento = documento['imagen']

    ladoDocumento = documento['ladoDocumento']

    tipoDocumento = documento['tipoDocumento']

    documentoData = readDataURL(imagenDocumento)

    personaData = readDataURL(imagenPersona)

    nombre = documento['nombre']

    nombre = textNormalize(nombre)

    apellido = documento['apellido']

    apellido = textNormalize(apellido)

    numeroDocumento = documento['documento']

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

    documentoOCRSencillo = ocr(documentoOrientado, 'sencillo')

    documentoOCRPre = ocr(documentoOrientado, 'preprocesado')

    nombreOCR, porcentajeNombre = validacionOCR(documentoOCRSencillo, nombre)
    apellidoOCR, porcentajeApellido = validacionOCR(documentoOCRSencillo, apellido)
    numeroDocumentoOCR, porcentajeDocumento = validacionOCR(documentoOCRSencillo, numeroDocumento)

    nombrePreOCR, porcentajeNombrePre = validacionOCR(documentoOCRPre, nombre)
    apellidoPreOCR, porcentajeApellidoPre = validacionOCR(documentoOCRPre, apellido)
    numeroDocumentoPreOCR, porcentajeDocumentoPre = validacionOCR(documentoOCRPre, numeroDocumento)

    nombreComparado, porcentajeNombreComparado = comparacionOCR(porcentajePre=porcentajeNombrePre, porcentajeSencillo=porcentajeNombre, ocrPre=nombrePreOCR, ocrSencillo=nombreOCR)
    apellidoComparado, porcentajeApellidoComparado = comparacionOCR(porcentajePre=porcentajeApellidoPre, porcentajeSencillo=porcentajeApellido, ocrPre=apellidoPreOCR, ocrSencillo=apellidoOCR)
    documentoComparado, porcentajeDocumentoComparado = comparacionOCR(porcentajePre=porcentajeDocumentoPre, porcentajeSencillo=porcentajeDocumento, ocrPre=numeroDocumentoPreOCR, ocrSencillo=numeroDocumentoOCR)

    # coincidencia = False

    if(len(carasImagenPersona) >= 1 and len(carasImagenDocumento) >= 1):
      coincidencia = True

    return jsonify({
      'ocr': {
          'nombreOCR': nombreComparado,
          'apellidoOCR': apellidoComparado,
          'documentoOCR': documentoComparado
      },
      'porcentajes': {
          'porcentajeNombreOCR': porcentajeNombreComparado,
          'porcentajeApellidoOCR': porcentajeApellidoComparado,
          'porcentajeDocumentoOCR': porcentajeDocumentoComparado
        },
      'rostro': verifyDocument,
      'ladoValido': ladoValido
    })


#rutas para el front
@ocr_bp.route('/reverso', methods=['POST'])
def verificarReverso():

  

    dataOCR = {
      'numeroDocumentoOCR': 'no encontrado',
      'nombreOCR': 'no encontrado',
      'apellidoOCR': 'no encontrado'
    }
    
    documento = request.get_json()

    imagenDocumento = documento['imagen']

    ladoDocumento = documento['ladoDocumento']

    tipoDocumento = documento['tipoDocumento']

    documentoData = readDataURL(imagenDocumento)
    
    nombre = documento['nombre']

    nombre = textNormalize(nombre)

    apellido = documento['apellido']

    apellido = textNormalize(apellido)

    numeroDocumento = documento['documento']

    # documentoOCRSencillo = ocr(documentoData, 'sencillo')

    # documentoOCRPre = ocr(documentoData, 'preprocesado')

    # busquedaSencillo = busquedaData(documentoOCRSencillo, nombre, apellido, numeroDocumento)
    # busquedaPre = busquedaData(documentoOCRPre, nombre, apellido, numeroDocumento)


    # print(busquedaSencillo, busquedaPre)
    validarLadoPre = validarLadoDocumento(tipoDocumento, ladoDocumento, documentoData, preprocesado=True)
    validarLadoSencillo = validarLadoDocumento(tipoDocumento, ladoDocumento, documentoData, preprocesado=False)

    totalValidacion = validarLadoPre + validarLadoSencillo

    ladoValido = False

    if(totalValidacion >= 1):
      ladoValido = True

    return jsonify({
        "codigoBarra":{
          'reconocido': 'false',
          'nombre':'false',
          'apellido':'false',
          'documento':'false'
        },
        'ladoValido': ladoValido
      })

    codigoBarrasData = lector_codigo.lectorCodigoBarras(imagenDocumento, tipoDocumento)

    if(codigoBarrasData is False):
      return jsonify({
        "codigoBarra":{
          'reconocido': 'false',
          'nombre': 'false',
          'apellido':'false',
          'documento':'false'
        },
        "ladoValido": validarLado
      })

    validacionNombre = lector_codigo.validarDataCodigo(nombre, f"{codigoBarrasData['primerNombre']}" + ' ' + f"{codigoBarrasData['segundoNombre']}")
    validacionApellido = lector_codigo.validarDataCodigo(apellido, f"{codigoBarrasData['primerApellido']}" + ' ' + f"{codigoBarrasData['segundoApellido']}")
    validacionDocumento = lector_codigo.validarDataCodigo(numeroDocumento, f"{codigoBarrasData['numeroDocumento']}")


    if(tipoDocumento == 'Cédula de extranjería'):
      return jsonify({
        "codigoBarra":{
          'reconocido': 'true',
          'nombre':'true',
          'apellido':'true',
          'documento':'true'
        },
        'ladoValido': validarLado
      })
    if(tipoDocumento == 'Cédula de ciudadanía'):
      return jsonify({
        "codigoBarra":{
          'reconocido': 'true',
          'nombre':validacionNombre,
          'apellido':validacionApellido,
          'documento':validacionDocumento
        },
        'ladoValido': validarLado
      })
