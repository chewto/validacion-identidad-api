from PIL import Image
from io import BytesIO
import easyocr
import pytesseract as tess
import base64
import cv2
import Levenshtein
from utilidades import readDataURL, ordenamiento, extraerPorcentaje
import numpy as np
import datetime
import re


# tess.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

country = 'COL'

countries = {
    'HND': ['HONDURAS'],
    'COL': ['COLOMBIA', 'AMAZONAS', 'ANTIOQUIA', 'BOGOTA' 'ARAUCA', 'ATLANTICO', 'BOLIVAR', 'BOYACA', 'CALDAS', 'CAQUETA', 'CASANARE', 'CAUCA', 'CESAR', 'CHOCO', 'CORDOBA', 'CUNDINAMARCA', 'GUAINIA', 'GUAVIARE', 'HUILA', 'LA GUAJIRA', 'MAGDALENA', 'META', 'NARIÑO', 'NORTE DE SANTANDER', 'PUTUMAYO', 'QUINDIO', 'RISARALDA', 'SAN ANDRES Y PROVIDENCIA', 'SANTANDER', 'SUCRE', 'TOLIMA', 'VALLE DEL CAUCA', 'VAUPES', 'VICHADA'],
    'PTY': ['PANAMA']
}

ocrHash = {
        "COL": {
            "Cédula de ciudadanía": {
                "anverso": ["IDENTIFICACION PERSONAL"],
                "reverso": ['FECHA Y LUGAR DE EXPEDICION', 'FECHA Y LUGAR', 'INDICE DERECHO', 'ESTATURA', 'FECHA DE NACIMIENTO']
            },
            "Cédula de extranjería": {
                "anverso": ["Cedula de Extranjeria","Cédula", "Extranjeria", 'NACIONALIDAD', 'EXPEDICION', 'VENCE', 'NO.', "REPUBLICA", "COLOMBIA", "MIGRANTE"],
                "reverso": ["MIGRACION", 'DOCUMENTO', 'NOTIFICAR', 'CAMBIO', 'MIGRATORIA', 'HOLDER', 'STATUS', 'MIGRATION', 'INFORMACION', "www.migracioncolombia.gov.co", "document", "titular", "documento"]
            },
            "Permiso por protección temporal": {
                "anverso": [],
                "reverso": []
            },
            "Pasaporte":{
                "anverso":['REPUBLICA DE COLOMBIA', 'PASAPORTE', 'PASSPORT'],
                "reverso":[]
            },
            "Cédula digital": {
                "anverso":['NUIP','Estatura','Fecha y lugar', 'expiracion'],
                "reverso":["IC"]
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
            'reverso': ['HND', 'DOMICILIO / ADDRESS']
        },
        'Pasaporte': {
            'anverso': ['PASAPORTE',  'PASSPORT'],
            'reverso': []
        }
    },
    "COL": {
            "Cédula de ciudadanía": {
                "anverso": ["IDENTIFICACION PERSONAL"],
                "reverso": ['FECHA Y LUGAR DE EXPEDICION', 'FECHA Y LUGAR', 'INDICE DERECHO', 'ESTATURA', 'FECHA DE NACIMIENTO', 'LUGAR DE NACIMIENTO']
            },
            "Cédula de extranjería": {
                "anverso": ["Cedula de Extranjeria","Cédula", "Extranjeria", 'EXPEDICION', 'VENCE', 'NO.', "MIGRANTE"],
                "reverso": ["MIGRACION", 'DOCUMENTO', 'NOTIFICAR', 'CAMBIO', 'MIGRATORIA', 'HOLDER', 'STATUS', 'MIGRATION', 'INFORMACION', "www.migracioncolombia.gov.co", "migracioncolombia", "www.migracioncolombia", 'status', "document", "titular", "documento"]
            },
            "Pasaporte": {
                "anverso": ["Passport", "PASAPORTE", "PASSPORT", "Pasaporte", "REPUBLICA DE COLOMBIA"],
                "reverso": []
            },
            "Cédula digital": {
                "anverso":[ 'NUIP','Estatura','lugar', 'expiracion'],
                "reverso":["IC"]
            }
    }
}

# "REPUBLICA DE COLOMBIA"

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

    reference = None

    for (coords, data, _) in ocrData:

        #para cedula de extranjeria
        # if ('VENCE' in data):
        #     reference = (coords, data)
        if ('' in data):
            reference = (coords, data)

    nearestCoords = None
    min_distance = float('inf')

    for (coords, data, _) in ocrData:
        x, y = coords[0]
        if reference:
            refCoords, _ = reference
            rX, rY = refCoords[0]
            # agregar if dependiendo de la direccion (realiza un hash map como siempre)
            # if x > rX:
            #     distance = abs(y - rY)
            #     if distance < min_distance:
            #         min_distance = distance
            #         nearestCoords = [coords, data]


            if y > rY:
                print(coords, data)
                # distance = abs(y - rY)
                # if distance < min_distance:
                #     min_distance = distance
                #     nearestCoords = [coords, data]

    if nearestCoords:
        print(f"Nearest coords to the reference in Y axis: {nearestCoords}")


#  for (coords, data, _) in ocrData:
#         x, y, w, h = coords
#         if reference:
#             ref_coords, _ = reference
#             rX, rY, rW, rH = ref_coords
#             if x > rX + rW and abs(y - rY) < h:
#                 print(f"({x}, {y}) está al lado derecho y verticalmente más cercano a la referencia ({rX}, {rY}, {rW}, {rH}), {data}")


    print(reference)

    # extraction = extractDate(data=ocrData, documentType=documentType)

    # if(documentType == 'Pasaporte'):
    #     extraction = dateFormatter(extraction)

    # extractedDates = filter(lambda x: len(x) >= 1, extraction)

    # lowerDates = []
    # higherDates = []

    # for date in extractedDates:
    #     splitedDate = date.split('-')

    #     try:
    #         day, month, year = int(splitedDate[0]), int(splitedDate[1]), int(splitedDate[2])

    #         if 1 <= month <= 12:
    #             convertedDate = datetime.date(year, month, day)
    #             if convertedDate > currentDate:
    #                 higherDates.append(convertedDate)
    #             else:
    #                 lowerDates.append(convertedDate)
    #         else: 
    #             raise ValueError("Month must be in 1..12") 
    #     except ValueError as e: 
    #         return True

    # return False if(len(higherDates) >= 1) else True

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
    reader = easyocr.Reader(['es'])

# Read text from an image

    if(preprocesado == False):
        lineas = []
        total_confidence = 0
        result = reader.readtext(imagen)
        for (bbox, text, prob) in result:
            upperCase = text.upper()
            lineas.append(upperCase)
            total_confidence += prob
        # txt: str = tess.image_to_string(imagen)
        # lineas: list[str] = txt.splitlines()
        print(lineas)
        average_confidence = total_confidence / len(result) if result else 0
        print(average_confidence)
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

        lineas = []
        
        total_confidence = 0
        result = reader.readtext(enhancedImage)
        for (bbox, text, prob) in result:
            upperCase = text.upper()
            lineas.append(upperCase)
            total_confidence += prob
            print(text)

        average_confidence = total_confidence / len(result) if result else 0


        return result, lineas


def validateDocumentType(documentType, documentSide, ocr):

    document = documentTypeHash[country][documentType][documentSide]

    for line in ocr:

        for documentLine in document:
            lineUpper = documentLine.upper()
            if(line in lineUpper or lineUpper in line):
                print(line, lineUpper)
                return f'{documentType}', 'OK'

    return 'no detectado', '!OK'

def validateDocumentCountry(ocr):
    lines = ocr

    for line in lines:
        for key, value in countries.items():
            for location in value:
                if(location in line):
                    if(key == country):
                        return key,value[0],'OK'
            if(key in line):
                if(key == country):
                    return key,value[0],'OK'

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


def validarLadoDocumento(tipoDocumento: str, ladoDocumento: str, imagen:str, lineas):

    lineas = []

    # lineas = ocr(imagen=imagen, preprocesado=preprocesado)

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