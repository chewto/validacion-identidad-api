from PIL import Image
from io import BytesIO
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


def preprocessing(img, resolution, filters):

    h0, w0 = img.shape[:2]

    if resolution < w0:
        h1 = int(h0 * resolution / w0)
        img = cv2.resize(img, (resolution, h1), interpolation=cv2.INTER_AREA)

    proc = img.copy()
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

def _evaluarSimilitudPalabras(palabras_usuario: list[str], palabras_candidatas: list[str]):
    """
    Empareja biyectivamente (1 a 1) las palabras del usuario con las palabras candidatas
    usando la máxima similitud disponible, penalizando palabras sobrantes o faltantes.
    """
    if not palabras_usuario or not palabras_candidatas:
        return 0.0

    similitudes = []
    for u_idx, u_w in enumerate(palabras_usuario):
        for c_idx, c_w in enumerate(palabras_candidatas):
            sim = extraerPorcentaje(u_w, c_w)
            # Si dos palabras son completamente diferentes (ej. RAMIREZ y BARRAGAN),
            # no deben aportar porcentaje positivo residual que infle el promedio de acierto
            if sim < 60.0:
                sim = 0.0
            similitudes.append((sim, u_idx, c_idx))

    # Ordenar de mayor a menor similitud para emparejamiento greedy óptimo
    similitudes.sort(key=lambda x: x[0], reverse=True)

    usados_u = set()
    usados_c = set()
    suma_sim = 0.0

    for sim, u_idx, c_idx in similitudes:
        if u_idx not in usados_u and c_idx not in usados_c:
            usados_u.add(u_idx)
            usados_c.add(c_idx)
            suma_sim += sim

    # Penalizar discrepancias en cantidad de palabras
    total_palabras = max(len(palabras_usuario), len(palabras_candidatas))
    if total_palabras == 0:
        return 0.0

    return suma_sim / total_palabras

def percentsSearch(dataOCR: list[str], dataUsuario: str, onlyNumbers: bool):
    """
    Busca la secuencia o línea en el OCR más similar a dataUsuario.
    Para texto (nombres/apellidos), usa emparejamiento 1 a 1 de tokens con penalización
    por palabras adicionales o faltantes, además de tolerar palabras unidas sin espacio por el OCR.
    """
    def limpiar_texto(texto):
        texto = texto.upper().strip().replace(",", "").replace(".", "").replace("-", "").replace(":", "")
        texto = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
        if onlyNumbers:
            texto = re.sub(r'\D', '', texto)
        return texto

    if onlyNumbers:
        num_usuario = limpiar_texto(dataUsuario)
        if not num_usuario:
            return 'no encontrado', 0

        n = len(num_usuario)
        best_line = 'no encontrado'
        best_pct = 0.0

        for linea_orig in dataOCR:
            if not linea_orig or not str(linea_orig).strip():
                continue
            linea_num = limpiar_texto(str(linea_orig))
            if not linea_num:
                continue

            pct_direct = extraerPorcentaje(num_usuario, linea_num)
            if pct_direct > best_pct:
                best_pct = pct_direct
                best_line = str(linea_orig).strip()

            if len(linea_num) > n:
                for i in range(len(linea_num) - n + 1):
                    sub = linea_num[i:i+n]
                    pct = extraerPorcentaje(num_usuario, sub)
                    if pct > best_pct:
                        best_pct = pct
                        best_line = str(linea_orig).strip()

        return best_line, round(best_pct)

    # Procesamiento para texto (nombres / apellidos)
    palabras_usuario = [limpiar_texto(x) for x in dataUsuario.split() if limpiar_texto(x)]
    n_usr = len(palabras_usuario)
    if n_usr == 0:
        return 'no encontrado', 0

    usuario_compacto = ''.join(palabras_usuario)
    best_pct = 0.0
    best_text = 'no encontrado'

    # Palabras de encabezados o etiquetas comunes que pueden acompañar al dato en una misma línea
    LABEL_WORDS = {'NOMBRES', 'NOMBRE', 'APELLIDOS', 'APELLIDO', 'PRIMER', 'SEGUNDO', 'DE', 'DEL'}

    for linea_orig in dataOCR:
        if not linea_orig or not str(linea_orig).strip():
            continue
        linea_limpia = limpiar_texto(str(linea_orig))
        palabras_linea = [p for p in linea_limpia.split() if p]
        if not palabras_linea:
            continue

        candidatos = [palabras_linea]
        # Si la línea contiene etiquetas de documento, considerar también la versión sin etiqueta
        palabras_filtradas = [p for p in palabras_linea if p not in LABEL_WORDS]
        if palabras_filtradas and palabras_filtradas != palabras_linea:
            candidatos.append(palabras_filtradas)

        for cands in candidatos:
            score_tokens = _evaluarSimilitudPalabras(palabras_usuario, cands)
            cand_compacto = ''.join(cands)
            score_compacto = extraerPorcentaje(usuario_compacto, cand_compacto)

            # Si el OCR unió las palabras en un solo bloque (ej: RAMIREZRAMIREZ) y la coincidencia es alta
            if len(cands) < len(palabras_usuario) and score_compacto >= 75.0:
                score_final = max(score_tokens, score_compacto)
            else:
                score_final = score_tokens

            if score_final > best_pct:
                best_pct = score_final
                best_text = str(linea_orig).strip()

    return best_text, round(best_pct)

def substringSearch(dataOCR: list[str], dataUsuario: str, onlyNumbers: bool):
    """
    Busca la coincidencia de palabras del usuario en el OCR asegurando que cada palabra
    de la línea OCR sólo sea consumida una vez, ponderando subcadenas por cobertura real
    y penalizando palabras discrepantes.
    """
    def limpiar_simple(texto):
        texto = texto.upper().strip().replace(",", "").replace(".", "").replace("-", "").replace(":", "")
        texto = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
        if onlyNumbers:
            return re.sub(r'\D', '', texto)
        return texto

    if onlyNumbers:
        return percentsSearch(dataOCR, dataUsuario, onlyNumbers=True)

    dataUserArr = [limpiar_simple(word) for word in dataUsuario.split() if limpiar_simple(word)]
    if not dataUserArr:
        return 'no encontrado', 0

    usuario_compacto = ''.join(dataUserArr)
    best_match = {'linea': 'no encontrado', 'pct': -1.0}

    for linea_original in dataOCR:
        if not linea_original or not str(linea_original).strip():
            continue

        linea_limpia = limpiar_simple(str(linea_original))
        palabras_ocr = [p for p in linea_limpia.split() if p]
        if not palabras_ocr:
            continue

        ocr_disponibles = list(palabras_ocr)
        suma_coincidencia = 0.0

        for user_word in dataUserArr:
            mejor_coincidencia = 0.0
            mejor_idx = None
            for idx, ocr_w in enumerate(ocr_disponibles):
                if user_word == ocr_w:
                    coincidencia = 1.0
                elif user_word in ocr_w or ocr_w in user_word:
                    # Ponderar por la razón de longitudes para evitar dar 100% a subcadenas parciales (ej: FERNANDO en DANIELFERNANDO)
                    coincidencia = min(len(user_word), len(ocr_w)) / max(len(user_word), len(ocr_w))
                else:
                    sim = extraerPorcentaje(user_word, ocr_w) / 100.0
                    coincidencia = sim if sim >= 0.70 else 0.0

                if coincidencia > mejor_coincidencia:
                    mejor_coincidencia = coincidencia
                    mejor_idx = idx

            if mejor_idx is not None and mejor_coincidencia > 0.0:
                suma_coincidencia += mejor_coincidencia
                ocr_disponibles.pop(mejor_idx)

        total_tokens = max(len(dataUserArr), len(palabras_ocr))
        pct_tokens = (suma_coincidencia / total_tokens) * 100 if total_tokens > 0 else 0.0

        # Tolerancia para palabras unidas por el OCR
        ocr_compacto = ''.join(palabras_ocr)
        pct_compacto = extraerPorcentaje(usuario_compacto, ocr_compacto)
        if len(palabras_ocr) < len(dataUserArr) and pct_compacto >= 75.0:
            pct = max(pct_tokens, pct_compacto)
        else:
            pct = pct_tokens

        if pct > best_match['pct']:
            best_match = {'linea': str(linea_original).strip(), 'pct': pct}

    if best_match['pct'] <= 0:
        return 'no encontrado', 0

    return best_match['linea'], round(best_match['pct'])

def validacionOCR(dataOCR: list[str], dataUsuario: str, onlyNumbers: bool):
    linea_ps, porcentaje_ps = percentsSearch(dataOCR, dataUsuario, onlyNumbers)

    linea_ss, porcentaje_ss = substringSearch(dataOCR, dataUsuario, onlyNumbers)

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