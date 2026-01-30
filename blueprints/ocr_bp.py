
import json
from flask import Blueprint, request, jsonify
from document_detection import detectDocument, searchDocumentSelfie, validateDocument
from utilities.formatter import _formatDocumentNumber
from lector_codigo import barcodeReader, barcodeSide, rotateBarcode, extractCountry
from utilities.logs import addLog, checkLogsFile
from utilities.name_search import searchId, searchName
from ocr import comparacionOCR, validacionOCR, validarLadoDocumento, validateDocumentCountry, validateDocumentType, preprocessing
from mrz import MRZSide, extractMRZ, mrzInfo, comparisonMRZInfo, validateMrz
from expiry import expiryDateOCR, hasExpiryDate
from reconocimiento import extractFaces, orientacionImagen, verifyFaces
from utilities.request_parser import _parse_request
from utilities.utilidades import readDataURL, textNormalize, imageToDataURL, fileCv2, orientation, rotateImage
from utilities.check_result import testingCountry, testingType, results
import time
import request.controlador_db as controlador_db
import cv2

ocr_bp = Blueprint('ocr', __name__, url_prefix='/ocr')

# confidenceThreshold = 0.6
@ocr_bp.route('/anverso', methods=['POST'])
def verificarAnverso():

    parsed = _parse_request(request)
    
    efirmaId = parsed['efirma_id']
    personaData = parsed['persona_data']
    documentoData = parsed['documento_data']
    ladoDocumento = parsed['lado_documento']
    tipoDocumento = parsed['tipo_documento']
    nombre = parsed['nombre'] or ''
    apellido = parsed['apellido'] or ''
    numeroDocumento = parsed['numero_documento']
    userCountry = parsed['user_country']
    tries = parsed['tries']
    ocr =  parsed['ocr']
    textAngle = parsed['text_angle']

    confidenceThreshold = 0.70 if tries >= 1 else 0.70

    # resolution = 600 if tries <=1 else 1080
    resolution = 1080

    getInitTime = time.time()
    countryData = controlador_db.selectData(f'''
      SELECT mrz,barcode,ocr,yolo_labels FROM pki_validacion.pais as pais 
      WHERE pais.codigo = "{userCountry}"''', ())
    getEndTime = time.time()
    getTime = getEndTime - getInitTime

    print(getTime)

    mrzData = json.loads(countryData[0])
    barcodeData = json.loads(countryData[1])
    ocrData = json.loads(countryData[2])
    yoloLabels = countryData[3]
    yoloLabels = yoloLabels.split(',')

    # resultsDict = {}

    resultsDict = {
      "barcode": None,
      "confidence": 0.99,
      "document": {
          "code": "",
          "country": "",
          "countryCheck": "",
          "isExpired": None,
          "type": "",
          "typeCheck": ""
      },
      "face": False,
      "documentFace": None,
      "image": "",
      "mrz": {
          "code": None,
          "data": {
              "lastName": "",
              "name": ""
          },
          "percentages": {
              "lastName": 0,
              "name": 0
          }
      },
      "ocr": {
          "data": {
              "ID": "",
              "lastName": "",
              "name": ""
          },
          "percentage": {
              "ID": 0,
              "lastName": 0,
              "name": 0
          }
      },
    }
    messages = []
    checkSide = {}
    documentoOrientado = rotateImage(documentoData, textAngle)

    detectFaceInitTime = time.time()
    documentSelfie = searchDocumentSelfie(
      yoloLabels=yoloLabels,
      img=documentoData,
      useCountry=userCountry,
      documentType=tipoDocumento
    )
    detectFaceEndTime = time.time()
    detectFaceTime = detectFaceEndTime - detectFaceInitTime
    getFacesInit = time.time()
    extractFace = extractFaces(documentoOrientado, anti_spoofing=False)

    getFacesEnd = time.time()
    getFaces = getFacesEnd - getFacesInit

    if (extractFace):
        resultsDict['documentFace'] = extractFace
        for face in extractFace:
            faceDetected = face.get('detected')
            resultsDict['faceDetected'] = faceDetected
            checkSide['faceDetected'] = faceDetected
            if not faceDetected:
                messages.append("No se ha detectado el rostro en el documento.")

    # return jsonify(extractFace)

    selfieOrientada = personaData

    preprocessedDocument = preprocessing(
      documentoOrientado,
      resolution,
      filters='sharp'
    )

    compareFacesInit = time.time()
    _, confidence, _ = verifyFaces(selfieOrientada, documentSelfie)
    compareFacesEnd = time.time()

    resultsDict['face'] = True if confidence <= confidenceThreshold else False
    resultsDict['confidence'] = confidence
    checkSide['face'] = True if confidence <= confidenceThreshold else False
    if (confidence >= confidenceThreshold):
        messages.append('Los rostros no coincidén.')

    
    detectInit = time.time()
    document_section, doc_check, doc_messages, croppedImage = validateDocument(
        documentoOrientado,
        ocr,
        tipoDocumento,
        ladoDocumento,
        userCountry,
        ocrData,
        yoloLabels
    )

    detectEnd = time.time()

    detectTime = detectEnd - detectInit

    if (croppedImage is not None):
        resultsDict['image'] = croppedImage
    else:
        resultsDict['image'] = imageToDataURL(preprocessedDocument)

    # Fusionar resultados de validación de documento
    checkSide.update(doc_check)
    messages.extend(doc_messages)
    resultsDict['document'] = document_section

    numeroDocumento = _formatDocumentNumber(numeroDocumento)

    nombre = textNormalize(nombre)
    apellido = textNormalize(apellido)

    nombreOcr, pctNombre = validacionOCR(
      ocr,
      nombre,
      onlyNumbers=False
    )
    apellidoOcr, pctApellido = validacionOCR(ocr, apellido, onlyNumbers=False)
    numeroOcr, pctNumero = validacionOCR(ocr, numeroDocumento, onlyNumbers=True)

    checkSide['percentName'] = True if pctNombre >= 50 else False
    checkSide['percentLastname'] = True if pctApellido >= 50 else False
    checkSide['percentID'] = True if pctNumero >= 50 else False

    if pctNombre <= 50:
        messages.append('El nombre no se ha encontrado en el documento.')
    if pctApellido <= 50:
        messages.append('El apellido no se ha encontrado en el documento.')
    if pctNumero <= 50:
        messages.append(
          'El número del identificación no se ha encontrado en el documento.'
        )

    resultsDict['ocr'] = {
        'data': {
          'name': nombreOcr,
          'lastName': apellidoOcr,
          'ID': numeroOcr
        },
        'percentage': {
          'name': pctNombre,
          'lastName': pctApellido,
          'ID': pctNumero
        }
    }

    hasbarcode, barcodeType, barcodetbr = barcodeSide(
      documentType=tipoDocumento,
      documentSide=ladoDocumento,
      barcodeData=barcodeData
    )
    barcodeIsOptional = barcodeData[tipoDocumento]["optional"]

    barcodeTime = None

    if hasbarcode:
        barcodeInit = time.time()
        detectedBarcodes = barcodeReader(
          preprocessedDocument,
          efirmaId,
          ladoDocumento,
          barcodeType,
          barcodetbr
        )

        barcodeEnd = time.time()
        barcodeTime = barcodeEnd - barcodeInit
        detectedBarcodes = True if (len(detectedBarcodes) >= 1) else False

        if barcodeIsOptional:
            if detectedBarcodes:
                resultsDict['barcode'] = detectedBarcodes
                checkSide['barcode'] = detectedBarcodes
        else:
            resultsDict['barcode'] = detectedBarcodes
            checkSide['barcode'] = detectedBarcodes
            if not detectedBarcodes:
                messages.append(
                  'No se pudo detectar el código de barras del documento.'
                )

    mrzLetter, documentMRZ = MRZSide(
        documentType=tipoDocumento,
        documentSide=ladoDocumento,
        mrzData=mrzData
    )

    mrzIsOptional = mrzData[tipoDocumento]['optional']

    mrzTime = None

    if documentMRZ:

        mrzInit = time.time()
        mrz = extractMRZ(preprocessedDocument)
        mrzEnd = time.time()

        mrzTime = mrzEnd - mrzInit

        if (mrz == "No se pudo detectar MRZ válido en la imagen." and not mrzIsOptional):
            messages.append('No se pudo detecar el código mrz del documento.')

        if 'valid_score' in mrz:
            if mrz['valid_score'] >= 51:
                if (userCountry == 'HND' and tipoDocumento =='PASAPORTE' and checkSide['documentValidation'] == False):
                    if (mrz['type'] == 'P<'):
                        checkSide['documentValidation'] = True
                        resultsDict['document']['type'] = 'Pasaporte'
                        resultsDict['document']['typeCheck'] = True
                    else:
                      messages.append('El tipo de documento no coincide con el seleccionado.')

                    if (mrz['country'] == 'HND' and checkSide['countryValidation'] == False):
                        checkSide['countryValidation'] = True
                        resultsDict['document']["code"] = 'HND'
                        resultsDict['document']['country'] = 'HONDURAS'
                        resultsDict['document']['countryCheck'] = True
                    else:
                      messages.append('El pais del documento no se encontro en el documento.') 

                extractName = mrzInfo(
                  mrz=mrz['raw_text'].replace("\n", "") if 'raw_text' in mrz else '',
                  searchTerm=nombre
                )
                extractLastname = mrzInfo(
                  mrz=mrz['raw_text'].replace("\n", "") if 'raw_text' in mrz else '',
                  searchTerm=apellido
                )

                nameMRZ = comparisonMRZInfo([extractName], nombre, 'name')
                lastNameMRZ = comparisonMRZInfo([extractLastname], apellido, 'surname')

                #Si MRZ no es opcional, siempre se agrega.
                #Si es opcional, solo si se detecta.
                if (not mrzIsOptional) or (mrzIsOptional and 'raw_text' in mrz):
                    resultsDict['mrz'] = {
                      'code': mrz['raw_text'] if 'raw_text' in mrz else 'No se pudo detectar MRZ válido en la imagen.',
                      'data': {
                        'name': nameMRZ['data'] if len(nameMRZ['data']) >= 1 else '',
                        'lastName': lastNameMRZ['data'] if len(lastNameMRZ['data']) >= 1 else ''
                      },
                      'percentages': {
                        'name': nameMRZ['percent'],
                        'lastName': lastNameMRZ['percent']
                      }
                    }

                # Si MRZ no es opcional, siempre se agregan los checks y mensajes
                if not mrzIsOptional:
                    checkSide['nameMrz'] = True if nameMRZ['percent'] >= 51 else False
                    checkSide['lastNameMrz'] = True if lastNameMRZ['percent'] >= 51 else False
                    if nameMRZ['percent'] <= 50 and 'raw_text' in mrz:
                        messages.append('No se encontró el nombre en el codigo mrz.')
                    if lastNameMRZ['percent'] <= 50 and 'raw_text' in mrz:
                        messages.append('No se encontró el apellido en el codigo mrz.')
                # Si MRZ es opcional, solo se agregan los checks si cumplen el porcentaje, no se agregan mensajes
                elif mrzIsOptional and 'raw_text' in mrz:
                    if nameMRZ['percent'] >= 51:
                        checkSide['nameMrz'] = True
                    if lastNameMRZ['percent'] >= 51:
                        checkSide['lastNameMrz'] = True
        else:
            # Si MRZ no es opcional, siempre se agrega aunque el score sea bajo
            if not mrzIsOptional:
                resultsDict['mrz'] = {
                  'code': "No se pudo detectar MRZ válido en la imagen.",
                  'data': {
                    'name': '',
                    'lastName': ''
                  },
                  'percentages': {
                    'name': 0,
                    'lastName': 0
                  }
                }

                messages.append(
                    'No se pudo detecar el código mrz del documento.'
                )
                checkSide['nameMrz'] = False
                checkSide['lastNameMrz'] = False

    valid_side, _, _ = results(49, 'AUTOMATICA', checkSide)

    resultsDict['messages'] = messages

    logsPath = checkLogsFile()
    logString = f"anverso; data-server: {getTime}; extraccion-rostros: {detectFaceTime}, busqueda-rostros: {getFaces}; deteccion-documento: {detectTime}; mrz: {mrzTime}; codigo-barra: {barcodeTime};\n"
    addLog(logsPath, logString)

    if confidence <= confidenceThreshold and valid_side and faceDetected:
        resultsDict['validSide'] = True if (valid_side and len(messages) <= 0) else False
        return jsonify(resultsDict)

    resultsDict['validSide'] = False
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
        ocr = request.form.get('ocr').split(',')
        textAngle = request.form.get('textAngle')
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
        ocr = reqBody.get('ocr')
        textAngle = reqBody.get('textAngle')


    # resolution = 600 if tries <=1 else 1080

    resolution = 1080

    imagenDocumento = rotateImage(imagenDocumento, textAngle)

    preprocessedDocument = preprocessing(imagenDocumento, resolution, filters='sharp')

    nombre = textNormalize(nombre)
    apellido = textNormalize(apellido)

    getInitTime = time.time()
    countryData = controlador_db.selectData(f'''
      SELECT mrz,barcode,ocr,yolo_labels FROM pki_validacion.pais as pais 
      WHERE pais.codigo = "{userCountry}"''', ())
    getEndTime = time.time()
    getTime = getEndTime - getInitTime

    mrzData = json.loads(countryData[0])
    barcodeData = json.loads(countryData[1])
    ocrData = json.loads(countryData[2])
    yoloLabels = countryData[3]
    yoloLabels = yoloLabels.split(',')

    documentoData = None

    resultsDict = {
    "barcode": None,
    "document": {
        "code": "",
        "country": "",
        "countryCheck": "",
        "isExpired": None,
        "type": "",
        "typeCheck": ""
    },
    "image": "",
    "mrz": {
        "code": None,
        "data": {
            "lastName": "",
            "name": ""
        },
        "percentages": {
            "lastName": 0,
            "name": 0
        }
    }
  }

    checkSide = {

    }

    ocr = ocr

    detectInit = time.time()
    document_section, doc_check, doc_messages, croppedImage = validateDocument(
        imagenDocumento,
        ocr,
        tipoDocumento,
        ladoDocumento,
        userCountry,
        ocrData,
        yoloLabels
    )
    detectEnd = time.time()

    detectTime = detectEnd - detectInit

    if(croppedImage is not None):
      resultsDict['image'] = croppedImage
    else:
      resultsDict['image'] = imageToDataURL(imagenDocumento)
    

    # Fusionar resultados de validación de documento
    checkSide.update(doc_check)
    messages.extend(doc_messages)
    resultsDict['document'] = document_section


    hasbarcode,barcodeType,barcodetbr  = barcodeSide(documentType=tipoDocumento, documentSide=ladoDocumento, barcodeData=barcodeData)
    barcodeIsOptional = barcodeData[tipoDocumento]["optional"]

    if hasbarcode:
      barcodeInit = time.time()
      detectedBarcodes = barcodeReader(preprocessedDocument, efirmaId, ladoDocumento, barcodeType, barcodetbr)
      barcodeEnd = time.time()
      barcodeTime = barcodeEnd - barcodeInit
      
      detectedBarcodes = True if (len(detectedBarcodes) >= 1) else False

      if barcodeIsOptional:
        if detectedBarcodes:
          resultsDict['barcode'] = detectedBarcodes
          checkSide['barcode'] = detectedBarcodes
      else:
        resultsDict['barcode'] = detectedBarcodes
        checkSide['barcode'] = detectedBarcodes
        if not detectedBarcodes:
          messages.append('No se pudo detectar el código de barras del documento.')


    mrzLetter, documentMRZ = MRZSide(documentType=tipoDocumento, documentSide=ladoDocumento, mrzData=mrzData)

    mrzIsOptional = mrzData[tipoDocumento]['optional']

    if documentMRZ:
      mrzInit = time.time()
      mrz = extractMRZ(preprocessedDocument)
      mrzEnd = time.time()

      mrzTime = mrzEnd - mrzInit


      if (mrz == "No se pudo detectar MRZ válido en la imagen." and not mrzIsOptional):
        messages.append('No se pudo detecar el código mrz del documento.')

      if 'valid_score' in mrz:
        if mrz['valid_score'] >= 51:
          extractName = mrzInfo(mrz=mrz['raw_text'].replace("\n", "") if 'raw_text' in mrz else '', searchTerm=nombre)
          extractLastname = mrzInfo(mrz=mrz['raw_text'].replace("\n", "") if 'raw_text' in mrz else '', searchTerm=apellido)

          nameMRZ = comparisonMRZInfo([extractName], nombre, 'name')
          lastNameMRZ = comparisonMRZInfo([extractLastname], apellido, 'surname')

          # Si MRZ no es opcional, siempre se agrega. Si es opcional, solo si se detecta.
          if (not mrzIsOptional) or (mrzIsOptional and 'raw_text' in mrz):
            resultsDict['mrz'] = {
              'code': mrz['raw_text'] if 'raw_text' in mrz else 'No se pudo detectar MRZ válido en la imagen.',
              'data': {
                'name': nameMRZ['data'] if len(nameMRZ['data']) >= 1 else '',
                'lastName': lastNameMRZ['data'] if len(lastNameMRZ['data']) >= 1 else ''
              },
              'percentages': {
                'name': nameMRZ['percent'],
                'lastName': lastNameMRZ['percent']
              }
            }

          # Si MRZ no es opcional, siempre se agregan los checks y mensajes
          if not mrzIsOptional:
            checkSide['nameMrz'] = True if nameMRZ['percent'] >= 51 else False
            checkSide['lastNameMrz'] = True if lastNameMRZ['percent'] >= 51 else False
            if nameMRZ['percent'] <= 50 and 'raw_text' in mrz:
              messages.append('No se encontró el nombre en el codigo mrz.')
            if lastNameMRZ['percent'] <= 50 and 'raw_text' in mrz:
              messages.append('No se encontró el apellido en el codigo mrz.')
          # Si MRZ es opcional, solo se agregan los checks si cumplen el porcentaje, no se agregan mensajes
          elif mrzIsOptional and 'raw_text' in mrz:
            if nameMRZ['percent'] >= 51:
              checkSide['nameMrz'] = True
            if lastNameMRZ['percent'] >= 51:
              checkSide['lastNameMrz'] = True
        else:
          # Si MRZ no es opcional, siempre se agrega aunque el score sea bajo
          if not mrzIsOptional:
            resultsDict['mrz'] = {
              'code': "No se pudo detectar MRZ válido en la imagen.",
              'data': {
                'name': '',
                'lastName': ''
              },
              'percentages': {
                'name': 0,
                'lastName': 0
              }
            }

            messages.append('No se pudo detecar el código mrz del documento.')
            checkSide['nameMrz'] = False
            checkSide['lastNameMrz'] = False


    validSide, _, _percent = results(51, 'AUTOMATICA', checkSide)

    logsPath = checkLogsFile()
    logString = f"reverso; data-server: {getTime};  deteccion-documento: {detectTime}; mrz: {mrzTime}; codigo-barra: {barcodeTime};\n"
    addLog(logsPath, logString)


    resultsDict['messages'] = messages

    resultsDict['validSide'] = validSide

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
    image = request.files.get('image')
    documentType = request.form.get('documentType')
    documentSide = request.form.get('documentSide')
    imageData = fileCv2(image)



    barcodes = barcodeReader(imageData, id, documentSide, "pdf417", "")

    return jsonify({
      # 'image': image,
      'barcodeData': barcodes
    })
