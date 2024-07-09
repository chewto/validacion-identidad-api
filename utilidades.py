import random
import string
import uuid
import cv2
import numpy as np
import base64
import unicodedata

def textNormalize(texto:str):
  texto = texto.strip()
  textoNormalizado = unicodedata.normalize('NFD', texto)
  sinAcentos  = ''.join(c for c in textoNormalizado if unicodedata.category(c) != 'Mn')
  return sinAcentos

def readDataURL(imagen):

  if(len(imagen) <= 0):
    return ''

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