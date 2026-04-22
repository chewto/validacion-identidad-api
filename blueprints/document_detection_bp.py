import json
from flask import Blueprint, request, jsonify
from ultralytics import YOLO
from utilities.check_result import results, testingCountry
import request.controlador_db as controlador_db
from expiry import expiryDateDetection, expiryDateOCR, hasExpiryDate
from utilities.formatter import _formatDocumentNumber
from lector_codigo import barcodeReader, barcodeSide, rotateBarcode
from mrz import MRZSide, comparisonMRZInfo, extractMRZ, mrzInfo
from ocr import validacionOCR, validateDocumentCountry, validateDocumentType
from reconocimiento import extractFaces, orientacionImagen, verifyFaces
from utilities.request_parser import _parse_request
from utilities.utilidades import fileCv2, imageToDataURL, readDataURL, textNormalize
from utilities.token_utils import token_required
import document_detection
import numpy as np

document_detection_bp = Blueprint('document', __name__, url_prefix="/document")

confidenceValue = 0.6


@document_detection_bp.route('/detection', methods=['POST', 'GET'])
@token_required
def documentDetection():

    testing = request.args.get("testing", "false").lower() == "true"

    documentType = request.args.get("documento")
    documentSide = request.args.get("lado")


    if (documentType == 'PASAPORTE'):
        document = 'PASAPORTE'

    if testing:
        image = request.files.get("image", None)
        country = request.form.get('country')
        imageData = fileCv2(image)
    else:
        data = request.get_json()
        country = data['country']
        imageData = readDataURL(data["image"])

    if (country == "HND"):
        if (documentSide == 'FRONTAL'):
            documentSide = 'ANVERSO'

    document = f'{documentType}_{documentSide}'.upper()

    if ('PASAPORTE' in documentType):
        return jsonify({
          "documentoValido": True,
        }), 200

    print(document)

    countryData = controlador_db.selectData(f'''
        SELECT yolo_labels, tipo_documento_validacion  FROM pki_validacion.pais as pais
        WHERE pais.codigo = "{country}"''', ())

    yoloLabels = countryData[0]
    # documents = countryData[1]
    yoloLabels = yoloLabels.upper()
    yoloLabels = yoloLabels.split(',')

    results = document_detection.detection(imageData, yoloLabels, country)

    crops = []
    labels = []
    isDocument = False

    for result in results:
        labels.append(result['label'])

        if 'CEDULA_DIGITAL' in result['label'] and documentType in 'CEDULA_CIUDADANIA':
            document = f'CEDULA_DIGITAL_{documentSide}'

        if document in result['label'] or 'FOTO' in result['label']:

            crop = {
              "left": int(result['crop'][1][0]),
              "right": int(result['crop'][1][1]),
              "top": int(result['crop'][0][0]),
              "bottom": int(result['crop'][0][1])
            }
            # Recortar la imagen y convertir a base64

            crops.append({
              "etiqueta": result['label'],
              "recorte": crop,
            })

    if document in labels:
        isDocument = True

    return jsonify({
        "documentoValido": isDocument,
        "etiquetas": labels,
        "recortes": crops
    }), 200

@document_detection_bp.route('/validate', methods=['POST', 'GET'])
@token_required
def validate():

  parsed = _parse_request(request)

  selfie = parsed['persona_data']
  documentImage = parsed['documento_data']
  efirmaId = parsed['efirma_id']
  name = parsed['nombre']
  surname = parsed['apellido']
  documentNumber = parsed['numero_documento']
  documentType = parsed['tipo_documento']
  documentSide = parsed['lado_documento']
  country = parsed["user_country"]
  tries = parsed["tries"]
  ocr = parsed["ocr"]

  print(country)


  confidenceThreshold = 0.65
  


  documentSide = request.args.get("side", None)


  resultsDict = {
    "barcode": None,
    # "confidence": 0.99,
    "document": {
        "code": "",
        "country": "",
        "countryCheck": "",
        "isExpired": None,
        "type": "",
        "typeCheck": ""
    },
    # "face": False,
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

  countryData = controlador_db.selectData(f'''
      SELECT barcode, mrz, yolo_labels FROM pki_validacion.pais as pais 
      WHERE pais.codigo = "{country}"''', ())
  
  
  barcodeData = json.loads(countryData[0])
  mrzData = json.loads(countryData[1])
  yoloLabels = countryData[2]
  yoloLabels = yoloLabels.split(',')

  face = False

  if(documentSide == 'anverso'):
    print('es un anverso')

    documentSelfie = document_detection.searchDocumentSelfie(yoloLabels=yoloLabels,img=documentImage, useCountry=country, documentType=documentType)
    _, confidence, _ = verifyFaces(selfie, documentSelfie)
    resultsDict['face'] = True if confidence <= confidenceThreshold else False
    face = True if confidence <= confidenceThreshold else False
    resultsDict['confidence'] = confidence

    extractFace = extractFaces(documentImage, anti_spoofing=False)

    if (extractFace):
      for face in extractFace:
        faceDetected = face.get('detected')
        resultsDict['faceDetected'] = faceDetected
        checkSide['faceDetected'] = faceDetected

    formatedDocumentNumber = _formatDocumentNumber(documentNumber)
    documentNumberExtracted = document_detection.getLabelContent(data=ocr, labelName='NUMERO_DOCUMENTO')

    name = textNormalize(name)
    nameExtracted = document_detection.getLabelContent(data=ocr, labelName='NOMBRES NOMBRESs')

    surname = textNormalize(surname)
    surnameExtracted = document_detection.getLabelContent(data=ocr, labelName='APELLIDOS APELLIDOSs')

    nameOcr, pctName = validacionOCR(nameExtracted, name, onlyNumbers=False)
    surnameOcr, pctSurname = validacionOCR(surnameExtracted, surname, onlyNumbers=False)
    IdNumberOcr, pctNumber = validacionOCR(documentNumberExtracted, formatedDocumentNumber, onlyNumbers=True)

    checkSide['percentName'] = True if pctName >= 50 else False
    checkSide['percentLastname'] = True if pctSurname >= 50 else False
    checkSide['percentID'] = True if pctNumber >= 50 else False

    resultsDict['ocr']['data']['ID'] = IdNumberOcr
    resultsDict['ocr']['data']['lastName'] =surnameOcr
    resultsDict['ocr']['data']['name'] =nameOcr

    resultsDict['ocr']['percentage']['ID'] = pctNumber
    resultsDict['ocr']['percentage']['lastName'] = pctSurname
    resultsDict['ocr']['percentage']['name'] = pctName


  countryHasModel, modelPath = document_detection.checkModel(country=country)

  if(countryHasModel):
    documentTypeDetected, documentValidation, countryCode, countryDetected, isCountry, croppedImage,documentLabel = document_detection.detectDocumentStand(
        img=documentImage, countryCode=country, side=documentSide, type=documentType, yoloLabels=yoloLabels, modelPath=modelPath
      )
    
    checkSide['countryValidation'] = isCountry
    checkSide['documentValidation'] = documentValidation

    resultsDict['document'] = {
        'type': documentTypeDetected,
        'typeCheck': documentValidation,
        'isExpired': None,
        "code": countryCode,
        "country": countryDetected,
        "countryCheck": isCountry,
    }
    
    resultsDict['image'] = croppedImage if croppedImage is not None else imageToDataURL(documentImage)


  hasbarcode,barcodeType,barcodetbr  = barcodeSide(documentType=documentType, documentSide=documentSide, barcodeData=barcodeData)
  barcodeIsOptional = barcodeData[documentType]["optional"]

  if hasbarcode:
      detectedBarcodes = barcodeReader(documentImage, efirmaId, documentSide, barcodeType, barcodetbr)
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

  mrzLetter, documentMRZ = MRZSide(documentType=documentType, documentSide=documentSide, mrzData=mrzData)

  mrzIsOptional = mrzData[documentType]['optional']

  if documentMRZ:
      mrz = extractMRZ(documentImage)

      if (mrz == "No se pudo detectar MRZ válido en la imagen." and not mrzIsOptional):
        messages.append('No se pudo detecar el código mrz del documento.')

      if 'valid_score' in mrz:
        if mrz['valid_score'] >= 51:
          extractName = mrzInfo(mrz=mrz['raw_text'].replace("\n", "") if 'raw_text' in mrz else '', searchTerm=name)
          extractLastname = mrzInfo(mrz=mrz['raw_text'].replace("\n", "") if 'raw_text' in mrz else '', searchTerm=surname)

          nameMRZ = comparisonMRZInfo([extractName], name, 'name')
          lastNameMRZ = comparisonMRZInfo([extractLastname], surname, 'surname')

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
  # else:
  #   print()

  resultsDict['messages'] = messages

  validSide, _, _ = results(49, 'AUTOMATICA', checkSide)

  if(documentSide == 'anverso'):
    resultsDict['validSide'] = validSide if face else False 
  else:
    resultsDict['validSide'] = validSide

  return resultsDict
