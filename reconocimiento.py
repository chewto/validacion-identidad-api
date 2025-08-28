import cv2
from utilidades import cv2Blob
from PIL import Image
import base64
import io
from deepface import DeepFace
import os

haarscascade_frontal_face = 'haarcascade_frontalface_alt.xml'
haarscascade_eye = 'haarcascade_eye.xml'

def extractFaces(imageArray, anti_spoofing:bool):

    faces = []

    try:

        antiSpoofing = DeepFace.extract_faces(
            img_path=imageArray,
            detector_backend='opencv',
            anti_spoofing=anti_spoofing
        )

        for detectedFaces in antiSpoofing:
            data = {
                "x": detectedFaces['facial_area']['x'],
                "y": detectedFaces['facial_area']['y'],
                "w": detectedFaces['facial_area']['w'],
                "h": detectedFaces['facial_area']['h']
            }
            if(anti_spoofing== True):
                data["isReal"] = detectedFaces['is_real']
        
            faces.append(data)

    except Exception as error:
        
        data = {
            "x":0,
            "y":0,
            "w":0,
            "h":0
        }
        if(anti_spoofing):
            data["isReal"] = False

        faces.append(data)

    finally:
        return faces

def antiSpoofingTest(selfie):

    try:
        verifyFace = DeepFace.extract_faces(
            img_path=selfie,
            anti_spoofing=True
        )

        test = all(face_obj["is_real"] is True for face_obj in verifyFace)

        return test
    except:
        return False

def verifyFaces(imageArray1, imageArray2):

    try:
        compareFaces = DeepFace.verify(
            img1_path=imageArray1,
            img2_path=imageArray2,
            model_name='Facenet512',
        )
        #tenemos una ventaja con la cual podemos extraer tambien las landmarks de ambas imagenes
        
        confidence = compareFaces['distance']
        verified = compareFaces['verified']
        img1 = compareFaces['facial_areas']['img1']
        img2 = compareFaces['facial_areas']['img2']

        print(confidence)
        print(verified)

        landmarks = {
            'img1': img1,
            'img2': img2
        }

        return landmarks, confidence, verified
    except:

        landmarks = {
            'img1': 0,
            'img2': 0
        }

        return landmarks,0.99, False

def getFrames(video_path, frameCounter):
    dataURL = ""
    framesCapturados = []
    if not os.path.isfile(video_path):
        print(f"Error: File does not exist {video_path}")
        return "path invalido"
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Cannot open video file {video_path}")
        return "no hay"
    contadorFrames = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        if contadorFrames % frameCounter == 0:
            # Guardar el frame como imagen en la carpeta ./videos
            framesCapturados.append(frame)
            output_dir = "/videos"
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            frame_filename = os.path.join(output_dir, f"frame_{contadorFrames}.jpg")
            cv2.imwrite(frame_filename, frame)
            print(f"Captured and saved frame {contadorFrames} to {frame_filename}")

        contadorFrames += 1

    cap.release()
    print(f"Total frames captured: {len(framesCapturados)}")
    return framesCapturados

def frame_to_dataurl(frame):
    """Convierte un frame en dataURL base64 JPEG."""
    frameRGB = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    pilIMG = Image.fromarray(frameRGB)
    buff = io.BytesIO()
    pilIMG.save(buff, format="JPEG")
    imgStr = base64.b64encode(buff.getvalue()).decode("utf-8")
    return "data:image/jpeg;base64," + imgStr


def faceDetection(frames, cascade_path=cv2.data.haarcascades + haarscascade_frontal_face):
    if not frames:
        return None, {}, []  # no hay frames

    # Cargar clasificador una sola vez
    clasificadorCaras = cv2.CascadeClassifier(cascade_path)

    rostroReferencia = None
    rostrosComparacion = []
    imageDataURL = None

    for idx, frame in enumerate(frames, start=1):
        frameGray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        carasDetectadas = clasificadorCaras.detectMultiScale(
            frameGray, scaleFactor=1.1, minNeighbors=7, minSize=(50, 50)
        )

        if len(carasDetectadas) > 0:
            for (x, y, w, h) in carasDetectadas:
                rostro = {"x": x, "y": y, "w": w, "h": h}

                if idx == 1 and rostroReferencia is None:
                    rostroReferencia = rostro
                    imageDataURL = frame_to_dataurl(frame)
                else:
                    rostrosComparacion.append(rostro)

    # Si no se detectó ningún rostro, usar el primer frame como fallback
    if not imageDataURL:
        imageDataURL = frame_to_dataurl(frames[0])

    return imageDataURL, rostroReferencia or {}, rostrosComparacion

import math

def movementDetection(rostroReferencia, rostros, threshold=5, min_moving_frames=1):
    """
    Detecta movimiento comparando un rostro de referencia con una lista de rostros.
    
    Params:
        rostroReferencia (dict): {x, y, w, h}
        rostros (list[dict]): lista de rostros detectados en frames posteriores
        threshold (int): distancia mínima en píxeles para considerar movimiento
        min_moving_frames (int): número mínimo de frames que deben mostrar movimiento
    
    Return:
        str: 'OK' si hay movimiento, '!OK' si no lo hay
    """

    if not rostroReferencia or not rostros:
        return '!OK'

    x_ref = rostroReferencia.get("x")
    y_ref = rostroReferencia.get("y")
    w_ref = rostroReferencia.get("w", 0)
    h_ref = rostroReferencia.get("h", 0)

    # Centro del rostro de referencia
    cx_ref = x_ref + w_ref // 2
    cy_ref = y_ref + h_ref // 2

    moving_count = 0

    for rostro in rostros:
        cx = rostro.get("x") + rostro.get("w", 0) // 2
        cy = rostro.get("y") + rostro.get("h", 0) // 2

        # Distancia euclidiana entre los centros
        dist = math.sqrt((cx_ref - cx) ** 2 + (cy_ref - cy) ** 2)

        if dist >= threshold:
            moving_count += 1

    if moving_count >= min_moving_frames:
        return 'OK'
    else:
        return '!OK'

def orientacionImagen(imagen):

    gray_image = cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY)

    carasAlmacenadas = []
    encontrado = False
    intentos = 0
    angulo = 0

    while intentos <= 4 and encontrado == False:

        clasificadorOjos = cv2.CascadeClassifier(
            cv2.data.haarcascades + haarscascade_eye
        )

        face_classifier = cv2.CascadeClassifier(
            cv2.data.haarcascades + haarscascade_frontal_face
        )

        carasDetectadas = face_classifier.detectMultiScale(
            gray_image, scaleFactor=1.1, minNeighbors=7, minSize=(50, 50)
        )

        if(len(carasDetectadas) <= 0):
            intentos = intentos + 1
            angulo += 90
            gray_image = cv2.rotate(gray_image, cv2.ROTATE_90_CLOCKWISE)
            imagen = cv2.rotate(imagen, cv2.ROTATE_90_CLOCKWISE)

        if(len(carasDetectadas) >= 1):
            encontrado = True
            for (x, y, w, h) in carasDetectadas:
                # Convert to square
                leftLimit = x
                rightLimit = x + w

                roi_gray = gray_image[y:y+h, x:x+w]

                ojos = clasificadorOjos.detectMultiScale(roi_gray)

                if(len(ojos) >= 1):
                    carasAlmacenadas.append((imagen, (leftLimit, rightLimit)))

        if(len(carasAlmacenadas) <= 0 and intentos >= 4):
            return imagen, carasAlmacenadas

    return imagen, carasAlmacenadas
