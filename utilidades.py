import random
import string
import uuid
import cv2
import numpy as np
import base64
import unicodedata
import re
from difflib import SequenceMatcher

browserPatterns = {
    "Chrome": r"Chrome\/([\d\.]+)",
    "Firefox": r"Firefox\/([\d\.]+)",
    "Safari": r"Version\/([\d\.]+).*Safari",
    "Edge": r"Edg\/([\d\.]+)",
    "Opera": r"OPR\/([\d\.]+)"
}

def listToText(list):
  string = ''
  
  for element in list:
    string += element

  return string

def getBrowser(userAgent):
    for browser, pattern in browserPatterns.items():
        match = re.search(pattern, userAgent)
        if match:
            return f"{browser} {match.group(1)}"
    return "navegador desconocido"

def extraerPorcentaje(valor1, valor2):
    radio = SequenceMatcher(None, valor1, valor2).ratio()
    porcentaje = radio * 100
    porcentaje = int(porcentaje)
    return porcentaje

def textNormalize(texto:str):
  texto = texto.strip()
  textoNormalizado = unicodedata.normalize('NFD', texto)
  sinAcentos  = ''.join(c for c in textoNormalizado if unicodedata.category(c) != 'Mn')
  toUpper = sinAcentos.upper()
  return toUpper

def readDataURL(imagen):

  if(len(imagen) <= 0):
    with open('./assets/img/placeholder.jpeg', "rb") as image_file: 
      encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
      imagen =  f"data:image/jpeg;base64,{encoded_string}"

  imagenURL = imagen

  imagenData = base64.b64decode(imagenURL.split(",")[1])

  npArray = np.frombuffer(imagenData, np.uint8)

  imagen = cv2.imdecode(npArray, cv2.IMREAD_COLOR)

  return imagen

def ordenamiento(data):

    listaOrdenada = sorted(data, key= lambda x:x['similitud'])

    return listaOrdenada


def cv2Blob(imagen):

  height, width = imagen.shape[:2]
  resizedImage = cv2.resize(imagen, (width // 2, height // 2))
  compressionParams = [cv2.IMWRITE_JPEG_QUALITY, 50]
  _, imagenEncode = cv2.imencode('.jpg',resizedImage, compressionParams)
  imagenBlob = imagenEncode.tobytes()

  return imagenBlob

def recorteData(data):
  if(len(data)>= 499):
    nueva = data[0:498]
    return nueva
  
  if(len(data) <= 498):
    return data
  
def generate_unique_code():
    unique_id = str(uuid.uuid4()).split('-')[-1]  # Generate a unique identifier and extract a portion
    random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))  # Generate 6 random characters
    unique_code = unique_id + random_chars  # Combine the unique identifier and random characters
    return unique_code


def stringBool(string):
  if(string == 'true'):
      return True
  if(string == 'false'):
      return False


def leerFileStorage(archivo):

  with open(archivo, 'rb') as archivoOpen:
    data = archivoOpen.read()
  return data
