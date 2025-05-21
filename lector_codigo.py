import base64
from PIL import Image
from io import BytesIO
import json
import os
import subprocess
import cv2
import numpy as np
import re

from logs import checkLogsFile, writeLogs
from utilidades import readDataURL

barcodes = {
  "COL": {
            "Cédula de ciudadanía": {
                "anverso": [False,'none', ''],
                "reverso": [True, 'pdf417','112']
            },
            "Cédula de extranjería": {
                "anverso": [False,'none', ''],
                "reverso": [True, 'pdf417','123']
            },
            "Permiso por protección temporal": {
                "anverso": [False,'none', ''],
                "reverso": [False, 'none', '']
            },
            "Pasaporte":{
                "anverso": [False,'none', ''],
                "reverso": [False, 'none', '']
            },
            "Cédula digital": {
               "anverso": [False, 'none', ''],
               "reverso": [True, 'datamatrix', '100']
            }
        },
        "PTY":{
            "Cédula de ciudadanía": {
                "anverso": [False,'none', ''],
                "reverso": [True, 'none', '']
            },
            "Cédula de extranjería": {
                "anverso": [False,'none', ''],
                "reverso": [False,'none', '']
            }
        },
  'HND': {
    "DNI":{
      "anverso": [False,'none', ''],
      "reverso": [True, 'qr', '116']
    },
    "Carnet de residente": {
      "anverso": [False, 'none', ''],
      "reverso": [True, 'none', ''],
    },
    "Pasaporte": {
      "anverso": [True,'pdf417', '107'],
      "reverso": [False, 'none' , '']
    }
  },
  'SLV': {
    "DNI":{
      "anverso": [False,'none', ''],
      "reverso": [True, 'pdf417', '107']
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


def barcodeSide(documentType, documentSide, barcodeData):
  hasBarcode, barcodeType, tbr = barcodeData[documentType][documentSide]
  return hasBarcode, barcodeType, tbr

def hasBarcode(documentType, barcodeData):

  barcodeDocumentType = barcodeData[documentType]

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

def barcodeReader(photo, idBarcodecode, barcodeSide, barcodeType, tbr):
  folderBarcodes = './codigos-barras'
  folderExistance = os.path.exists(folderBarcodes)

  if not folderExistance:
    os.makedirs(folderBarcodes)

  imagePath = f"{folderBarcodes}/{idBarcodecode}-{barcodeSide}.jpeg"
  cv2.imwrite(imagePath, photo)

  exe = '../BarcodeReaderCLI/bin/BarcodeReaderCLI'

  args = []
  args.append(exe)
  args.append(f'-type={barcodeType}')
  # args.append('-type=pdf417,qr,datamatrix,code39,code128,codabar,ucc128,code93,upca,ean8,upce,ean13,i25,imb,bpo,aust,sing')
  args.append('-tbr=112,115,117')
  args.append('-fields=text,data,rectangle,rotation')
  args.append(imagePath)

  try:
        process = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        process.check_returncode()
  except subprocess.CalledProcessError as e:
        print(e)
        print('no es detectaron')
        return '!OK'
  except PermissionError as e:
        print('error de permisos')
        return '!OK'

  barcodeExistance = os.path.exists(imagePath)
  if(barcodeExistance):
    os.remove(imagePath)

  string = process.stdout.decode('utf-8')
  jsonProcess = json.loads(string)

  sessionsExtracted = jsonProcess["sessions"][0]
  barcodesExtracted = sessionsExtracted["barcodes"]

  return barcodesExtracted



def rotateBarcode(image, barcodes):

  if(barcodes == '!OK'):
    return image

  if(len(barcodes) <= 0):
    return image

  left = 0
  right = 0
  upside = 0

  for barcode in barcodes:

    side = barcode['rotation']

    if(side == 'left'):
      left = 1
    if(side == 'right'):
      right = 1
    if(side == 'upside'):
      upside = 1

  rotatedImage = image

  if(left >= 1):
    rotatedImage = cv2.rotate(rotatedImage, cv2.ROTATE_90_CLOCKWISE)

  if(right >= 1):
    rotatedImage = cv2.rotate(rotatedImage, cv2.ROTATE_90_COUNTERCLOCKWISE)

  if(upside >= 1):
    rotatedImage = cv2.rotate(rotatedImage, cv2.ROTATE_180)

  return rotatedImage
