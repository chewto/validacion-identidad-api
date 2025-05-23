import random
import string
import time
from PIL import Image
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

def resizeImage(image, percentage):

  original_height, original_width = image.shape[:2]

  new_width = int(original_width * (percentage / 100.0))
  new_height = int(original_height * (percentage / 100.0))
  new_dimensions = (new_width, new_height)

  resized_image = cv2.resize(image, new_dimensions, interpolation=cv2.INTER_AREA)

  return resized_image


def resizeHandle(image, max_dimension=1200):
  original_height, original_width = image.shape[:2]

  if original_width > max_dimension or original_height > max_dimension:
    if original_width > original_height:
      new_width = max_dimension
      new_height = int((max_dimension / original_width) * original_height)
    else:
      new_height = max_dimension
      new_width = int((max_dimension / original_height) * original_width)
  else:
    new_width = original_width
    new_height = original_height

  new_dimensions = (new_width, new_height)
  resized_image = cv2.resize(image, new_dimensions, interpolation=cv2.INTER_AREA)

  return resized_image

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

def imageToDataURL(image):
  _, buffer = cv2.imencode('.jpg', image)
  image_base64 = base64.b64encode(buffer).decode('utf-8')
  dataURL = f"data:image/jpeg;base64,{image_base64}"
  return dataURL

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

def readDataUrlFrames(images:list):

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

  _, imagenEncode = cv2.imencode('.jpg',imagen)
  imagenBlob = imagenEncode.tobytes()

  return imagenBlob

def fileCv2(image):
  npArrayImage = np.frombuffer(image.read(), np.uint8)
  decodedImage = cv2.imdecode(npArrayImage, cv2.IMREAD_COLOR)
  return decodedImage

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


