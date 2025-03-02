import base64
from PIL import Image
from io import BytesIO
import json
import os
import subprocess
import cv2
import numpy as np
import re

country = 'COL'

barcodes = {
  "COL": {
            "Cédula de ciudadanía": {
                "anverso": False,
                "reverso": True,
                "cifrado": False,
                "type": 'pdf417'
            },
            "Cédula de extranjería": {
                "anverso": False,
                "reverso": True,
                "cifrado": False,
                "type": 'pdf417'
            },
            "Permiso por protección temporal": {
                "anverso": False,
                "reverso": False
            },
            "Pasaporte":{
                "anverso":False,
                "reverso":False,
                "cifrado": False,
                "type": ''
            }
        },
        "PTY":{
            "Cédula de ciudadanía": {
                "anverso": False,
                "reverso": True
            },
            "Cédula de extranjería": {
                "anverso": False,
                "reverso": True
            }
        },
  'HND': {
    "DNI":{
      "anverso": False,
      "reverso": True,
      "cifrado": False,
      "type": 'qr,datamatrix'
    },
    "Carnet de residente": {
      "anverso": False,
      "reverso": True,
      "cifrado": True
    },
    "Pasaporte": {
      "anverso": True,
      "reverso": False,
      "cifrado": False,
      "type": 'pdf417'
    }
  }
}

formatDefinition = {
    "Cédula de ciudadanía": [
        ("codigoAfis", 2, 10),
        ("fingerCard", 40, 48),
        ("numeroDocumento", 48, 58),
        ("apellido", 58, 80),
        ("segundaApellido", 81, 104),
        ("nombre", 104, 127),
        ("segundoNombre", 127, 150),
        ("genero", 151, 152),
        ("añoNacimeinto", 152, 156),
        ("mesNacimiento", 156, 158),
        ("diaNacimiento", 158, 160),
        ("codigoMunicipalidad", 160, 162),
        ("codigoDepartamento", 162, 165),
        ("tipoSangre", 166, 168)
    ],
    "Cédula de extranjería": [
        ("estado", 10, ),
        ("fingerCard", 40, 48),
        ("numeroDocumento", 28, 58),
        ("apellido", 58, 80),
        ("segundaApellido", 81, 104),
        ("nombre", 104, 127),
        ("segundoNombre", 127, 150),
        ("genero", 151, 152),
        ("añoNacimeinto", 152, 156),
        ("mesNacimiento", 156, 158),
        ("diaNacimiento", 158, 160),
        ("codigoMunicipalidad", 160, 162),
        ("codigoDepartamento", 162, 165),
        ("tipoSangre", 166, 168)
    ]
}


def barcodeSide(documentType, documentSide):
  barcode = barcodes[country][documentType][documentSide]
  isCrypted = barcodes[country][documentType]['cifrado']
  barcodeType = barcodes[country][documentType]['type']
  return barcode, isCrypted, barcodeType

def hasBarcode(documentType):

  barcodeDocumentType = barcodes[country][documentType]

  sideData = []

  for key,value in barcodeDocumentType.items():
    sideData.append(value)

  totalBarcode = any(sideData)

  return totalBarcode

def extractBarcodeData(barcodeData, documentType):
  barcodeBytes = base64.b64decode(barcodeData)
  barcodeString = barcodeBytes.decode('utf-8', errors='ignore')
  print(barcodeString)
  documentFormat = formatDefinition[documentType]

  barcodeData ={}

  for field in documentFormat:

    fieldName, start, end = field
    data = barcodeString[start:end]
    if('\x00' in data):
      data = data.replace('\x00', '')
    barcodeData[fieldName] = data

  return barcodeData

def barcodeReader(photo, idBarcodecode, barcodeSide, isCrypted, barcodeType, documentType):
  folderBarcodes = './codigos-barras'
  folderExistance = os.path.exists(folderBarcodes)

  if(not folderExistance):
    os.makedirs(folderBarcodes)

  header, encoded = photo.split(",",1)
  data = base64.b64decode(encoded)
  image = Image.open(BytesIO(data))
  image = image.convert('RGB')

  imagePath = f"{folderBarcodes}/{idBarcodecode}-{barcodeSide}.jpeg"

  image.save(imagePath)

  exe = '../BarcodeReaderCLI/bin/BarcodeReaderCLI'

  args = []
  args.append(exe)
  args.append(f'-type={barcodeType}')
  # args.append('-type=pdf417,qr,datamatrix,code39,code128,codabar,ucc128,code93,upca,ean8,upce,ean13,i25,imb,bpo,aust,sing')
  args.append('-tbr=112,115,117')
  args.append(imagePath)

  try:
        process = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        process.check_returncode()
  except subprocess.CalledProcessError as e:
        return '!OK'
  except PermissionError as e:
        return '!OK'

  barcodeExistance = os.path.exists(imagePath)
  if(barcodeExistance):
    os.remove(imagePath)

  string = process.stdout.decode('utf-8')
  jsonProcess = json.loads(string)
  sessionsExtracted = jsonProcess["sessions"][0]
  barcodesExtracted = sessionsExtracted["barcodes"]

  if(not isCrypted):
    filteredBarcodes = list(filter(lambda barcode: barcode['type'] == barcodeType, barcodesExtracted))
    if(len(filteredBarcodes) >= 1):
      barcodeData = filteredBarcodes[0]['data']
      print(barcodeData)
      extractedData = extractBarcodeData(barcodeData, documentType)
      return 'OK', extractedData
    else:
      return '!OK', None

  barcodesDetected = len(barcodesExtracted)

  return 'OK', None if barcodesDetected >= 1 else '!OK', None
