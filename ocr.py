from PIL import Image
from io import BytesIO
import pytesseract as tess
import base64

tess.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def imagenOCR(imagen:str, nombre:str, apellido:str, numeroDocumento:str):

    imagenData: list[str] = imagen.split(',')[1]

    decoded: bytes = base64.b64decode(imagenData)

    lerrImagen: Image = Image.open(BytesIO(decoded))

    txt: str = tess.image_to_string(lerrImagen)

    lineas: list[str] = txt.splitlines()

    informacionOCR = {}

    numeros = '1234567890'

    for linea in lineas:

        linea = linea.upper()
        linea = linea.strip()

        lineaLimpia = ''

        for caracter in linea:
            for numero in numeros:
                if (caracter == numero):
                    lineaLimpia += caracter

        if (linea.find(nombre) != -1):
            nombreLimpio = limpiarData(linea, nombre)

            informacionOCR['nombre'] = nombreLimpio

        if (linea.find(apellido) != -1):
            apellidoLimpio = limpiarData(linea, apellido)

            print(apellidoLimpio)

            informacionOCR['apellido'] = apellidoLimpio

        if (lineaLimpia.find(numeroDocumento) != -1):
            informacionOCR['numeroDocumento'] = lineaLimpia

    return informacionOCR


def limpiarData(dataSinLimpiar: str, dataBase: str):

    dataArray = dataSinLimpiar.split(' ')

    dataBaseArray = dataBase.split(' ')

    dataLimpiaArr = []


    if (len(dataBaseArray) >= 2):

        for data, dataComparacion in zip(dataArray, dataBaseArray):
            if (data == dataComparacion):
                dataLimpiaArr.append(dataComparacion)

    if (len(dataBaseArray) <= 1):
        a = dataBaseArray[0]

        for data in dataArray:
            if (data == a):
                dataLimpiaArr.append(a)

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

  if('nombre' in infoDocumento):
    nombreOCR = infoDocumento['nombre']
    coincidenciaNombre += porcetajeNombres(nombreParam, nombreOCR)

  if('apellido' in infoDocumento):
    apellidoOCR = infoDocumento['apellido']
    coincidenciaApellido += porcetajeNombres(apellidoParam, apellidoOCR)


  if('numeroDocumento' in infoDocumento):
    numeroDocumentoOCR = infoDocumento['numeroDocumento']
    coincidenciaDocumento += porcentajeDocumento(numeroDocumentoParam, numeroDocumentoOCR)

  return coincidenciaNombre, coincidenciaApellido, coincidenciaDocumento

def porcetajeNombres(valorBase:str, valorRecolectado:str):

  validacionMaxima = 100

  porcentajeUnidad = validacionMaxima/len(valorBase)

  porcentajeAcumulado = 0

  for caracter, caracterComparar in zip(valorBase, valorRecolectado):
    print(caracter, caracterComparar)
    if(caracter == caracterComparar):
      porcentajeAcumulado += porcentajeUnidad
      print(porcentajeAcumulado)
  
  porcentajeAcumulado = round(porcentajeAcumulado)

  return porcentajeAcumulado

def porcentajeDocumento(valorBase:str, valorRecolectado:str):

  validacionMaxima = 100

  porcentajeUnidad = validacionMaxima / len(valorBase)

  porcentajeAcumulado = 0

  for caracterBase, caracterRecolectado in zip(valorBase, valorRecolectado):
    if(caracterBase == caracterRecolectado):
      porcentajeAcumulado += porcentajeUnidad

  porcentajeAcumulado = round(porcentajeAcumulado)

  return porcentajeAcumulado