from PIL import Image
from io import BytesIO
import pytesseract as tess
import base64

tess.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def imagenOCR(imagen:str, nombre:str, apellido:str, numeroDocumento:str):
  
  nombre = nombre.upper()
  apellido = apellido.upper()

  imagenData:list[str] = imagen.split(',')[1]
  decoded:bytes = base64.b64decode(imagenData)
  lerrImagen:Image = Image.open(BytesIO(decoded))

  txt:str = tess.image_to_string(lerrImagen)

  lineas:list[str] = txt.splitlines()

  informacionOCR = {}

  letras = 'qwertyuiopasdfghjklzxcvbnm'
  numeros = '1234567890'

  for linea in lineas:

    linea = linea.upper()
    linea = linea.strip()

    print(linea)

    lineaLimpia = ''

    for caracter in linea:
      for numero in numeros:
        if(caracter == numero):
          lineaLimpia +=  caracter

    if(linea.find(nombre) != -1):
      informacionOCR['nombre'] = linea

    
    if(linea.find(apellido) != -1):
      informacionOCR['apellido'] = linea


    if(lineaLimpia.find(numeroDocumento) != -1):
      informacionOCR['numeroDocumento'] = lineaLimpia

  return informacionOCR


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