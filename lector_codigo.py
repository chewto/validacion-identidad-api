import base64
import Levenshtein
from PIL import Image
import io
from aspose.barcode import barcoderecognition
from ocr import extraerPorcentaje
from utilidades import generate_unique_code, ordenamiento
import cv2
import os

def lectorCodigoBarras(documentoData:str, tipoDocumento):
  image_data = base64.b64decode(documentoData.split(',')[1])

  directorio = './codigos-barras'

  nombreImagen = generate_unique_code()
  nombreImagen = f'{nombreImagen}.png'

  with open(f'{directorio}/{nombreImagen}', 'wb') as file:
    file.write(image_data)

  result = []

  tipoCodigo = ''

  if(tipoDocumento == 'Cédula de extranjería'):
    if os.path.exists(f'{directorio}/{nombreImagen}'):
        os.remove(f'{directorio}/{nombreImagen}')
        print( f"The file '{nombreImagen}' has been successfully deleted.")
    else:
        print( f"The file '{nombreImagen}' does not exist.")

    return {
      "codigoAFIS": '',
      "huella": '',
      "numeroDocumento": '',
      "primerNombre": '',
      "segundoNombre": '',
      "primerApellido": '',
      "segundoApellido": '',
      "genero": '',
      "anhoNacimiento": '',
      "mesNacimiento": '',
      "diaNacimiento": '',
      "codigoMunicipio": '',
      "codigoDepartamento": '',
      "tipoSangre": ''
  }
  if(tipoDocumento == 'Cédula de ciudadanía'):
    tipoCodigo = barcoderecognition.DecodeType.PDF417

  reader = barcoderecognition.BarCodeReader(f'{directorio}/{nombreImagen}', tipoCodigo )
  recognized_results = reader.read_bar_codes()
  for barcode in recognized_results:
      print(barcode.code_text)
      result.append(barcode.code_text)

  if os.path.exists(f'{directorio}/{nombreImagen}'):
        os.remove(f'{directorio}/{nombreImagen}')
        print( f"The file '{nombreImagen}' has been successfully deleted.")
  else:
        print( f"The file '{nombreImagen}' does not exist.")


  diccionarioData = organizacionData(result)

  return diccionarioData


def organizacionData(data):

  if(len(data) <= 0):
    return False

  barcodeData = data[0]

  codigoAFIS = barcodeData[2:10]

  huella = barcodeData[40:48]

  numeroDocumento = barcodeData[48:58]

  primerNombre = barcodeData[104:127]
  segundoNombre = barcodeData[127:150]

  primerApellido = barcodeData[58:80]
  segundoApellido = barcodeData[81:104]

  genero = barcodeData[151:152]

  anhoNacimiento = barcodeData[152:156]
  mesNacimiento = barcodeData[156:158]
  diaNacimiento = barcodeData[158:160]

  codigoMunicipio = barcodeData[160:162]
  codigoDepartamento = barcodeData[162:165]
  tipoSangre = barcodeData[166:168]

  return {
      "codigoAFIS": codigoAFIS,
      "huella": huella,
      "numeroDocumento": numeroDocumento,
      "primerNombre": primerNombre,
      "segundoNombre": segundoNombre,
      "primerApellido": primerApellido,
      "segundoApellido": segundoApellido,
      "genero": genero,
      "anhoNacimiento": anhoNacimiento,
      "mesNacimiento": mesNacimiento,
      "diaNacimiento": diaNacimiento,
      "codigoMunicipio": codigoMunicipio,
      "codigoDepartamento": codigoDepartamento,
      "tipoSangre": tipoSangre
  }

def validarDataCodigo(firmadorData:str, codigoBarrasData:str):

  firmadorInfoSplit = firmadorData.split(' ')
  codigoBarrasDataSplit = codigoBarrasData.split(' ')

  cantidadComparacion = len(firmadorInfoSplit)

  conseguidos = 0

  for infoFirmador in firmadorInfoSplit:
    for infoCodigoBarra in codigoBarrasDataSplit:
      infoCodigoBarra = infoCodigoBarra[0:len(infoFirmador)]
      if(infoFirmador.find(infoCodigoBarra) != -1):
        conseguidos = conseguidos + 1


  if(conseguidos >= cantidadComparacion):
    return 'true'
  else:
    return 'false'