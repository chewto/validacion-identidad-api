
import json
from flask import Blueprint, request, jsonify
from document_detection import detectDocument, validateDocument
from formatter import _formatDocumentNumber
from lector_codigo import barcodeReader, barcodeSide, rotateBarcode, extractCountry
from name_search import searchId, searchName
from ocr import comparacionOCR, validacionOCR, validarLadoDocumento, validateDocumentCountry, validateDocumentType, preprocessing
from mrz import MRZSide, extractMRZ, mrzInfo, comparisonMRZInfo, validateMrz
from expiry import expiryDateOCR, hasExpiryDate
from reconocimiento import orientacionImagen, verifyFaces
from request_parser import _parse_request
from utilidades import readDataURL, textNormalize, imageToDataURL, fileCv2, orientation, rotateImage
from check_result import testingCountry, testingType, results
import time
import controlador_db
import cv2

ocr_bp = Blueprint('ocr', __name__, url_prefix='/ocr')

confidenceThreshold = 0.6
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


    # resolution = 600 if tries <=1 else 1080
    resolution = 1080

    countryData = controlador_db.selectData(f'''
      SELECT * FROM pki_validacion.pais as pais 
      WHERE pais.codigo = "{userCountry}"''', ())

    mrzData = json.loads(countryData[3])
    barcodeData = json.loads(countryData[4])
    ocrData = json.loads(countryData[5])

    resultsDict = {}
    messages = []
    checkSide = {}

    selfieOrientada = personaData

    documentoOrientado = rotateImage(documentoData, textAngle)

    preprocessedDocument = preprocessing(documentoOrientado, resolution, filters='sharp')

    _, confidence, _ = verifyFaces(selfieOrientada, documentoOrientado)

    checkSide['face'] = 'OK' if confidence <= confidenceThreshold else '!OK'
    if(confidence >= confidenceThreshold):
      messages.append('Los rostros no coincidén.')

    messages = []

    document_section, doc_check, doc_messages = validateDocument(
        documentoData,
        ocr,
        tipoDocumento,
        ladoDocumento,
        userCountry,
        ocrData
    )

    # Fusionar resultados de validación de documento
    checkSide.update(doc_check)
    messages.extend(doc_messages)
    resultsDict['document'] = document_section

    numeroDocumento = _formatDocumentNumber(numeroDocumento)

    nombre = textNormalize(nombre)
    apellido = textNormalize(apellido)

    nombreOcr, pctNombre = validacionOCR(ocr, nombre, onlyNumbers=False)
    apellidoOcr, pctApellido = validacionOCR(ocr, apellido, onlyNumbers=False)
    numeroOcr, pctNumero = validacionOCR(ocr, numeroDocumento, onlyNumbers=True)

    checkSide['percentName'] = 'OK' if pctNombre >= 50 else '!OK'
    checkSide['percentLastname'] = 'OK' if pctApellido >= 50 else '!OK'
    checkSide['percentID'] = 'OK' if pctNumero >= 50 else '!OK'

    if pctNombre <= 50:
        messages.append('El nombre no se ha encontrado en el documento.')
    if pctApellido <= 50:
        messages.append('El apellido no se ha encontrado en el documento.')
    if pctNumero <= 50:
        messages.append('El número del identificación no se ha encontrado en el documento.')

  
    image = imageToDataURL(preprocessedDocument)

    resultsDict['image'] = image
    resultsDict['ocr'] = {
        'data':{
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

    resultsDict['face'] = True if confidence <= confidenceThreshold else False
    resultsDict['confidence'] = confidence

    # resultsDict = {
    #   'image': image,
    #   'ocr': {
    #     'data':{
    #       'name': nombrePreOCR,
    #       'lastName': apellidoPreOCR,
    #       'ID': numeroDocumentoPreOCR
    #     },
    #     'percentage': {
    #       'name': porcentajeNombrePre,
    #       'lastName': porcentajeApellidoPre,
    #       'ID': porcentajeDocumentoPre
    #     }
    #   },
    #   'face': True if confidence <= confidenceValue else False,
    #   'confidence': confidence,
    #   'document':{
    #     'type':documentType,
    #     'typeCheck':documentValidation,
    #     'isExpired': isExpired
    #   }
    # }

    hasbarcode,barcodeType,barcodetbr  = barcodeSide(documentType=tipoDocumento, documentSide=ladoDocumento, barcodeData=barcodeData)
    if(hasbarcode):
      detectedBarcodes = barcodeReader(preprocessedDocument, efirmaId, ladoDocumento, barcodeType, barcodetbr)
      detectedBarcodes = 'OK' if(len(detectedBarcodes) >= 1) else '!OK'
      resultsDict['barcode'] = detectedBarcodes
      checkSide['barcode'] = detectedBarcodes
      if(detectedBarcodes != 'OK'):
        messages.append('No se pudo detectar el código de barras del documento.')
    else:
      resultsDict['barcode'] = None

    mrz_section, mrz_checks, mrz_messages, mrz_country_update = validateMrz(
        documentoData, tipoDocumento, ladoDocumento, nombre, apellido, userCountry, mrzData
    )

    # Si MRZ devolvió una actualización de país -> aplicarla
    if mrz_country_update:
        resultsDict['document'].update(mrz_country_update)
        checkSide.update({'countryValidation': mrz_country_update.get('countryCheck')})
        if mrz_country_update.get('countryCheck') != 'OK':
            messages.append('El país del documento no coincide.')

    # Añadir mrz al resultado
    resultsDict['mrz'] = mrz_section
    checkSide.update(mrz_checks)
    messages.extend(mrz_messages)

    # Si no hay MRZ y no se rellenó country anteriormente -> validar por OCR
    if not mrz_section or mrz_section.get('code', '') == '':
        country_code_pre, country_detected_pre, doc_country_validation_pre = validateDocumentCountry(ocr, country=userCountry)
        code_c, country_name, country_validation = testingCountry([
            {'country': country_code_pre, 'countryDetected': country_detected_pre, 'validation': doc_country_validation_pre}
        ])

        if country_validation != 'OK':
            messages.append('El país del documento no coincide.')

        if userCountry != 'COL':
            resultsDict['document'].update({'code': code_c, 'country': country_name, 'countryCheck': country_validation})
            checkSide['countryValidation'] = country_validation

    # Validación final del lado
    valid_side, _, _ = results(49, 'AUTOMATICA', checkSide)

    resultsDict['messages'] = messages

    if confidence <= confidenceThreshold and valid_side:
        resultsDict['validSide'] = 'OK' if (valid_side and len(messages) <= 0) else '!OK'
        return jsonify(resultsDict)

    resultsDict['validSide'] = '!OK'
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

    countryData = controlador_db.selectData(f'''
      SELECT * FROM pki_validacion.pais as pais 
    WHERE pais.codigo = "{userCountry}"''', ())

    mrzData = json.loads(countryData[3])
    barcodeData = json.loads(countryData[4])
    ocrData = json.loads(countryData[5])

    documentoData = None

    resultsDict = {
      'document': {},
      'barcode': None
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

      rotatedImage = imagenDocumento if detectedBarcodes == '!OK' else rotateBarcode(preprocessedDocument, barcodes=barcodes)

      if(tipoDocumento == 'CEDULA DE EXTRANJERIA'):
        resultsDict['barcode'] = detectedBarcodes if (detectedBarcodes == 'OK') else None
      # else:
      #   resultsDict['barcode'] = detectedBarcodes

      resultsDict['image'] = imageToDataURL(rotatedImage)

      if(tipoDocumento != 'CEDULA DE CIUDADANIA'):
        if(detectedBarcodes == 'OK'):
          checkSide['barcode'] = detectedBarcodes

      if(tipoDocumento == 'CEDULA DE CIUDADANIA'):
        temp['barcode']= detectedBarcodes

        if(detectedBarcodes == 'OK' and len(barcodes) >= 1):

          extractedCountry = extractCountry(barcodes)

          if len(extractedCountry) >= 1:

            countryCodePre, countryDetectedPre, documentCountryValidationPre = validateDocumentCountry( [extractedCountry[0]], country=userCountry)
            codeC, country, countryValidation = testingCountry([{'country': countryCodePre, 'countryDetected': countryDetectedPre, 'validation': documentCountryValidationPre}])

            if(countryValidation != 'OK'):
              messages.append('El país del documento no coincide.')

            resultsDict['document']['code'] = codeC
            resultsDict['document']['country'] = country
            resultsDict['document']['countryCheck'] = countryValidation

            checkSide['countryValidation'] = countryValidation
        # else:
        #   countryCodePre, countryDetectedPre, documentCountryValidationPre = validateDocumentCountry( ocr, country=userCountry)
        #   codeC, country, countryValidation = testingCountry([{'country': countryCodePre, 'countryDetected': countryDetectedPre, 'validation': documentCountryValidationPre}])

        #   if(countryValidation != 'OK'):
        #     messages.append('El país del documento no coincide.')

        #   resultsDict['document'] = {
        #     'code': codeC,
        #     'country': country,
        #     'countryCheck':countryValidation
        #   }
        #   checkSide['countryValidation'] = countryValidation


      if(detectedBarcodes == '!OK' and tipoDocumento != 'CEDULA DE CIUDADANIA'):
        messages.append('No se pudo detectar el código de barras del documento.')
    else:
      rotatedImage = imagenDocumento
      resultsDict['image'] = imageToDataURL(rotatedImage)
      resultsDict['barcode'] = None

    # rotatedImage = orientation(documentoData)

    timeOcrInit = time.time()

    ocr = ocr

    # typeDetected, documentTypeValidation = validateDocumentType(tipoDocumento, ladoDocumento, documentoOCRSencillo)
    # countryCode, countryDetected, documentCountryValidation = validateDocumentCountry( documentoOCRSencillo)


    # print(totalValidacion)

    # checkSide['validation'] = 'OK'if totalValidacion >= 2 else '!OK'

    if userCountry == "COL":
      documentType, documentValidation, countryCode, countryDetected, isCountry = detectDocument(
        img=imagenDocumento, countryCode=userCountry, side=ladoDocumento, type=tipoDocumento
      )

      checkSide['documentValidation'] = documentValidation

      resultsDict['document'] = {
        'type': documentType,
        'typeCheck': documentValidation,
        'isExpired': None,
      }

      # Validación de país
      if isCountry != 'OK':
        countryCodePre, countryDetectedPre, documentCountryValidationPre = validateDocumentCountry(
          ocr, country=userCountry
        )
        codeC, country, countryValidation = testingCountry([
          {'country': countryCodePre, 'countryDetected': countryDetectedPre, 'validation': documentCountryValidationPre}
        ])

        resultsDict['document']['code'] = codeC
        resultsDict['document']['country'] = country
        resultsDict['document']['countryCheck'] = countryValidation
        checkSide['countryValidation'] = countryValidation

        if countryValidation != 'OK':
          messages.append('El país del documento no se encontró en el documento.')
      else:
        resultsDict['document']['code'] = countryCode
        resultsDict['document']['country'] = countryDetected
        resultsDict['document']['countryCheck'] = isCountry
        checkSide['countryValidation'] = isCountry

        if isCountry != 'OK':
          messages.append('El país del documento no se encontró en el documento.')

      # Validación de tipo de documento
      if documentValidation != 'OK':
        messages.append('El tipo de documento no coincide con el seleccionado.')

    else:
      typeDetectedPre, documentTypeValidationPre = validateDocumentType(
        tipoDocumento, ladoDocumento, ocr, detectionData=ocrData
      )
      documentType, documentValidation = testingType([
        {'type': typeDetectedPre, 'validation': documentTypeValidationPre}
      ])

      checkSide['documentValidation'] = documentValidation

      resultsDict['document'] = {
        'type': documentType,
        'typeCheck': documentValidation,
        'isExpired': None
      }

      if documentValidation != 'OK':
        messages.append('El tipo de documento no coincide con el seleccionado.')


    # typeDetectedPre, documentTypeValidationPre = validateDocumentType(tipoDocumento, ladoDocumento, ocr, ocrData)
    # documentType, documentValidation = testingType([{'type':typeDetectedPre, 'validation':documentTypeValidationPre}])

    timeOcrEnd = time.time()
    OCRtime = timeOcrInit - timeOcrEnd
    print('ocr time ', OCRtime)

    # if(tipoDocumento != 'CEDULA DE EXTRANJERIA'):
    #   if(documentValidation != 'OK'):
    #     messages.append('El tipo de documento no coincide con el seleccionado.')

    #   checkSide['documentValidation'] = documentValidation

    #   resultsDict['document']['type'] = documentType
    #   resultsDict['document']['typeCheck'] = documentValidation


    codeTimeInit = time.time()


    mrzLetter, documentMRZ = MRZSide(documentType=tipoDocumento, documentSide=ladoDocumento, mrzData=mrzData)
    if(documentMRZ):

      nameHasK = nombre.find("k")
      lastNamehasK = apellido.find("k")

      mrz =  extractMRZ(imagenDocumento)

      # if(nameHasK == -1 or lastNamehasK == -1):
      #   mrz = mrz['raw_text'].replace('K', ' ')

      if(mrz == "No se pudo detectar MRZ válido en la imagen." and tipoDocumento != 'CEDULA DE CIUDADANIA'):
        messages.append('No se pudo detecar el código mrz del documento.')

      if('valid_score' in mrz):
        if mrz['valid_score'] >= 51:
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

          # if(tipoDocumento != 'CEDULA DE CIUDADANIA'):
          #   checkSide['mrzNamePercent'] = 'OK' if nameMRZ['percent'] >= 50 else '!OK'
          #   checkSide['mrzLastNamePercent'] = 'OK' if lastNameMRZ['percent'] >= 50 else '!OK'

          # if(tipoDocumento == 'CEDULA DIGITAL'):
          #   if 'type' in mrz:
          #     if(mrz['type'] == 'IC' or mrz['type'] == 'TC'):
          #       checkSide['documentValidation'] = 'OK'

          #       resultsDict['document']['type'] = 'CEDULA DE CIUDADANIA'
          #       resultsDict['document']['typeCheck'] = 'OK'

          #       checkSide['typeCheck'] ='OK'

          #     else:
          #       resultsDict['document']['type'] = documentType
          #       resultsDict['document']['typeCheck'] = documentValidation

          #       checkSide['typeCheck'] = documentValidation
          #   else:
          #     # checkSide['documentValidation'] = documentValidation

          #     resultsDict['document']['type'] = documentType
          #     resultsDict['document']['typeCheck'] = documentValidation

          #     checkSide['typeCheck'] = documentValidation
          
          # if(tipoDocumento == 'CEDULA DE CIUDADANIA'):

          #   if 'type' in mrz:
          #     if(mrz['type'] == 'IC' or mrz['type'] == 'TC'):
          #       checkSide['documentValidation'] = 'OK'

          #       resultsDict['document']['type'] = 'CEDULA DE CIUDADANIA'
          #       resultsDict['document']['typeCheck'] = 'OK'

          #       checkSide['typeCheck'] ='OK'

          #     else:

          #       # checkSide['documentValidation'] = documentValidation

          #       resultsDict['document']['type'] = documentType
          #       resultsDict['document']['typeCheck'] = documentValidation

          #       checkSide['typeCheck'] = documentValidation
          #   else:
          #     # checkSide['documentValidation'] = documentValidation

          #     resultsDict['document']['type'] = documentType
          #     resultsDict['document']['typeCheck'] = documentValidation

          #     checkSide['typeCheck'] = documentValidation

          #   temp['mrz']= {
          #     'mrz': 'OK' if 'raw_text' in mrz else '!OK',
          #     'mrzNamePercent': 'OK' if nameMRZ['percent'] >= 50 else '!OK',
          #     'mrzLastNamePercent': 'OK' if lastNameMRZ['percent'] >= 50 else '!OK'
          #   }

          # if(tipoDocumento == 'CEDULA DE EXTRANJERIA'):
          #   if 'type' in mrz:
          #     if(mrz['type'] == 'I<' or mrz['type'] == 'T<'):
          #       checkSide['documentValidation'] = 'OK'

          #       resultsDict['document']['type'] = 'CEDULA DE EXTRANJERIA'
          #       resultsDict['document']['typeCheck'] = 'OK'

          #       checkSide['typeCheck'] ='OK'

          #     else:
          #       # checkSide['documentValidation'] = documentValidation

          #       resultsDict['document']['type'] = documentType
          #       resultsDict['document']['typeCheck'] = documentValidation

          #       checkSide['typeCheck'] = documentValidation
          #   else:
          #     # checkSide['documentValidation'] = documentValidation

          #     resultsDict['document']['type'] = documentType
          #     resultsDict['document']['typeCheck'] = documentValidation

          #     checkSide['typeCheck'] = documentValidation

          if(nameMRZ['percent']<= 50 and tipoDocumento != 'CEDULA DE CIUDADANIA'):
            messages.append('No se encontró el nombre en el codigo mrz.')
          if(lastNameMRZ['percent']<= 50 and tipoDocumento != 'CEDULA DE CIUDADANIA'):
            messages.append('No se encontró el apellido en el codigo mrz.')

          if userCountry != 'COL':
            if 'type' in mrz:
              if(mrz['type'] == 'I<' or mrz['type'] == 'T<'):
                checkSide['documentValidation'] = 'OK'

                resultsDict['document']['type'] = 'DNI'
                resultsDict['document']['typeCheck'] = 'OK'

                checkSide['typeCheck'] ='OK'

              elif(mrz['type'] == 'P<'):

                checkSide['documentValidation'] = 'OK'

                resultsDict['document']['type'] = 'PASAPORTE'
                resultsDict['document']['typeCheck'] = 'OK'

                checkSide['typeCheck'] ='OK'
              else:
                # checkSide['documentValidation'] = documentValidation

                resultsDict['document']['type'] = documentType
                resultsDict['document']['typeCheck'] = documentValidation

                checkSide['typeCheck'] = documentValidation
            # else:
            #   # checkSide['documentValidation'] = documentValidation

            #   resultsDict['document']['type'] = documentType
            #   resultsDict['document']['typeCheck'] = documentValidation

            #   checkSide['typeCheck'] = documentValidation

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

            resultsDict['document']['type'] = documentType
            resultsDict['document']['typeCheck'] = documentValidation

            checkSide['typeCheck'] = documentValidation

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

        resultsDict['document']['type'] = documentType
        resultsDict['document']['typeCheck'] = documentValidation

        checkSide['typeCheck'] = documentValidation
        
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

      resultsDict['document']['type'] = documentType
      resultsDict['document']['typeCheck'] = documentValidation

      checkSide['typeCheck'] = documentValidation

    # Si no se detecta el país por MRZ ni por barcode, intentar por OCR
    if resultsDict['mrz']['code'] == '' or resultsDict['mrz']['code'] == 'No se pudo detectar MRZ válido en la imagen.' and resultsDict['barcode'] == '!OK':
      countryCodePre, countryDetectedPre, documentCountryValidationPre = validateDocumentCountry(ocr, country=userCountry)
      codeC, country, countryValidation = testingCountry([{'country': countryCodePre, 'countryDetected': countryDetectedPre, 'validation': documentCountryValidationPre}])
      if(countryValidation != 'OK'):
        messages.append('El país del documento no coincide.')

      resultsDict['document']['code'] = codeC
      resultsDict['document']['country'] = country
      resultsDict['document']['countryCheck'] = countryValidation

      checkSide['countryValidation'] = countryValidation

    if(tipoDocumento == 'CEDULA DE CIUDADANIA' and documentMRZ and documentBarcode):

      # Flags para evitar mensajes duplicados
      mrz_message_added = False
      barcode_message_added = False

      # Si se detecta MRZ y no código de barras, solo usar MRZ
      if temp['mrz'] is not None and (temp['barcode'] is None or temp['barcode'] == '!OK'):
        checkSide['mrzNamePercent'] = temp['mrz']['mrzNamePercent']
        checkSide['mrzLastNamePercent'] = temp['mrz']['mrzLastNamePercent']

        if temp['mrz']['mrz'] == 'OK':
          if temp['mrz']['mrzNamePercent'] != 'OK' and not mrz_message_added:
            messages.append('El nombre en el mrz no alcanzó el porcentaje minimo.')
            mrz_message_added = True
          if temp['mrz']['mrzLastNamePercent'] != 'OK' and not mrz_message_added:
            messages.append('El apellido en el mrz no alcanzó el porcentaje minimo.')
            mrz_message_added = True
        else:
          if not mrz_message_added:
            messages.append('No se pudo detectar el código de mrz del documento.')
            mrz_message_added = True

      # Si se detecta código de barras y no MRZ, solo usar código de barras
      if temp['barcode'] is not None and (temp['mrz'] is None or temp['mrz']['mrz'] != 'OK'):
        resultsDict['barcode'] = temp['barcode'] if temp['barcode'] == 'OK' else None
        if temp['barcode'] == '!OK' and not barcode_message_added:
          messages.append('No se pudo detectar el código de barras del documento.')
          checkSide['barcode'] = temp['barcode']
          barcode_message_added = True

      # Si se detectan ambos, agregarlos al checkSide pero no mostrar mensajes duplicados
      if temp['mrz'] is not None and temp['mrz']['mrz'] == 'OK' and temp['barcode'] is not None and temp['barcode'] == 'OK':
        checkSide['mrzNamePercent'] = temp['mrz']['mrzNamePercent']
        checkSide['mrzLastNamePercent'] = temp['mrz']['mrzLastNamePercent']
        checkSide['barcode'] = temp['barcode']
        # Agregar mensajes si los porcentajes de nombre o apellido son bajos
        if temp['mrz']['mrzNamePercent'] != 'OK' and not mrz_message_added:
          messages.append('El nombre en el mrz no alcanzó el porcentaje minimo.')
          mrz_message_added = True
        if temp['mrz']['mrzLastNamePercent'] != 'OK' and not mrz_message_added:
          messages.append('El apellido en el mrz no alcanzó el porcentaje minimo.')
          mrz_message_added = True

      # Si no se detecta ninguno, agregar ambos mensajes solo una vez cada uno
      if (temp['barcode'] is None or temp['barcode'] == '!OK') and (temp['mrz'] is None or temp['mrz']['mrz'] != 'OK'):
        if not barcode_message_added:
          messages.append('No se pudo detectar el código de barras del documento.')
          barcode_message_added = True
        if not mrz_message_added:
          messages.append('No se pudo detectar el código de mrz del documento.')
          mrz_message_added = True

      if(resultsDict['document']['type'] == '!OK' or resultsDict['document']['typeCheck'] == '!OK'):

        resultsDict['document']['type'] = documentType
        resultsDict['document']['typeCheck'] = documentValidation

    validSide, _, _percent = results(51, 'AUTOMATICA', checkSide)


    codeTimeEnd = time.time()
    codeTime = codeTimeInit - codeTimeEnd

    resultsDict['messages'] = messages

    resultsDict['validSide'] = 'OK' if(validSide) else '!OK'

    if resultsDict['validSide'] == '!OK' and len(messages) >= 1:
      unique_messages = []
      seen = set()
      for msg in resultsDict['messages']:
        if msg not in seen:
          unique_messages.append(msg)
          seen.add(msg)
      resultsDict['messages'] = unique_messages
      # Agregar el mensaje de recomendación al inicio
      resultsDict['messages'].insert(0, 'Por favor, recomendamos buscar buena iluminación y enfocar el documento.')

    if resultsDict['validSide'] == 'OK' and (tipoDocumento == 'CEDULA DE EXTRANJERIA' or tipoDocumento == 'CEDULA DE CIUDADANIA'):
      resultsDict['messages'] = []

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

  print(id, documentType, documentSide)


  barcodes = barcodeReader(imageData, id, documentSide, "pdf417", "")

  print(barcodes)

  return jsonify({
    # 'image': image,
    'barcodeData': barcodes
  })
