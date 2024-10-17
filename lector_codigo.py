import base64
from PIL import Image
from io import BytesIO
import json
import os
import subprocess


country = 'HND'

barcodes = {
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


def hasBarcode(documentType, documentSide):
  barcode = barcodes[country][documentType][documentSide]
  return barcode

def barcodeReader(photo, idBarcodecode, barcodeSide):
  folderBarcodes = './codigos-barras'
  folderExistance = os.path.exists(folderBarcodes)

  if(not folderExistance):
    os.makedirs(folderBarcodes)

  header, encoded = photo.split(",",1)
  data = base64.b64decode(encoded)
  image = Image.open(BytesIO(data))
  imagePath = f"{folderBarcodes}/{idBarcodecode}-{barcodeSide}.jpeg"
  image.save(imagePath)

  exe = '../BarcodeReaderCLI/bin/BarcodeReaderCLI'
  args = []
  args.append(exe)
  args.append(imagePath)
  process = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

  barcodeExistance = os.path.exists(imagePath)
  if(barcodeExistance):
    os.remove(imagePath)

  string = process.stdout.decode('utf-8')
  jsonProcess = json.loads(string)
  sessionsExtracted = jsonProcess["sessions"][0]
  barcodesExtracted = sessionsExtracted["barcodes"]
  barcodesDetected = len(barcodesExtracted)

  return True if barcodesDetected >= 1 else False