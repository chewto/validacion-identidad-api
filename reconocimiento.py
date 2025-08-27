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

def faceDetection(frames):

    rostrosComparacion = []

    rostroReferencia = {}

    imageDataURL = ''

    contador = 1

    for frame in frames:

        frameGray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        clasificadorCaras = cv2.CascadeClassifier(
            cv2.data.haarcascades + haarscascade_frontal_face
        )

        carasDetectadas = clasificadorCaras.detectMultiScale(
            frameGray, scaleFactor=1.1, minNeighbors=7, minSize=(50,50)
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
                    imageDataURL = "data:image/jpeg;base64," + imgStr.decode("utf-8")

                if(contador >= 2):
                    rostro = {
                        "X": x,
                        "Y": y
                    }
                    rostrosComparacion.append(rostro)

        contador+= 1

    # Si no se detectó ningún rostro, usar el primer frame como data URL
    if not imageDataURL and len(frames) > 0:
        frame = frames[0]
        frameRGB = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pilIMG = Image.fromarray(frameRGB)
        buff = io.BytesIO()
        pilIMG.save(buff, format="JPEG")
        imgStr = base64.b64encode(buff.getvalue())
        imageDataURL = "data:image/jpeg;base64," + imgStr.decode("utf-8")

    return imageDataURL, rostroReferencia, rostrosComparacion

def movementDetection(rostroReferencia, rostros):

    if(len(rostroReferencia) <= 0  or len(rostros) <= 0):
        return '!OK'

    resultados = []

    for rostro in rostros:

        for key in rostro:

            resultado = rostroReferencia.get(key) - rostro.get(key)
            if(resultado <= -1 or resultado >=1):
                    resultados.append(True)
            if(resultado == 0):
                    resultados.append(False)

    pruebaMovimiento = any(resultados)

    if(pruebaMovimiento):
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
