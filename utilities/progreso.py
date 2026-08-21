import base64
import os
import shutil

import cv2

from utilities.utilidades import readDataURL, resizeHandle

EVIDENCIAS_PROGRESO_DIR = os.getenv("EVIDENCIAS_PROGRESO_DIR", "./evidencias-progreso")
MAX_DIMENSION = 800
JPEG_QUALITY = 75
EVIDENCIA_TIPOS = ("anverso", "reverso", "selfie")


def _carpetaFirmador(id_firmador):
    return os.path.join(EVIDENCIAS_PROGRESO_DIR, str(id_firmador))


def guardarEvidencia(id_firmador, nombre, dataURL):
    if not dataURL or nombre not in EVIDENCIA_TIPOS:
        return None
    try:
        imagen = readDataURL(dataURL)
        imagen = resizeHandle(imagen, MAX_DIMENSION)
        carpeta = _carpetaFirmador(id_firmador)
        os.makedirs(carpeta, exist_ok=True)
        ruta = os.path.join(carpeta, f"{nombre}.jpeg")
        cv2.imwrite(ruta, imagen, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
        return ruta
    except Exception as e:
        print(f"Error guardando evidencia {nombre} de firmador {id_firmador}: {e}")
        return None


def leerEvidencia(id_firmador, nombre):
    if nombre not in EVIDENCIA_TIPOS:
        return None
    ruta = os.path.join(_carpetaFirmador(id_firmador), f"{nombre}.jpeg")
    if not os.path.exists(ruta):
        return None
    try:
        with open(ruta, "rb") as archivo:
            data = base64.b64encode(archivo.read()).decode("utf-8")
        return f"data:image/jpeg;base64,{data}"
    except Exception as e:
        print(f"Error leyendo evidencia {nombre} de firmador {id_firmador}: {e}")
        return None


def leerEvidencias(id_firmador):
    evidencias = {}
    for nombre in EVIDENCIA_TIPOS:
        data = leerEvidencia(id_firmador, nombre)
        if data:
            evidencias[nombre] = data
    return evidencias


def borrarProgresoFirmador(id_firmador):
    carpeta = _carpetaFirmador(id_firmador)
    if os.path.exists(carpeta):
        shutil.rmtree(carpeta, ignore_errors=True)
