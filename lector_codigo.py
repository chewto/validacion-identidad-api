import base64
from PIL import Image
from io import BytesIO
import json
import os
import subprocess


country = 'HND'

barcodes = {
  "COL": {
            "Cédula de ciudadanía": {
                "anverso": False,
                "reverso": True
            },
            "Cédula de extranjería": {
                "anverso": False,
                "reverso": True
            },
            "Permiso por protección temporal": {
                "anverso": False,
                "reverso": False
            },
            "Pasaporte":{
                "anverso":False,
                "reverso":False
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
      "reverso": True
    },
    "Carnet de residente": {
      "anverso": False,
      "reverso": True
    },
    "Pasaporte": {
      "anverso": True,
      "reverso": False
    }
  }
}


def barcodeSide(documentType, documentSide):
  barcode = barcodes[country][documentType][documentSide]
  return barcode

def hasBarcode(documentType):

  barcodeDocumentType = barcodes[country][documentType]

  sideData = []

  for key,value in barcodeDocumentType.items():
    sideData.append(value)

  totalBarcode = any(sideData)

  return totalBarcode


def barcodeReader(photo, idBarcodecode, barcodeSide):
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
  args.append(imagePath)
  # process = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

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
  print(string)
  jsonProcess = json.loads(string)
  sessionsExtracted = jsonProcess["sessions"][0]
  barcodesExtracted = sessionsExtracted["barcodes"]
  barcodesDetected = len(barcodesExtracted)

  return 'OK' if barcodesDetected >= 1 else '!OK'