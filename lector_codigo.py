import base64
from PIL import Image
from io import BytesIO
import json
import os
import subprocess
import cv2
import numpy as np
import re

from utilities.logs import checkLogsFile, writeLogs
from utilities.utilidades import readDataURL

countries = {
  'COL': {
    "Amazonas": "091",
    "Antioquia": "505",
    "Arauca": "807",
    "Atlántico": "808",
    "Bogotá, D.C.": "103",
    "Bolívar": "110",
    "Boyacá": "152",
    "Caldas": "172",
    "Caquetá": "182",
    "Casanare": "185",
    "Cauca": "190",
    "Cesar": "200",
    "Chocó": "227",
    "Córdoba": "223",
    "Cundinamarca": "225",
    "Guainía": "294",
    "Guaviare": "295",
    "Huila": "241",
    "La Guajira": "244",
    "Magdalena": "247",
    "Meta": "250",
    "Nariño": "252",
    "Norte de Santander": "254",
    "Putumayo": "286",
    "Quindío": "263",
    "Risaralda": "266",
    "Santander": "268",
    "San Andrés, Providencia y Santa Catalina": "288",
    "Sucre": "270",
    "Tolima": "273",
    "Valle del Cauca": "276",
    "Vaupés": "297",
    "Vichada": "299"
  }
}

countryKeys= {
  'COL': 'COLOMBIA'
}

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
  documentFormat = formatDefinition[documentType]

TBR_CODES = [103,125, 115, 118, 112, 109, 106,121 ]
# TBR_CODES = [103]

def ejecutar_lector(imagen_path, tbr_code, barcodeType):

  exe = './BarcodeReaderCLI/bin/BarcodeReaderCLI'

  cmd = [exe, f'-type={barcodeType}', f'-tbr={tbr_code}', '-fields=text,data,rectangle,rotation', imagen_path]
  proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  out = proc.stdout.decode('utf-8', errors='replace').strip()
  err = proc.stderr.decode('utf-8', errors='replace').strip()
  if proc.returncode != 0:
    return '!OK'
  return out

def barcodeReader(photo, idBarcodecode, barcodeSide, barcodeType, tbrList):

  folderBarcodes = './codigos-barras'
  folderExistance = os.path.exists(folderBarcodes)

  if not folderExistance:
    os.makedirs(folderBarcodes)

  imagePath = f"{folderBarcodes}/{idBarcodecode}-{barcodeSide}.jpeg"
  cv2.imwrite(imagePath, photo)

  barcodesExtracted = []

  found = False
  for tbr in tbrList:
    res = ejecutar_lector(imagePath, tbr, barcodeType)
    try:
      data = json.loads(res)
      sessions = data.get('sessions')
      if sessions and isinstance(sessions[0], dict):
        barcodes = sessions[0].get('barcodes')
        if barcodes:
          found = True
          barcodesExtracted = barcodes
          break
    except json.JSONDecodeError:
      pass
    if found:
      break

  barcodeExistance = os.path.exists(imagePath)
  if(barcodeExistance):
    os.remove(imagePath)

  return barcodesExtracted


def barcodereaderPath(imagePath, barcodeType):

    barcodesExtracted = []

    found = False
    for tbr in TBR_CODES:
        res = ejecutar_lector(imagePath, tbr, barcodeType)
        try:
            data = json.loads(res)
            sessions = data.get('sessions')
            if sessions and isinstance(sessions[0], dict):
                barcodes = sessions[0].get('barcodes')
                if barcodes:
                    found = True
                    barcodesExtracted = barcodes
                    break
        except json.JSONDecodeError:
            pass
        if found:
            break

    return barcodesExtracted


formatDefinition = {
    "CEDULA_CIUDADANIA": [
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
    "CEDULA_EXTRANJERIA": [
        ("estado", 12, 20),                # "MIGRANTE"
        ("numeroDocumento", 34, 52),        # "000000000000423105"
        ("apellido", 52, 82),              # "OTERO" + espacios
        ("segundoApellido", 82, 112),      # "CARREIRA" + espacios
        ("nombre", 112, 142),              # "BENITO" + espacios
        ("segundoNombre", 142, 172),       # Bloque de espacios vacíos
        ("fechaNacimiento", 192, 200),       # "21"
        ("genero", 200, 201),               # "M"
        # Campos adicionales detectados en tu cadena:
        ("fechaExpedicion", 201, 209),     # "20210802"
        ("fechaVencimiento", 209, 217),    # "20240729"
        ("tipoSangre", 217, 220),           # "A+ "
        ("nacionalidad", 220, 224)
    ]
}


def formatData(barcodes: list, documentType: str):
    if not barcodes:
        return []

    results = []

    for barcode in barcodes:
        raw_text = barcode.get('text', '')
        text = raw_text.replace("{NUL}", " ")

        definition = formatDefinition[documentType]

        parsed_item = {}

        for field in definition:
            nombre_campo = field[0]
            inicio = field[1]
            fin = field[2]

            valor = text[inicio:fin].strip()

            valor = valor.replace("|", "").strip()

            parsed_item[nombre_campo] = valor

        results.append(parsed_item)

    return results


def extractCountry(barcodes):

  for barcode in barcodes:
    if 'data' not in barcode:
      continue

    data = barcode['data']

    try:
      decoded_data = base64.b64decode(data).decode('utf-8', errors='ignore')
      departmentCode = decoded_data[162:165]
      countryCode, country, countryCheck = searchDep(departmentCode, 'COL')
      return countryCode, country, countryCheck

    except Exception as e:
      print(f"Error decoding barcode data: {e}")
      return 'no detectado', 'no detectado', '!OK'

  return 'no detectado', 'no detectado', '!OK'

def searchDep(code, country):

  depData = countries[country]

  for depInfo, depCode in depData.items():
    if(code == depCode):
      countryKey = countryKeys[country]
      return country, countryKey, 'OK'

  return 'no detectado','no detectado', '!OK'

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
