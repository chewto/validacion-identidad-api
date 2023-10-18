from io import BytesIO
from PIL import Image
import cv2
import numpy as np
import base64


def leerDataUrl(imagen):
  imagenURL = imagen

  imagenData = base64.b64decode(imagenURL.split(",")[1])

  npArray = np.frombuffer(imagenData, np.uint8)

  imagen = cv2.imdecode(npArray, cv2.IMREAD_COLOR)

  return imagen


def cv2Blob(imagen):
  _, imagenEncode = cv2.imencode('.jpg',imagen)
  imagenBlob = imagenEncode.tobytes()

  return imagenBlob

def ioBytesDesdeDataURL(imagen):
  _, encoded = imagen.split(",", 1)

  imagenBytes = BytesIO(base64.b64decode(encoded))

  imagen = Image.open(imagenBytes)

  return imagen