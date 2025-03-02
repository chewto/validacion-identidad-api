from PIL import Image
from io import BytesIO
import easyocr
import imutils
import pytesseract as tess
import base64
import cv2
import Levenshtein
from utilidades import readDataURL, ordenamiento, extraerPorcentaje
import numpy as np
import datetime
import re


tess.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

country = 'HND'

countries = {
    'HND': 'HONDURAS',
    'COL': 'COLOMBIA',
    'PTY': 'PANAMA'
}

ocrHash = {
        "COL": {
            "Cédula de ciudadanía": {
                "anverso": ["IDENTIFICACION PERSONAL", "CEDULA DE CIUDADANIA", "REPUBLICA DE COLOMBIA"],
                "reverso": ['FECHA Y LUGAR DE EXPEDICION', 'FECHA Y LUGAR', 'INDICE DERECHO', 'ESTATURA', 'FECHA DE NACIMIENTO']
            },
            "Cédula de extranjería": {
                "anverso": ["Cedula de Extranjeria","Cédula", "Extranjeria", 'NACIONALIDAD', 'EXPEDICION', 'VENCE', 'NO.', "REPUBLICA", "COLOMBIA", "MIGRANTE"],
                "reverso": ["MIGRACION", 'DOCUMENTO', 'NOTIFICAR', 'CAMBIO', 'MIGRATORIA', 'HOLDER', 'STATUS', 'MIGRATION', 'INFORMACION', "COLOMBIA", "www.migracioncolombia.gov.co", "<", "document", "titular", "documento"]
            },
            "Permiso por protección temporal": {
                "anverso": [],
                "reverso": []
            },
            "Pasaporte":{
                "anverso":['REPUBLICA DE COLOMBIA', 'PASAPORTE', 'PASSPORT'],
                "reverso":[]
            }
        },
        "PTY":{
            "Cédula de ciudadanía": {
                "anverso": ['REPUBLICA DE PANAMA','TRIBUNAL ELECTORAL'],
                "reverso": ['TRIBUNAL', 'ELECTORAL']
            },
            "Cédula de extranjería": {
                "anverso": [],
                "reverso": []
            }
        },
        "HND":{
            "DNI": {
                "anverso": ['REGISTRO', 'NACIONAL','PERSONAS', 'HONDURAS', 'REGISTRO', 'DOCUMENTO', 'NACIONAL DE IDENTIFICACION', 'DOCUMENTO', 'IDENTIFICACION', 'LUGAR', 'NACIMIENTO', 'NACIONALIDAD', 'REGISTRO'],
                "reverso": ['HND', 'COMISIONADOS', 'PROPIETARIOS', '<']
            },
            "Carnet de residente": {
                "anverso": [],
                "reverso": []
            },
            "carnet de conducir": {
                "anverso": [],
                "reverso": []
            },
            "Pasaporte":{
                "anverso":['HONDURAS', 'REPUBLICA', 'TIPO', 'TYPE', 'EMISOR','PASAPORTE','PASSPORT', 'NACIONALIDAD', 'NATIONALITY','HONDURENA', 'HONDUREÑA', 'INSTITUTO', 'NACIONAL', 'MIGRACION', '<'],
                "reverso":[]
            }
        }
    }


documentTypeHash = {
    'HND':{
        'DNI':{
            'anverso': ['DOCUMENTO NACIONAL DE IDENTIFICACION', 'REGISTRO NACIONAL DE LAS PERSONAS'],
            'reverso': ['<', 'HND']
        },
        'Pasaporte': {
            'anverso': ['PASAPORTE',  'PASSPORT'],
            'reverso': []
        }
    },
    "COL": {
            "Cédula de ciudadanía": {
                "anverso": ["IDENTIFICACION PERSONAL", "CEDULA DE CIUDADANIA", "REPUBLICA DE COLOMBIA"],
                "reverso": ['FECHA Y LUGAR DE EXPEDICION', 'FECHA Y LUGAR', 'INDICE DERECHO', 'ESTATURA', 'FECHA DE NACIMIENTO']
            },
            "Cédula de extranjería": {
                "anverso": ["Cedula de Extranjeria","Cédula", "Extranjeria", 'NACIONALIDAD', 'EXPEDICION', 'VENCE', 'NO.', "REPUBLICA", "COLOMBIA", "MIGRANTE"],
                "reverso": ["MIGRACION", 'DOCUMENTO', 'NOTIFICAR', 'CAMBIO', 'MIGRATORIA', 'HOLDER', 'STATUS', 'MIGRATION', 'INFORMACION', "COLOMBIA", "www.migracioncolombia.gov.co", "<", "document", "titular", "documento"]
            },
    }
}

documentReferencePlacement = {
    'HND':{
        'DNI':{
            'anverso': 'left',
            'reverso': ''
        },
        'Pasaporte': {
            'anverso': 'left',
            'reverso': ''
        }
    }
}

def extractDate(data, documentType):
    datePattern = r'\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})\b' 

    if(documentType == 'Pasaporte'):
        datePattern = r'\d{2}\s(?:ENE|FEB|MAR|ABR|MAY|JUN|JUL|AGO|SEP|OCT|NOV|DIC)/(?:ENE|FEB|MAR|ABR|MAY|JUN|JUL|AGO|SEP|OCT|NOV|DIC)\s\d{4}'

    datesFound = []
    
    for line in data:
        match = re.search(datePattern, line)
        if(match is not None):
            matchString = match.string
            dateString = matchString[match.start():match.end()]
            datesFound.append(dateString)

    return datesFound

def dateFormatter(dates):
    monthPattern = r'(?:ENE|FEB|MAR|ABR|MAY|JUN|JUL|AGO|SEP|OCT|NOV|DIC)/(?:ENE|FEB|MAR|ABR|MAY|JUN|JUL|AGO|SEP|OCT|NOV|DIC)'

    monthDict = {
        'ENE':'1',
        'FEB':'2',
        'MAR':'3',
        'ABR':'4',
        'MAY':'5',
        'JUN':'6',
        'JUL':'7',
        'AGO':'8',
        'SEP':'9',
        'OCT':'10',
        'NOV':'11',
        'DIC':'12',
    }

    datesFound = []

    for date in dates:
        match = re.search(monthPattern, date)
        if(match is not None):
            matchStart = match.start()
            matchEnd = match.end()
            matchString = match.string
            matchLength = len(matchString)
            monthString = matchString[matchStart:matchEnd]
            monthSplitted = monthString.split('/')
            monthExtracted = monthSplitted[0]
            month = monthDict[monthExtracted]
            day = matchString[0:matchStart]
            year = matchString[matchEnd:matchLength]
            date = f'{day}-{month}-{year}'
            datesFound.append(date)

    return datesFound

def expiracyDateOCR(ocrData, documentType):

    currentDate = datetime.date.today()

    extraction = extractDate(data=ocrData, documentType=documentType)

    if(documentType == 'Pasaporte'):
        extraction = dateFormatter(extraction)

    extractedDates = filter(lambda x: len(x) >= 1, extraction)

    lowerDates = []
    higherDates = []

    for date in extractedDates:
        splitedDate = date.split('-')

        try:
            day, month, year = int(splitedDate[0]), int(splitedDate[1]), int(splitedDate[2])

            if 1 <= month <= 12:
                convertedDate = datetime.date(year, month, day)
                if convertedDate > currentDate:
                    higherDates.append(convertedDate)
                else:
                    lowerDates.append(convertedDate)
            else: 
                raise ValueError("Month must be in 1..12") 
        except ValueError as e: 
            return True

    return False if(len(higherDates) >= 1) else True

def verificacionRostro(dataURL: str):

    gray = cv2.cvtColor(dataURL, cv2.COLOR_BGR2GRAY)

    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_alt.xml")

    scaleFactor = 1.1
    minNeighbors = 5
    minSize = (30, 30)

    found = False
    intentos = 0

    while not found and intentos < 4:  # Try rotating the dataURL up to 4 times
        faces = face_cascade.detectMultiScale(gray, scaleFactor=scaleFactor, minNeighbors=minNeighbors, minSize=minSize)

        if len(faces) > 0:
            found = True
            return True
        else:
            dataURL = cv2.rotate(dataURL, cv2.ROTATE_90_CLOCKWISE)
            gray = cv2.cvtColor(dataURL, cv2.COLOR_BGR2GRAY)
            intentos += 1

    if not found:
        return False

def ocr(imagen: str, preprocesado):

    if(preprocesado == False):
        txt: str = tess.image_to_string(imagen)
        lineas: list[str] = txt.splitlines()
        return lineas

    if(preprocesado):

        gris = cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY)
        kernel = np.array([[0, -1, 0], [-1, 5,-1], [0, -1, 0]]) 
        sharpened = cv2.filter2D(gris, -1, kernel)
        invertedImage = cv2.bitwise_not(sharpened)
        enhancedImage = cv2.convertScaleAbs(invertedImage, alpha=1.0, beta=-25)
        # threshold = cv2.adaptiveThreshold(gris, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 35, 7)
        # kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1,1))
        # opened = cv2.morphologyEx(threshold, cv2.MORPH_RECT, kernel, iterations=1)

        txt: str = tess.image_to_string(enhancedImage)

        lineas: list[str] = txt.splitlines()
        return lineas


def detect_text(image):
  """Use EasyOCR to detect text in the image."""
  reader = easyocr.Reader(['en'], gpu=False)  # Specify the language
  results = reader.readtext(image)
  return results

def rotate_image(image, angle):
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)

    # Get the rotation matrix for the given angle
    M = cv2.getRotationMatrix2D(center, angle, 1.0)

    # Calculate the new bounding box dimensions
    abs_cos = abs(M[0, 0])
    abs_sin = abs(M[0, 1])
    new_w = int(h * abs_sin + w * abs_cos)
    new_h = int(h * abs_cos + w * abs_sin)

    # Adjust the rotation matrix to account for the translation
    M[0, 2] += (new_w / 2) - center[0]
    M[1, 2] += (new_h / 2) - center[1]

    # Perform the rotation with the new bounding box dimensions
    rotated = cv2.warpAffine(image, M, (new_w, new_h))
    return rotated

def orientation(dataURL: str, reference, documentType, documentSide):

    refPlacement = documentReferencePlacement[country][documentType][documentSide]

    image = cv2.cvtColor(dataURL, cv2.COLOR_BGR2RGB)
    kernel = np.array([[0, -1, 0], [-1, 5,-1], [0, -1, 0]]) 
    sharpened = cv2.filter2D(image, -1, kernel)
    invertedImage = cv2.bitwise_not(sharpened)
    enhancedImage = cv2.convertScaleAbs(invertedImage, alpha=1.0, beta=-25)

    results = detect_text(enhancedImage)
    
    boxCounter = {
        'wider': 0,
        'higher': 0,
        'equal': 0
    }

    textCoords = []

# Loop through the results and draw bounding boxes
    for (bbox, text, prob) in results:
        (top_left, top_right, bottom_right, bottom_left) = bbox
        top_left = tuple(map(int, top_left))
        top_right = tuple(map(int, top_right))
        bottom_right = tuple(map(int, bottom_right))
        bottom_left = tuple(map(int, bottom_left))

        width = bottom_right[0] - top_left[0]
        height = bottom_right[1] - top_left[1]

        textCoords.append((top_left, top_right, bottom_right, bottom_left))  # Append all limits of the text box

        if(width > height):
            boxCounter['wider'] += 1
        
        if(width < height):
            boxCounter["higher"] += 1
        
        if(width == height):
            boxCounter["equal"] += 1

    if(boxCounter['wider'] < boxCounter['higher']):
        # Rotate the image 90 degrees counterclockwise

        rotate180 = 0
        notRotate = 0

        leftLimit = reference[0]
        rightLimit = reference[1]

        rotatedImage = cv2.rotate(dataURL, cv2.ROTATE_90_COUNTERCLOCKWISE)

        detectedTextTest = detect_text(rotatedImage)

        for (bbox, _, _) in detectedTextTest:
            (top_left, top_right, bottom_right, bottom_left) = bbox
            top_left = tuple(map(int, top_left))
            top_right = tuple(map(int, top_right))
            bottom_right = tuple(map(int, bottom_right))
            bottom_left = tuple(map(int, bottom_left))

            textLeftLimit = min(top_left[0], bottom_left[0])
            textRightLimit = max(top_right[0], bottom_right[0])

            if(refPlacement == 'left'):
                if leftLimit > textLeftLimit and rightLimit > textRightLimit :
                    rotate180 += 1
                else:
                    notRotate += 1

        if(refPlacement == 'left'):
            print('rated', rotate180, notRotate)
            # rotatedImage = cv2.rotate(rotatedImage, cv2.ROTATE_180)

            return rotatedImage

            # if textLeftLimit > rightLimit:
            #     right += 1
            # elif textRightLimit > leftLimit:
            #     left += 1

        # print(f"left: {left}, right: {right}")

        # if refPlacement == 'left':
        #     if left >= right:
        #         print('test')
        #         return rotatedImage
        #     else:
        #         print('bombaclar')
        #         rotatedImage = cv2.rotate(rotatedImage, cv2.ROTATE_180)
        #         return rotatedImage
        # else:
        #     if right >= left:
        #         return rotatedImage
        #     else:
        #         return dataURL

        # if refPlacement == 'left':
        #     if left >= right:
        #         return rotatedImage
        #     else:
        #         return dataURL
        # else:
        #     if right >= left:
        #         return rotatedImage
        #     else:
        #         return dataURL
        
        # info = tess.image_to_osd(rotatedImage, output_type=tess.Output.DICT)
        # print(info['rotate'])

        # if(info['rotate'] == 180):
        #     rotatedImage = cv2.rotate(rotatedImage, cv2.ROTATE_180)
        #     return rotatedImage

    # # Compare the coordinates of the text with the reference coordinates
    #     for (top_left, top_right, bottom_right, bottom_left) in textCoords:
    #         top_limit = min(top_left[1], top_right[1])
    #         bottom_limit = max(bottom_left[1], bottom_right[1])

    #         firstRef = reference[0]
    #         secondRef = reference[1]

    #         print('refs', firstRef, secondRef)
    #         print('limits', top_limit, bottom_limit)

    #         if top_limit > firstRef and top_limit > secondRef:
    #             print('The image is below the reference')
    #         elif bottom_limit < firstRef and bottom_limit < secondRef:
    #             print('The image is above the reference')

    #         # print(reference)
    #         # print(f'Top limit: {top_limit}, Bottom limit: {bottom_limit}')

    #         # if(top_limit > reference[0] and top_limit > reference[1]):
    #         #     print('el texto esta por debajo la foto')

    #         # if(bottom_limit < reference[0] and bottom_limit < reference[1]):
    #         #     print('el texto esta por encima de la foto')

    #         # if top_limit < reference[0] and bottom_limit > reference[0]:
    #         #     print('esta por debajo')
    #         # if top_limit > reference[0] and bottom_limit < reference[0]:
    #         #     print('esta por encima')
    #         # return dataURL



        return dataURL



    #evaluate if the document is upside down

#   # Rotate the image and detect text for each angle
#     # for angle in [0, 90, 180, 270]:
#     for angle in [0]:
#         rotated_image = rotate_image(enhancedImage, angle)
#         rotatedCopy = rotate_image(dataURL, angle)
#         results = detect_text(rotated_image)
#         print(results)
#         sumConfidence = 0
#         for result in results:
#             sumConfidence += result[2]

#         all_results.append((angle, sumConfidence,rotatedCopy))

#     best_angle, best_confidence, best_image = max(all_results, key=lambda x: x[1])

#     # rotatedImage = cv2.cvtColor(best_image, cv2.COLOR_BGR2RGB)

    return dataURL

# def evaluatePlacement(ref, text, ):

def validateDocumentType(documentType, documentSide, ocr):

    document = documentTypeHash[country][documentType][documentSide]

    for line in ocr:

        for documentLine in document:
            if(len(line) >= 1 and (line in documentLine or documentLine in line)):

                return f'{documentType}', 'OK'

    return 'no detectado', '!OK'

def validateDocumentCountry(ocr):
    lines = ocr

    for line in lines:
        for key, value in countries.items():
            if(value in line):
                if(key == country):
                    return key,value,'OK'
            if(key in line):
                if(key == country):
                    return key,value,'OK'

    return 'no detectado','no detectado', '!OK'

def validacionOCR(dataOCR, dataUsuario):

    dataUsuario = dataUsuario.split(" ")

    porcentajes = []
    
    for linea in dataOCR:

        linea = linea.upper()
        linea = linea.strip()
        linea = linea.replace(",","").replace(".","").replace("-","")
        linea = linea.split(" ")

        for lineaElemento in linea:

            for dataElemento in dataUsuario:
                if(len(lineaElemento) >=1):
                    porcentaje = extraerPorcentaje(dataElemento, lineaElemento)
                    similitud = Levenshtein.distance(dataElemento, lineaElemento)
                    data = {
                        "similitud": similitud,
                        "porcentaje": porcentaje,
                        "linea": lineaElemento
                    }

                    porcentajes.append(data)

    porcentajesOrdenados = ordenamiento(porcentajes)

    data, porcentaje = busquedaResultado(porcentajesOrdenados, dataUsuario)

    return data, porcentaje


def busquedaResultado(porcentajes, dataUsuario):

    if(len(porcentajes) <= 0):
        return 'no encontrado', 0

    data = []

    porcentajeAcumulado = 0

    index = len(dataUsuario)

    activado = True

    vueltas = 0

    while activado == True:
        info = porcentajes[vueltas]
        data.append(info['linea'])
        porcentajeAcumulado = porcentajeAcumulado + (info['porcentaje'] / index)
        vueltas += 1
        if(vueltas >= index):
            activado = False

    data = ' '.join(data)
    porcentajeAcumulado = round(porcentajeAcumulado)

    if(porcentajeAcumulado <= 0):
        data = 'no encontrado'

    return data, porcentajeAcumulado


def limpiarData(dataSinLimpiar: str, dataBase: str):

    dataArray = dataSinLimpiar.split(' ')

    dataBaseArray = dataBase.split(' ')

    dataLimpiaArr = []

    for data, dataComparacion in zip(dataArray, dataBaseArray):
        if (data == dataComparacion):
            dataLimpiaArr.append(dataComparacion)

    dataLimpiaStr = ' '.join(dataLimpiaArr)

    return dataLimpiaStr


def validarOCR(infoDocumento, nombre:str, apellido:str, numeroDocumento:str):

    nombreParam = nombre.upper()
    apellidoParam = apellido.upper()
    numeroDocumentoParam = numeroDocumento.upper()

    nombreOCR = ''
    apellidoOCR = ''
    numeroDocumentoOCR = ''

    coincidenciaNombre = 0
    coincidenciaApellido = 0
    coincidenciaDocumento = 0

    if ('nombre' in infoDocumento and len(nombreParam) >= 1):
        nombreOCR = infoDocumento['nombre']
        coincidenciaNombre += extraerPorcentaje(nombreParam, nombreOCR)

    if ('apellido' in infoDocumento and len(apellidoParam) >= 1):
        apellidoOCR = infoDocumento['apellido']
        coincidenciaApellido += extraerPorcentaje(apellidoParam, apellidoOCR)


    if ('numeroDocumento' in infoDocumento and len(numeroDocumentoParam) >= 1):
        numeroDocumentoOCR = infoDocumento['numeroDocumento']
        # coincidenciaDocumento += porcentajeDocumento(numeroDocumentoParam, numeroDocumentoOCR)

    return coincidenciaNombre, coincidenciaApellido, coincidenciaDocumento

def comparacionOCR(porcentajePre,ocrPre, porcentajeSencillo, ocrSencillo):

    if(porcentajePre >= porcentajeSencillo):
        return ocrPre, porcentajePre

    if(porcentajeSencillo >= porcentajePre):
        return ocrSencillo, porcentajeSencillo


def validarLadoDocumento(tipoDocumento: str, ladoDocumento: str, imagen:str, ocr):

    lineas = ocr

    ladoPalabras = ocrHash[country][tipoDocumento][ladoDocumento]

    coincidencias = 0

    porcentajes = []

    lineasLimpias = []

    for linea in lineas:
        if(len(linea) >= 1):
            nuevaLinea = linea.split(" ")

            for elementoNuevaLinea in nuevaLinea:

                if(len(elementoNuevaLinea) >= 2):
                    lineasLimpias.append(elementoNuevaLinea)

    for linea in lineasLimpias:

        for palabra in ladoPalabras:

            linea = linea.upper()

            palabra = palabra.upper()

            if(len(linea) >=1):
                    if(palabra in linea):
                        coincidencias += 1

                    porcentaje = extraerPorcentaje(palabra, linea)
                    similitud = Levenshtein.distance(palabra, linea)
                    data = {
                        "similitud": similitud,
                        "porcentaje": porcentaje,
                        "linea": linea
                    }

                    porcentajes.append(data)

    ordenarPorcentajes = ordenamiento(porcentajes)

    for orden in ordenarPorcentajes:
        if orden['porcentaje'] >= 75:
            coincidencias += 1

    return coincidencias

def busquedaData(ocr,nombre, apellido, documento):

    data = []

    documentoEncontrado = []

    nombreEncontrado = []

    for linea in ocr:
        if(len(linea) >= 1):
            nuevaLinea = linea.split(" ")

            for elementoNuevaLinea in nuevaLinea:

                if(len(elementoNuevaLinea) >= 2 and elementoNuevaLinea.find("<") != -1):
                    data.append(elementoNuevaLinea)

    for info in data:
        if(info.find(nombre) != -1):
            divisionNombre = info.split("<")
            for linea in divisionNombre:
                if(len(linea) >=1):
                    nombreEncontrado.append(linea)
        if(info.find(documento) != -1):
            divisionNombre = info.split("<")
            for linea in divisionNombre:
                if(len(linea) >=1):
                    documentoEncontrado.append(linea)