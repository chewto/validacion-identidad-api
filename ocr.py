from PIL import Image
from io import BytesIO
import easyocr
import imutils
import pytesseract as tess
import base64
import cv2
import Levenshtein
from utilities.utilidades import readDataURL, ordenamiento, extraerPorcentaje
import numpy as np
import datetime
import re
import unicodedata

countries = {
    'HND': ['HONDURAS'],
    'COL': ['COLOMBIA', 'AMAZONAS', 'ANTIOQUIA', 'BOGOTA' 'ARAUCA', 'ATLANTICO', 'BOLIVAR', 'BOYACA', 'CALDAS', 'CAQUETA', 'CASANARE', 'CAUCA', 'CESAR', 'CHOCO', 'CORDOBA', 'CUNDINAMARCA', 'GUAINIA', 'GUAVIARE', 'HUILA', 'LA GUAJIRA', 'MAGDALENA', 'META', 'NARIÑO', 'NORTE DE SANTANDER', 'PUTUMAYO', 'QUINDIO', 'RISARALDA', 'SAN ANDRES Y PROVIDENCIA', 'SANTANDER', 'SUCRE', 'TOLIMA', 'VALLE DEL CAUCA', 'VAUPES', 'VICHADA', 'GUAVATA'],
    'PTY': ['PANAMA'],
    'SLV': ['EL SALVADOR', 'SAN SALVADOR', 'AHUACHAPAN', 'SONSONATE', 'SANTA ANA', 'LA LIBERTAD', 'CHALATENANGO', 'CUSCATLAN', 'LA PAZ', 'SAN VICENTE', 'CABAÑAS', 'USULUTAN', 'SAN MIGUEL', 'MORAZAN', 'LA UNION']
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
        },
        "SLV":{
            "DNI": {
                "anverso": ['REGISTRO', 'NACIONAL','PERSONAS', 'HONDURAS', 'REGISTRO', 'DOCUMENTO', 'NACIONAL DE IDENTIFICACION', 'DOCUMENTO', 'IDENTIFICACION', 'LUGAR', 'NACIMIENTO', 'NACIONALIDAD', 'REGISTRO'],
                "reverso": ['HND', 'COMISIONADOS', 'PROPIETARIOS', '<']
            },
        }
    }


documentTypeHash = {
    'HND':{
        'DNI':{
            'anverso': ['NACIONAL', 'REGISTRO NACIONAL DE LAS PERSONAS'],
            'reverso': ['HND', 'DOMICILIO / ADDRESS']
        },
        'Pasaporte': {
            'anverso': ['PASAPORTE',  'PASSPORT'],
            'reverso': []
        }
    },
    "COL": {
            "Cédula de ciudadanía": {
                "anverso": ["IDENTIFICACION", "PERSONAL"],
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
    },
    "SLV":{
            "DNI": {
                "anverso": ['UNICO','IDENTIDAD', 'ID', 'SALVADOREÑO', 'BY', 'SALVADOREAN'],
                "reverso": ['ID']
            },
        }
}

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


def adjustBrightness(image_array):

    current_brightness = np.mean(image_array)
    
    # Definir rango objetivo
    target_min = 130
    target_max = 180
    target_mid = (target_min + target_max) / 2
    
    # Calcular factor de ajuste
    if current_brightness < target_min:
        adjustment_factor = target_mid / max(current_brightness, 1)
    elif current_brightness > target_max:
        adjustment_factor = target_mid / current_brightness
    else:
        adjustment_factor = 1.0
    
    # Ajustar brillo y limitar al rango válido
    adjusted_image = np.clip(image_array * adjustment_factor, 0, 255)
    
    return adjusted_image.astype(np.uint8), current_brightness, np.mean(adjusted_image), adjustment_factor

reader = easyocr.Reader(['es'])


def preprocessing(img, resolution, filters):

    h0, w0 = img.shape[:2]

    print(img.shape[:2], 'previo')
    if resolution < w0:
        h1 = int(h0 * resolution / w0)
        img = cv2.resize(img, (resolution, h1), interpolation=cv2.INTER_AREA)

    proc = img.copy()
    print(proc.shape[:2], 'post')
    # if 'gray' in filters:
    #     proc = cv2.cvtColor(proc, cv2.COLOR_BGR2GRAY)
    # if 'hist' in filters:
    #     gray = proc if proc.ndim == 2 else cv2.cvtColor(proc, cv2.COLOR_BGR2GRAY)
    #     proc = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
    # if 'sharp' in filters:
    #     kernel = np.array([[0,-1,0],[-1,5,-1],[0,-1,0]])
    #     proc = cv2.filter2D(proc, -1, kernel)
    # if 'blur' in filters:
    #     proc = cv2.medianBlur(proc, 3)
    # if 'thresh' in filters:
    #     if proc.ndim == 2:
    #         _, proc = cv2.threshold(proc, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # proc_rgb = proc if proc.ndim == 3 else cv2.cvtColor(proc, cv2.COLOR_GRAY2BGR)

    return proc

def ocr(img):

        lineas = []
        
        total_confidence = 0
        result = reader.readtext(img)
        for (bbox, text, prob) in result:
            upperCase = text.upper()
            lineas.append(upperCase)
            total_confidence += prob

        average_confidence = total_confidence / len(result) if result else 0

        return result, lineas


def validateDocumentType(documentType, documentSide, ocr, detectionData):

    documentWords = detectionData['documentDectection'][documentType][documentSide]

    for line in ocr:
        for documentLine in documentWords:
            lineUpper = documentLine.upper()
            if(len(line) >= 1 and len(lineUpper) >= 1):
                if(line in lineUpper or lineUpper in line):
                    return f'{documentType}', True

    return 'no detectado', False

def validateDocumentCountry(ocr, country):

    lines = ocr

    for line in lines:
        for key, value in countries.items():
            for location in value:
                if(location in line):
                    if(key == country):
                        return key,value[0],True
            if(key in line):
                if(key == country):
                    return key,value[0],True

    return 'no detectado','no detectado', False

def extraerPorcentaje(str1, str2):
    """Calcula el porcentaje de similitud entre dos cadenas."""
    if not str1 and not str2:
        return 100.0
    distance = Levenshtein.distance(str1, str2)
    max_len = max(len(str1), len(str2))
    if max_len == 0:
        return 100.0
    similitud = (1 - distance / max_len) * 100
    return similitud

def percentsSearch(dataOCR: list[str], dataUsuario: str, onlyNumbers: bool):
    """
    Busca la secuencia de palabras más similar en el OCR usando Levenshtein
    y un cálculo de porcentaje de similitud.
    """
    def limpiar_texto(texto):
        texto = texto.upper().strip().replace(",", "").replace(".", "").replace("-", "")
        texto = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
        if onlyNumbers:
            texto = re.sub(r'\D', '', texto)
        return texto
    
    dataUsuarioArr = [limpiar_texto(x) for x in dataUsuario.split()]


    n = len(dataUsuarioArr)
    if n == 0:
        return 'no encontrado', 0
        
    mejores_resultados = []
    ocr_limpio = [limpiar_texto(linea) for linea in dataOCR if len(linea.strip()) > 0]

    for linea in ocr_limpio:    
        palabras = linea.split()
        if len(palabras) >= n:
            for i in range(len(palabras) - n + 1):
                secuencia = palabras[i:i+n]
                porcentaje_total = sum(extraerPorcentaje(dataUsuarioArr[idx], palabra_ocr) for idx, palabra_ocr in enumerate(secuencia))
                similitud_total = sum(Levenshtein.distance(dataUsuarioArr[idx], palabra_ocr) for idx, palabra_ocr in enumerate(secuencia))
                
                mejores_resultados.append({
                    "similitud": similitud_total / n,
                    "porcentaje": porcentaje_total / n,
                    "linea": " ".join(secuencia)
                })

    if not mejores_resultados:
        return 'no encontrado', 0

    mejores_resultados = sorted(mejores_resultados, key=lambda x: (-x['porcentaje'], x['similitud']))
    
    mejor = mejores_resultados[0]
    return mejor['linea'], round(mejor['porcentaje'])

# VERSIÓN CORREGIDA
def substringSearch(dataOCR: list[str], dataUsuario: str, onlyNumbers: bool):
    """
    Busca la línea del OCR con la mayor cantidad de coincidencias de substrings
    y retorna esa línea junto con su porcentaje de acierto.
    """
    def limpiar_simple(texto):
        texto = texto.upper()
        if onlyNumbers:
            return re.sub(r'\D', '', texto)
        return texto

    dataUserArr = [limpiar_simple(word) for word in dataUsuario.split() if word]

    if not dataUserArr:
        return 'no encontrado', 0

    best_match = {'linea': 'no encontrado', 'score': -1, 'len': float('inf')}

    for linea_original in dataOCR:
        if not linea_original.strip():
            continue
        
        linea_limpia = limpiar_simple(linea_original)
        current_score = 0
        
        for user_word in dataUserArr:
            if user_word in linea_limpia:
                current_score += 1

        # Si el puntaje actual es mejor que el mejor que teníamos
        if current_score > best_match['score']:
            best_match = {'linea': linea_original.strip(), 'score': current_score, 'len': len(linea_original)}
        # Si el puntaje es el mismo, usamos la línea más corta como desempate
        elif current_score == best_match['score'] and current_score > 0:
            if len(linea_original) < best_match['len']:
                best_match = {'linea': linea_original.strip(), 'score': current_score, 'len': len(linea_original)}

    if best_match['score'] == -1:
        return 'no encontrado', 0

    # El porcentaje se basa en cuántas palabras del usuario se encontraron
    final_percent = (best_match['score'] / len(dataUserArr)) * 100
    
    return best_match['linea'], round(final_percent)

# --- Función Principal de Validación (Ahora más simple) ---

def validacionOCR(dataOCR: list[str], dataUsuario: str, onlyNumbers: bool):
    linea_ps, porcentaje_ps = percentsSearch(dataOCR, dataUsuario, onlyNumbers)

    linea_ss, porcentaje_ss = substringSearch(dataOCR, dataUsuario, onlyNumbers)

    # La comparación ahora es directa
    if porcentaje_ps >= porcentaje_ss:
        return linea_ps, porcentaje_ps
    else:
        return linea_ss, porcentaje_ss

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


def validarLadoDocumento(tipoDocumento: str, ladoDocumento: str, lineas, ocrData):

    lineas = []

    ladoPalabras = ocrData['documentOcr'][tipoDocumento][ladoDocumento]

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