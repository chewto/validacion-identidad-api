from PIL import Image
from io import BytesIO
import pytesseract as tess
import base64

tess.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def imagenOCR(imagen:str, tipoDocumento:str ,ladoDocumento:str):
  imagenData:list[str] = imagen.split(',')[1]
  decoded:bytes = base64.b64decode(imagenData)
  lerrImagen:Image = Image.open(BytesIO(decoded))

  txt:str = tess.image_to_string(lerrImagen)

  lineas:list[str] = txt.splitlines()

  palabrasClave = []

  letras = 'qwertyuiopasdfghjklzxcvbnm'

  for linea in lineas:
    lineaSinEspacios = linea.replace(' ','')
    lineaSinCaracteres = lineaSinEspacios.replace('-', '')
    lineaLower = lineaSinCaracteres.lower()


    lineaSinNumeros = ''

    for caracter in lineaLower:

      for letra in letras:
        if(caracter == letra):
          lineaSinNumeros += letra

    if(ladoDocumento == 'reverso' and tipoDocumento == 'Cédula de ciudadanía'):
      if('fecha' in lineaSinNumeros or 'lugar' in lineaSinNumeros or 'registrador' in lineaSinNumeros):
        palabrasClave.append(lineaSinNumeros)

    if(ladoDocumento == 'anverso' and tipoDocumento == 'Cédula de ciudadanía'):
      if('cedula' in lineaSinNumeros or 'republica' in lineaSinNumeros or 'identificacion' in lineaSinNumeros or 'colombia' in lineaSinNumeros):
        palabrasClave.append(lineaSinNumeros)
  
  return palabrasClave

def validarOCR(arrayTexto:list[str], tipoDocumento:str, ladoDocumento:str):

  print(arrayTexto)

  palabrasClave = {
    'Cédula de ciudadanía': {
      'anverso': ['republicadecolombia', 'identificacionpersonal', 'ceduladeciudadania'],
      'reverso': ['fechadenacimiento', 'lugardenacimiento', 'fechaylugardeexpedicion', 'registradornacional']
    }
  }

  palabras = palabrasClave[tipoDocumento][ladoDocumento]

  arrayOCR = arrayTexto

  porcentajeValidacion = 0

  for palabra, palabraClave in zip(arrayOCR, palabras):

    inicioPalabra = palabra.startswith(palabraClave)
    if(inicioPalabra == False):
      palabraIndex = palabra.find(palabraClave)
      palabra = palabra[palabraIndex:]


    porcentajePalabra = 0

    for letra, letraClave in zip(palabra, palabraClave):
      if(letra == letraClave):
        porcentajePalabra = porcentajePalabra + 1.5
        porcentajeValidacion = porcentajeValidacion + porcentajePalabra


  porcentajeValidacion = (porcentajeValidacion / 10)
  porcentajeValidacion = round(porcentajeValidacion)

  return porcentajeValidacion