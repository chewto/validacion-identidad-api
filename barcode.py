import base64
import Levenshtein
from PIL import Image
import io
import re
import requests
from ocr import extraerPorcentaje
from utilidades import generate_unique_code, ordenamiento
import cv2
import os

baseURL = "https://api.pdf.co/v1"
apiKEY = "thierryarsenalhenry@yopmail.com_xBF2tLZ4Q1CRQbMtX8BOAXLFLnqFZ6iy66lWvQrRIGUBHVvNOCCqCibQlFyAwQRY"
barcodeTypes = "PDF417,Code128"
pages = ""

def uploadBarcodeFile(documentDataUrl, fileName):

  url = f"{baseURL}/file/upload/get-presigned-url?contenttype=application/octet-stream&name={fileName}"

  response = requests.get(url, headers={"x-api-key": apiKEY})
  if(response.status_code == 200):
    json = response.json()

    if json["error"] == False:
      uploadUrl = json['presignedUrl']
      uploadFileUrl = json['url']

      binaryData = base64.b64decode(documentDataUrl.split(",")[1])

      bytesIO = io.BytesIO(binaryData)

      bufferedReader = io.BufferedReader(bytesIO)

      requests.put(uploadUrl, data=bufferedReader, headers={ "x-api-key": apiKEY, "content-type": "application/octet-stream" })

      return uploadFileUrl
    else:
      print(json["message"])
      return None

  else:
    print(f"Request Error: {response.reason}")

  return None

def readBarcode(uploadedFileUrl):

  parameters = {}
  parameters["types"] = barcodeTypes
  parameters["pages"] = pages
  parameters["url"] = uploadedFileUrl

  url = f"{baseURL}/barcode/read/from/url"

  response = requests.post(url, data=parameters, headers={"x-api-key": apiKEY})

  if(response.status_code == 200):
    json = response.json()

    if json["error"] == False:

      for barcode in json["barcodes"]:
        return barcode["Value"]
    else:
      print(json["message"])
  else:
    print(f"Request error: {response.status_code} {response.reason}")



def validateBarcode(documentDataUrl, fileName):

  return ''

  # uploadedFile = uploadFile(documentDataUrl, fileName)

  # print(uploadedFile)


  # return {
  #     "codigoAFIS": '',
  #     "huella": '',
  #     "numeroDocumento": '',
  #     "primerNombre": '',
  #     "segundoNombre": '',
  #     "primerApellido": '',
  #     "segundoApellido": '',
  #     "genero": '',
  #     "anhoNacimiento": '',
  #     "mesNacimiento": '',
  #     "diaNacimiento": '',
  #     "codigoMunicipio": '',
  #     "codigoDepartamento": '',
  #     "tipoSangre": ''
  # }

  # diccionarioData = organizacionData(result)

  # return diccionarioData

def barcodeDTO(barcodeData):

  if(len(barcodeData) <= 0):
    return ''

  codigoAFIS = barcodeData[2:10]

  huella = barcodeData[40:48]

  numeroDocumento = barcodeData[48:58]

  primerNombre = deleteUselessChar(barcodeData[104:127])
  segundoNombre = deleteUselessChar(barcodeData[127:150])

  primerApellido = deleteUselessChar(barcodeData[58:80])
  segundoApellido = deleteUselessChar(barcodeData[81:104])

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

def deleteUselessChar(text):
  
  newText = re.sub(r'[^\x20-\x7E]', '', text)

  return newText


def isValid(value1, value2):

  if(value1 in value2):
    return True
  else:
    return False

def validarDataCodigo(firmadorData, codigoBarrasData:str):

  return ''
  # codigoBarrasDataSplit = codigoBarrasData.split(' ')

  # cantidadComparacion = len(firmadorInfoSplit)

  # conseguidos = 0

  # for infoFirmador in firmadorInfoSplit:
  #   for infoCodigoBarra in codigoBarrasDataSplit:
  #     infoCodigoBarra = infoCodigoBarra[0:len(infoFirmador)]
  #     if(infoFirmador.find(infoCodigoBarra) != -1):
  #       conseguidos = conseguidos + 1


  # if(conseguidos >= cantidadComparacion):
  #   return 'ok'
  # else:
  #   return '!ok'