import face_recognition
import controlador_db
from io import BytesIO
import base64
import numpy as np
import cv2
from utilidades import cv2Blob
import dlib
from PIL import Image
from utilidades import leerDataUrl

# def reconocerRostro(imgPersona, imgDocumento):


#     cargarImg = face_recognition.load_image_file(imgPersona)
#     reconocerImagen = face_recognition.face_encodings(cargarImg)
#     if len(reconocerImagen) == 0:
#         return False,'pendiente revision'
#     else:
#         reconocerImagen = reconocerImagen[0]

#     reconocido = False

#     cargarImgComparar = face_recognition.load_image_file(imgDocumento)
#     reconocerImagenComparar = face_recognition.face_encodings(cargarImgComparar)

#     if len(reconocerImagenComparar) == 0:
#       return False, 'pendiente revision'
#     else:
#       reconocerImagenComparar = reconocerImagenComparar[0]

#     reconocido = face_recognition.compare_faces([reconocerImagenComparar], reconocerImagen)

#     reconocido = reconocido[0]

#     if reconocido:
#         return True, 'verificado'
#     else:
#         return False, 'pendiente revision'

def orientacionImagen(imgDocumento):

    blobdocumento = cv2Blob(imgDocumento)

    reconocido = False

    orientado = False

    intentosOrientacion = 0

    while orientado == False and intentosOrientacion <= 4:
      reconocerImagenComparar = face_recognition.face_encodings(imgDocumento)

      if len(reconocerImagenComparar) <= 0:
        print(False, 'girando imagen')
        imgDocumento = cv2.rotate(imgDocumento, cv2.ROTATE_90_CLOCKWISE)
        intentosOrientacion = intentosOrientacion + 1

        
        if (intentosOrientacion == 4 and orientado == False):
          return False, 'pendiente revision, no hay un rostro en el documento', blobdocumento
      else:
        orientado = True
        reconocerImagenComparar = reconocerImagenComparar[0]

def reconocerRostro(imgPersona, imgDocumento):

    blobdocumento = cv2Blob(imgDocumento)

    reconocido = False

    orientado = False

    intentosOrientacion = 0

    while orientado == False and intentosOrientacion <= 4:
      reconocerImagenComparar = face_recognition.face_encodings(imgDocumento)

      if len(reconocerImagenComparar) <= 0:
        print(False, 'girando imagen')
        imgDocumento = cv2.rotate(imgDocumento, cv2.ROTATE_90_CLOCKWISE)
        intentosOrientacion = intentosOrientacion + 1

        
        if (intentosOrientacion == 4 and orientado == False):
          return False, 'pendiente revision, no hay un rostro en el documento', blobdocumento
      else:
        orientado = True
        reconocerImagenComparar = reconocerImagenComparar[0]

    _, imagenOrientadaBlob = cv2.imencode('.jpg',imgDocumento)
    imagenOrientadaBlob = imagenOrientadaBlob.tobytes()

    reconocerImagen = face_recognition.face_encodings(imgPersona)
    if len(reconocerImagen) == 0:
        return False,'pendiente revision, ningun rostro reconocido', imagenOrientadaBlob
    else:
        reconocerImagen = reconocerImagen[0]

    reconociendo = False

    intentos = 0

    resultados = []

    while intentos <= 1 and reconociendo is False:
        reconocido = face_recognition.compare_faces([reconocerImagenComparar], reconocerImagen, 0.8)

        reconocido = reconocido[0]

        intentos = intentos + 1

        if reconocido == True:
            reconociendo = True
            return True, 'verificado', imagenOrientadaBlob

        if reconocido == False:
            imgDocumento = cv2.rotate(imgDocumento, cv2.ROTATE_180)
            _, imagenOrientadaBlob = cv2.imencode('.jpg',imgDocumento)
            imagenOrientadaBlob = imagenOrientadaBlob.tobytes()
            reconocerImagenComparar = face_recognition.face_encodings(imgDocumento)
            if(len(reconocerImagenComparar) == 0):
                return False, 'pendiente revision, no hay un rostro en el documento', blobdocumento
            else:
                reconocerImagenComparar = reconocerImagenComparar[0]

def pruebaVida(imagenBase, imagenComparacion):
   
    imagenBaseEncode = face_recognition.face_encodings(imagenBase)
    if len(imagenBaseEncode) ==0:
        return False, 0
    else:
        imagenBaseEncode = imagenBaseEncode[0]

    imagenComparacionEncode = face_recognition.face_encodings(imagenComparacion)
    if len(imagenComparacionEncode) == 0:
        return False, 0
    else:
        imagenComparacionEncode = imagenComparacionEncode[0]

    comparacion = face_recognition.compare_faces([imagenBaseEncode], imagenComparacionEncode)

    comparacion = comparacion[0]

    if comparacion:
        return comparacion, 12.5
    else:
        return comparacion, 0




# def reconocerRostro(img, tabla):

#     filas = controlador_db.obtenerTodos(tabla)

#     cargarImg = face_recognition.load_image_file(img)
#     reconocerImagen = face_recognition.face_encodings(cargarImg)
#     if len(reconocerImagen) == 0:
#         return 'no se encontro ninguna persona', False
#     else:
#         reconocerImagen = reconocerImagen[0]

#     reconocido = False
#     nombre = ''
#     vueltas = 0

#     nombres = []
#     imagenes = []

#     for row in filas:
#         b = io.BytesIO(row[1])
#         imagenes.append(b)
#         # nombre = row[1]
#         # apellido = row[2]
#         # nombreCompleto = f"{nombre} {apellido}"
#         # nombres.append(nombreCompleto)

#     dbData = [imagen for imagen in imagenes]

#     while ((not reconocido) and (vueltas < len(dbData))):
#         imagenComparar = imagenes[vueltas]

#         # nombreUsuario = nombres[vueltas]


#         cargarImgComparar = face_recognition.load_image_file(imagenComparar)
#         reconocerImagenComparar = face_recognition.face_encodings(cargarImgComparar)

#         if len(reconocerImagenComparar) == 0:
#             return 'no se ha reconocido a una persona'
#         else:
#             reconocerImagenComparar = reconocerImagenComparar[0]

#         reconocido = face_recognition.compare_faces([reconocerImagenComparar], reconocerImagen)

#         reconocido = reconocido[0]

#         vueltas+= 1

#     if reconocido:
#         return 'reconocido', True
#     else:
#         return 'no reconocido', False