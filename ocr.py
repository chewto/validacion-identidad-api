from PIL import Image
from io import BytesIO
import pytesseract as tess
import base64
import cv2

tess.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


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


def imagenOCR(imagen:str, nombre:str, apellido:str, numeroDocumento:str):

    imagenData: list[str] = imagen.split(',')[1]

    decoded: bytes = base64.b64decode(imagenData)

    lerrImagen: Image = Image.open(BytesIO(decoded))

    txt: str = tess.image_to_string(lerrImagen)

    lineas: list[str] = txt.splitlines()

    print(lineas)

    informacionOCR = {}

    numeros = '1234567890'

    for linea in lineas:

        linea = linea.upper()
        linea = linea.strip()

        if (linea.find(nombre) != -1):
            nombreIndex = linea.find(nombre)
            nombreSinLimpiar = linea[nombreIndex:]
            nombreLimpio = limpiarData(nombreSinLimpiar, nombre)
            informacionOCR['nombre'] = nombreLimpio

        if (linea.find(apellido) != -1):
            apellidoIndex = linea.find(apellido)
            apellidoSinLimpiar = linea[apellidoIndex:]
            apellidoLimpio = limpiarData(apellidoSinLimpiar, apellido)
            informacionOCR['apellido'] = apellidoLimpio

        if (linea.find(numeroDocumento) != -1):
            documentoArr = linea.split(' ')
            documentoEncontrado = ''

            for elemento in documentoArr:
                if(elemento == numeroDocumento):
                    documentoEncontrado = elemento

            informacionOCR['numeroDocumento'] = documentoEncontrado

    return informacionOCR


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
        coincidenciaNombre += porcetajeNombres(nombreParam, nombreOCR)

    if ('apellido' in infoDocumento and len(apellidoParam) >= 1):
        apellidoOCR = infoDocumento['apellido']
        coincidenciaApellido += porcetajeNombres(apellidoParam, apellidoOCR)


    if ('numeroDocumento' in infoDocumento and len(numeroDocumentoParam) >= 1):
        numeroDocumentoOCR = infoDocumento['numeroDocumento']
        coincidenciaDocumento += porcentajeDocumento(numeroDocumentoParam, numeroDocumentoOCR)

    return coincidenciaNombre, coincidenciaApellido, coincidenciaDocumento


def porcetajeNombres(valorBase:str, valorRecolectado:str):

    validacionMaxima = 100

    porcentajeUnidad = validacionMaxima/len(valorBase)

    porcentajeAcumulado = 0

    for caracter, caracterComparar in zip(valorBase, valorRecolectado):
        if (caracter == caracterComparar):
            porcentajeAcumulado += porcentajeUnidad

    porcentajeAcumulado = round(porcentajeAcumulado)

    return porcentajeAcumulado


def porcentajeDocumento(valorBase:str, valorRecolectado:str):

    validacionMaxima = 100

    porcentajeUnidad = validacionMaxima / len(valorBase)

    porcentajeAcumulado = 0

    for caracterBase, caracterRecolectado in zip(valorBase, valorRecolectado):
        if (caracterBase == caracterRecolectado):
            porcentajeAcumulado += porcentajeUnidad

    porcentajeAcumulado = round(porcentajeAcumulado)

    return porcentajeAcumulado


def validarLadoDocumento(tipoDocumento: str, ladoDocumento: str, imagen:str):

    imagenData: list[str] = imagen.split(',')[1]

    decoded: bytes = base64.b64decode(imagenData)

    lerrImagen: Image = Image.open(BytesIO(decoded))

    txt: str = tess.image_to_string(lerrImagen)

    lineas: list[str] = txt.splitlines()


    infoHash = {
      "Cédula de ciudadanía": {
          "anverso": ["IDENTIFICACION PERSONAL", "CEDULA DE CIUDADANIA"],
          "reverso": ['FECHA Y LUGAR DE EXPEDICION', 'FECHA Y LUGAR', 'INDICE DERECHO', 'ESTATURA', 'FECHA DE NACIMIENTO']
      },
      "Cédula de extranjería": {
          "anverso": ["Cédula de Extranjeria", 'MIGRANTE'],
          "reverso": ["MIGRACION", "COLOMBIA", "www.migracioncolombia.gov.co"]
      }
    }

    ladoPalabras = infoHash[tipoDocumento][ladoDocumento]

    coincidencias = 0

    for linea in lineas:

        for palabra in ladoPalabras:

            if (linea.find(palabra) != -1):
                coincidencias = coincidencias + 1

    if (coincidencias >= 1):
        return True
    else:
        return False
