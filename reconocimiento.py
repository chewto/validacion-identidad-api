import face_recognition
import numpy as np
import cv2
from utilidades import cv2Blob
from PIL import Image
import base64
import io


def obtenerFrames(video_path):
    dataURL = ""
    framesCapturados = []
    cap = cv2.VideoCapture(video_path)
    contadorFrames = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        if contadorFrames % 10 == 0:
            frameGris = cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
            framesCapturados.append(frameGris)

        contadorFrames += 1

    cap.release()
    return dataURL,framesCapturados

def deteccionRostro(frames):

    rostrosComparacion = []

    rostroReferencia = {

    }

    contador = 1

    for frame in frames:

        clasificadorCaras = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_alt.xml"
        )

        carasDetectadas = clasificadorCaras.detectMultiScale(
            frame, scaleFactor=1.1, minNeighbors=7, minSize=(50,50)
        )

        if(len(carasDetectadas) >= 1):
            for(x,y,w,h) in carasDetectadas:
                if(contador == 1):
                    rostroReferencia['X'] = x
                    rostroReferencia['Y'] = y

                    frameRGB = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    pilIMG = Image.fromarray(frameRGB)
                    buff = io.BytesIO()
                    pilIMG.save(buff, format="JPEG")
                    imgStr = base64.b64encode(buff.getvalue())
                    imageDataURL += "data:image/jpeg;base64," + imgStr.decode("utf-8")
                
                if(contador >= 2):
                    rostro = {
                        "X": x,
                        "Y": y
                    }
                    rostrosComparacion.append(rostro)

        contador+= 1

    return rostroReferencia, rostrosComparacion

def determinarMovimiento(rostroReferencia, rostros):

    if(len(rostroReferencia) <= 0  and len(rostros) <= 0):
        return False

    resultados = []

    for rostro in rostros:

        for key in rostro:

            resultado = rostroReferencia.get(key) - rostro.get(key)
            if(resultado <= -1 or resultado >=1):
                    resultados.append(True)
            if(resultado == 0):
                    resultados.append(False)

    pruebaMovimiento = any(resultados)

    return pruebaMovimiento

# def reconocerRostro(imgPersona, imgDocumento):

#     blobdocumento = cv2Blob(imgDocumento)

#     reconocido = False

#     orientado = False

#     intentosOrientacion = 0

#     while orientado == False and intentosOrientacion <= 4:
#       reconocerImagenComparar = face_recognition.face_encodings(imgDocumento)

#       if len(reconocerImagenComparar) <= 0:
#         print(False, 'girando imagen')
#         imgDocumento = cv2.rotate(imgDocumento, cv2.ROTATE_90_CLOCKWISE)
#         intentosOrientacion = intentosOrientacion + 1

        
#         if (intentosOrientacion == 4 and orientado == False):
#           return False, 'pendiente revision, no hay un rostro en el documento', blobdocumento
#       else:
#         orientado = True
#         reconocerImagenComparar = reconocerImagenComparar[0]

#     _, imagenOrientadaBlob = cv2.imencode('.jpg',imgDocumento)
#     imagenOrientadaBlob = imagenOrientadaBlob.tobytes()

#     reconocerImagen = face_recognition.face_encodings(imgPersona)
#     if len(reconocerImagen) == 0:
#         return False,'pendiente revision, ningun rostro reconocido', imagenOrientadaBlob
#     else:
#         reconocerImagen = reconocerImagen[0]

#     reconociendo = False

#     intentos = 0

#     resultados = []

#     while intentos <= 1 and reconociendo is False:
#         reconocido = face_recognition.compare_faces([reconocerImagenComparar], reconocerImagen, 0.8)

#         reconocido = reconocido[0]

#         intentos = intentos + 1

#         if reconocido == True:
#             reconociendo = True
#             return True, 'verificado', imagenOrientadaBlob

#         if reconocido == False:
#             imgDocumento = cv2.rotate(imgDocumento, cv2.ROTATE_180)
#             _, imagenOrientadaBlob = cv2.imencode('.jpg',imgDocumento)
#             imagenOrientadaBlob = imagenOrientadaBlob.tobytes()
#             reconocerImagenComparar = face_recognition.face_encodings(imgDocumento)
#             if(len(reconocerImagenComparar) == 0):
#                 return False, 'pendiente revision, no hay un rostro en el documento', blobdocumento
#             else:
#                 reconocerImagenComparar = reconocerImagenComparar[0]




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

def reconocimiento(imgPersona, imgDocumento):

    if(len(imgPersona) <= 0 or len(imgDocumento) <= 0):
        return False

    reconocimientos = []

    for selfie in imgPersona:
        for documento in imgDocumento:
            comparacion = face_recognition.compare_faces([selfie], documento)
            similitud = comparacion[0]

            reconocimientos.append(similitud)

    coincidencias = any(reconocimientos)

    return coincidencias

def obtencionEncodings(encodings: list):

    carasValidas = []

    if(len(encodings) <= 0):
        return []

    for cara in encodings:
        testEncodings = face_recognition.face_encodings(cara)
        if(len(testEncodings) >= 1):
            carasValidas.append(testEncodings[0])

    return carasValidas

def orientacionImagen(imagen):

    gray_image = cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY)

    carasAlmacenadas = []

    encontrado = False
    intentos = 0

    while intentos <= 4 and encontrado == False:

        clasificadorOjos = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_eye.xml"
        )

        face_classifier = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_alt.xml"
        )

        carasDetectadas = face_classifier.detectMultiScale(
            gray_image, scaleFactor=1.1, minNeighbors=7, minSize=(50, 50)
        )

        if(len(carasDetectadas) <= 0):
            intentos = intentos + 1
            gray_image = cv2.rotate(gray_image,cv2.ROTATE_90_CLOCKWISE)
            imagen = cv2.rotate(imagen,cv2.ROTATE_90_CLOCKWISE )

        if(len(carasDetectadas) >= 1):
            encontrado = True
            for (x, y, w, h) in carasDetectadas:
                roi_gray = gray_image[y:y+h, x:x+w]

                ojos = clasificadorOjos.detectMultiScale(roi_gray)

                if(len(ojos) >= 1):
                    carasAlmacenadas.append(imagen)

        if(len(carasAlmacenadas) <= 0 and intentos >= 4):
            return imagen, carasAlmacenadas

    return imagen, carasAlmacenadas