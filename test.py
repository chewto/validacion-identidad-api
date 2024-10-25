import subprocess
import os
import sys
import base64
from PIL import Image
from io import BytesIO
import json


def barcodeReader():
  folderBarcodes = './codigos-barras'
  folderExistance = os.path.exists(folderBarcodes)

  if(not folderExistance):
    os.makedirs(folderBarcodes)

  # header, encoded = photo.split(",",1)
  # data = base64.b64decode(encoded)
  # image = Image.open(BytesIO(data))
  # imagePath = f"{folderBarcodes}/{idBarcodecode}-{barcodeSide}.jpeg"
  # image.save(imagePath)

  exe = '../BarcodeReaderCLI/bin/BarcodeReaderCLI'
  args = []
  args.append(exe)
  args.append('../fotos-prueba/reversa mafe.jpg')
  process = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

  # barcodeExistance = os.path.exists(imagePath)
  # if(barcodeExistance):
  #   os.remove(imagePath)

  string = process.stdout.decode('utf-8')
  jsonProcess = json.loads(string)
  print(jsonProcess)
  sessionsExtracted = jsonProcess["sessions"][0]
  barcodesExtracted = sessionsExtracted["barcodes"]
  barcodesDetected = len(barcodesExtracted)

  return 'OK' if barcodesDetected >= 1 else '!OK'

barcodeReader()
