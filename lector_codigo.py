import base64
from PIL import Image
from io import BytesIO
import json
import os
import subprocess
import cv2
import numpy as np

from logs import checkLogsFile, writeLogs
from utilidades import readDataURL

country = 'HND'

barcodes = {
  "COL": {
            "Cédula de ciudadanía": {
                "anverso": [False,'none'],
                "reverso": [True, 'pdf417']
            },
            "Cédula de extranjería": {
                "anverso": [False,'none'],
                "reverso": [True, 'pdf417']
            },
            "Permiso por protección temporal": {
                "anverso": [False,'none'],
                "reverso": [False, 'none']
            },
            "Pasaporte":{
                "anverso": [False,'none'],
                "reverso": [False, 'none']
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
      "anverso": [False,'none'],
      "reverso": [True, 'qr']
    },
    "Carnet de residente": {
      "anverso": False,
      "reverso": True
    },
    "Pasaporte": {
      "anverso": [True,'pdf417'],
      "reverso": [False, 'none']
    }
  }
}


def barcodeSide(documentType, documentSide):
  hasBarcode, barcodeType = barcodes[country][documentType][documentSide]
  return hasBarcode, barcodeType

def hasBarcode(documentType):

  barcodeDocumentType = barcodes[country][documentType]

  sideData = []

  for key,value in barcodeDocumentType.items():
    sideData.append(value)

  totalBarcode = any(sideData)

  return totalBarcode


def barcodeReader(photo, idBarcodecode, barcodeSide, barcodeType):
  folderBarcodes = './codigos-barras'
  folderExistance = os.path.exists(folderBarcodes)

  if not folderExistance:
    os.makedirs(folderBarcodes)

  gray = cv2.cvtColor(photo, cv2.COLOR_BGR2GRAY)

  imagePath = f"{folderBarcodes}/{idBarcodecode}-{barcodeSide}.jpeg"
  cv2.imwrite(imagePath, gray)

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
  
  return barcodesExtracted



def rotateBarcode(image, barcodes):

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