import os
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

def removeAccents(text):
  """
  Elimina acentos y convierte el texto a mayúsculas.
  """
  text = unicodedata.normalize('NFD', text)
  text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
  return text.upper()

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
    """Convierte una data URL base64 a una imagen OpenCV.
    Si `imagen` es None o está vacía, se carga una imagen placeholder.
    """
    # Si la entrada es None o una cadena vacía, usar placeholder
    if not imagen or len(imagen) <= 0:
        print(imagen, "imagen")
        placeholder_path = './assets/img/placeholder.jpeg'
        try:
            with open(placeholder_path, "rb") as image_file:
                
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                imagen = f"data:image/jpeg;base64,{encoded_string}"
        except Exception as e:
            # Si no se puede cargar el placeholder, lanzar un error claro
            raise FileNotFoundError(f"Placeholder image not found at {placeholder_path}: {e}")

    # Extraer los datos base64 después de la coma
    try:
        imagenData = base64.b64decode(imagen.split(",")[1])
    except Exception as e:
        raise ValueError(f"Invalid data URL format: {e}")

    # Convertir a numpy array y decodificar con OpenCV
    npArray = np.frombuffer(imagenData, np.uint8)
    img = cv2.imdecode(npArray, cv2.IMREAD_COLOR)
    return img

# def readDataUrlFrames(images:list):

#   if(len(imagen) <= 0):
#     with open('./assets/img/placeholder.jpeg', "rb") as image_file: 
#       encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
#       imagen =  f"data:image/jpeg;base64,{encoded_string}"

#   imagenURL = imagen

#   imagenData = base64.b64decode(imagenURL.split(",")[1])

#   npArray = np.frombuffer(imagenData, np.uint8)

#   imagen = cv2.imdecode(npArray, cv2.IMREAD_COLOR)

#   return imagen

def rotateImage(image, angle):
  
    
    if isinstance(angle, str):
      try:
        angle = int(angle)
      except ValueError:
        return image
    """
    Rota la imagen según el ángulo proporcionado (90, 180, 270 grados antihorario).
    """
    if angle == 90:
      return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
    elif angle == 180:
      return cv2.rotate(image, cv2.ROTATE_180)
    elif angle == 270:
      return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    else:
      # Si el ángulo no es válido, retorna la imagen original
      return image

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


def orientation(image):
  height, width = image.shape[:2]
  if height > width:
    # Rotate the image 90 degrees to make it horizontal
    rotated = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    return rotated
  
  return image


def sanitizeFileName(value):
  """
  Reduce un valor a un segmento de ruta seguro.
  Las etiquetas provienen de pais.yolo_labels en base de datos, por lo que un
  '/' o un '..' allowrian escribir fuera del directorio de recortes.
  """
  cleaned = re.sub(r'[^A-Za-z0-9_-]', '_', str(value))
  return cleaned.strip('_') or 'desconocido'


def saveYoloCrops(image, recortes, country, signerId, side, outputDir, padding=0.0):
  """
  Recorta y persiste en disco las regiones de interes detectadas por YOLO.

  Args:
    image: ndarray BGR de la imagen ORIGINAL sobre la que se detectaron los
      bounding boxes. Debe ser la imagen completa, no un recorte previo.
    recortes: lista con el contrato de POST /document/detection, es decir
      [{"etiqueta": str, "recorte": {"left","right","top","bottom"}}, ...]
    country: codigo de pais (COL, HND) usado como primer nivel de la ruta.
    signerId: id del firmador usado como segundo nivel de la ruta.
    side: 'front' o 'back', se antepone al nombre del archivo.
    outputDir: raiz de almacenamiento.
    padding: margen proporcional alrededor del bbox para no cortar bordes.
  Returns:
    list[str]: rutas de los archivos escritos.
  """
  if image is None:
    return []

  savedPaths = []
  height, width = image.shape[:2]
  targetDir = os.path.join(outputDir, sanitizeFileName(country), sanitizeFileName(signerId))
  # YOLO puede devolver la misma etiqueta mas de una vez en una imagen. El contador
  # se reinicia en cada llamada, de forma que reprocesar el mismo firmador
  # sobreescribe los archivos en vez de acumular sufijos de ejecuciones anteriores.
  labelCounters = {}

  for item in recortes or []:
    label = sanitizeFileName(item.get('etiqueta', 'desconocido'))
    box = item.get('recorte') or {}

    x1 = int(box.get('left', 0))
    y1 = int(box.get('top', 0))
    x2 = int(box.get('right', 0))
    y2 = int(box.get('bottom', 0))

    boxWidth = x2 - x1
    boxHeight = y2 - y1

    if boxWidth <= 0 or boxHeight <= 0:
      continue

    if padding > 0:
      padX = int(boxWidth * padding)
      padY = int(boxHeight * padding)
      x1 -= padX
      y1 -= padY
      x2 += padX
      y2 += padY

    x1 = max(0, x1)
    y1 = max(0, y1)
    x2 = min(width, x2)
    y2 = min(height, y2)

    if x2 <= x1 or y2 <= y1:
      continue

    crop = image[y1:y2, x1:x2]

    if crop.size == 0:
      continue

    os.makedirs(targetDir, exist_ok=True)

    labelCounters[label] = labelCounters.get(label, 0) + 1
    occurrence = labelCounters[label]
    fileName = f"{sanitizeFileName(side)}_{label}.jpg"
    if occurrence > 1:
      fileName = f"{sanitizeFileName(side)}_{label}_{occurrence}.jpg"

    filePath = os.path.join(targetDir, fileName)

    isWritten, encoded = cv2.imencode('.jpg', crop, [int(cv2.IMWRITE_JPEG_QUALITY), 92])

    if not isWritten:
      continue

    with open(filePath, 'wb') as cropFile:
      cropFile.write(encoded.tobytes())

    savedPaths.append(filePath)

  return savedPaths