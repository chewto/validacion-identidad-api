import cv2
from PIL import Image
import base64
import io
from deepface import DeepFace
import os
from typing import List, Optional
import numpy as np
from insightface.app import FaceAnalysis

try:
    import av
except Exception as e:
    raise ImportError("PyAV no está instalado. Instala con: pip install av") from e



haarscascade_frontal_face = 'haarcascade_frontalface_alt.xml'
haarscascade_eye = 'haarcascade_eye.xml'

def extractFaces(imageArray, anti_spoofing: bool):

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
                "h": detectedFaces['facial_area']['h'],
                "detected": True
            }
            if anti_spoofing:
                data["isReal"] = detectedFaces['is_real']

            faces.append(data)

        # Si no se detectaron caras, agregar un elemento indicando no detectado
        if not faces:
            data = {
                "x": 0,
                "y": 0,
                "w": 0,
                "h": 0,
                "detected": False
            }
            if anti_spoofing:
                data["isReal"] = False
            faces.append(data)

    except Exception as error:
        print("no se dio xd")
        data = {
            "x": 0,
            "y": 0,
            "w": 0,
            "h": 0,
            "detected": False
        }
        if anti_spoofing:
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


def analyzeFace(image):
    result = DeepFace.analyze(img_path=image, actions=['age', 'gender'])
    # Convert any np.float types to native float recursively
    def convert_npfloat(obj):
        if isinstance(obj, dict):
            return {k: convert_npfloat(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_npfloat(v) for v in obj]
        elif isinstance(obj, np.floating):
            return float(obj)
        else:
            return obj
    return convert_npfloat(result)


def verifyFaces(imageArray1, imageArray2):
    try:
        compareFaces = DeepFace.verify(
            img1_path=imageArray1,
            img2_path=imageArray2,
            model_name='Facenet512',
            detector_backend='retinaface', # Mucho más estable
            enforce_detection=False,       # Evita que el programa "muera" si no ve una cara clara
            align=True                     # Ayuda a que Facenet reciba la cara derecha
        )

        distance = int(compareFaces['distance'] * 100) / 100

        return (
            compareFaces['facial_areas'],
            distance,
            compareFaces['verified']
        )
    except Exception as e:
        print(f"Error en validación: {e}")
        return {'img1': 0, 'img2': 0}, 10.67, False # Uso 1.0 para indicar distancia máxima


# def getFrames(
#     video_path: str,
#     frameCounter: int,
#     use_timestamps: bool = False,
#     interval_ms: int = 333,
#     max_frames: Optional[int] = None,
# ) -> List[np.ndarray]:
#     """
#     Extrae frames usando PyAV (av). Compatibilidad con la semántica original:
#       - si use_timestamps == False: toma 1 cada `frameCounter` frames decodificados (contador % frameCounter == 0)
#       - si use_timestamps == True: toma 1 cada `interval_ms` milisegundos (más robusto para VFR)

#     Devuelve lista de frames (numpy arrays BGR) y además guarda cada frame capturado como JPG en save_dir.
#     """
#     framesCapturados: List[np.ndarray] = []

#     if not os.path.isfile(video_path):
#         print(f"Error: File does not exist {video_path}")
#         return "path invalido"

#     try:
#         container = av.open(video_path)
#     except Exception as e:
#         print(f"Error abriendo el video con PyAV: {e}")
#         return "no hay"

#     # obtener primer stream de video
#     try:
#         vstream = next(s for s in container.streams if s.type == "video")
#     except StopIteration:
#         print("No se encontró stream de video en el archivo.")
#         container.close()
#         return "no hay video"

#     contadorFrames = 0
#     saved = 0
#     next_target_time = 0.0  # en segundos, para muestreo por tiempo

#     try:
#         for packet in container.demux(vstream):
#             for frame in packet.decode():
#                 # obtener timestamp fiable
#                 t = None
#                 if frame.time is not None:
#                     t = float(frame.time)
#                 elif frame.pts is not None and vstream.time_base is not None:
#                     try:
#                         t = float(frame.pts * vstream.time_base)
#                     except Exception:
#                         t = None

#                 if use_timestamps:
#                     # muestreo por tiempo (robusto frente a VFR)
#                     if t is None:
#                         # si no hay timestamp, fallback a contador
#                         cond = (contadorFrames % frameCounter == 0)
#                     else:
#                         cond = (t >= next_target_time)
#                 else:
#                     # comportamiento original: muestrear por índice de frame decodificado
#                     cond = (contadorFrames % frameCounter == 0)

#                 if cond:
#                     # convertir VideoFrame a ndarray BGR
#                     try:
#                         img = frame.to_ndarray(format="bgr24")
#                     except Exception as e:
#                         print(f"Error convirtiendo frame a ndarray: {e}")
#                         img = None

#                     if img is not None:
#                         # opcional: guarda imagen en disco
#                         frame_filename = os.path.join('./videos', f"frame_{contadorFrames}.jpg")
#                         try:
#                             cv2.imwrite(frame_filename, img)
#                         except Exception as e:
#                             print(f"Error guardando {frame_filename}: {e}")
#                         framesCapturados.append(img)
#                         saved += 1
#                         # actualizar siguiente objetivo temporal si aplica
#                         if use_timestamps and t is not None:
#                             next_target_time += interval_ms / 1000.0

#                         # si max_frames está definido, corta cuando se alcanza
#                         if max_frames is not None and saved >= max_frames:
#                             container.close()
#                             print(f"Total frames captured: {len(framesCapturados)}")
#                             return framesCapturados

#                 contadorFrames += 1
#     except Exception as e:
#         print(f"Error durante la decodificación: {e}")
#     finally:
#         container.close()

#     print(f"Total frames captured: {len(framesCapturados)}")
#     return framesCapturados

def getFrames(
    video_path: str,
    frameCounter: int = 1,           # parámetro ignorado (se mantiene por compatibilidad)
    use_timestamps: bool = True,     # forzado a True internamente
    interval_ms: int = 500,          # 500 ms -> 0.5 s
    max_frames: Optional[int] = None,
) -> List[np.ndarray]:
    """
    Extrae 1 frame cada `interval_ms` milisegundos (por defecto 500 ms).
    - Ignora frameCounter (no se usa).
    - Guarda los frames en ./videos como frame_00000.jpg...
    - Devuelve lista de np.ndarray (BGR).
    """
    frames_capturados: List[np.ndarray] = []

    if not os.path.isfile(video_path):
        print(f"Error: File does not exist {video_path}")
        return []

    save_dir = "./videos"
    os.makedirs(save_dir, exist_ok=True)

    try:
        container = av.open(video_path)
    except Exception as e:
        print(f"Error abriendo el video con PyAV: {e}")
        return []

    try:
        vstream = next(s for s in container.streams if s.type == "video")
    except StopIteration:
        print("No se encontró stream de video.")
        container.close()
        return []

    interval_s = interval_ms / 1000.0
    target_index = 0
    target_time = target_index * interval_s
    saved = 0

    try:
        for packet in container.demux(vstream):
            for frame in packet.decode():
                # Obtener timestamp fiable
                t = None
                if frame.time is not None:
                    t = float(frame.time)
                elif frame.pts is not None and vstream.time_base is not None:
                    try:
                        t = float(frame.pts * vstream.time_base)
                    except Exception:
                        t = None
                else:
                    t = None

                if t is None:
                    continue  # no timestamp -> saltar

                # Si el tiempo actual pasó el objetivo, capturamos 1 frame para ese intervalo
                if t + 1e-9 >= target_time:
                    # convertir VideoFrame a ndarray BGR
                    try:
                        img = frame.to_ndarray(format="bgr24")
                    except Exception as e:
                        print(f"Error convirtiendo frame a ndarray: {e}")
                        continue

                    # guardar JPG
                    # frame_filename = os.path.join(save_dir, f"frame_{saved:05d}.jpg")
                    # try:
                    #     # cv2.imwrite(frame_filename, img)
                    # except Exception as e:
                    #     print(f"Warning: no se pudo guardar {frame_filename}: {e}")

                    frames_capturados.append(img)
                    saved += 1

                    # avanzar el target_index para el siguiente objetivo temporal
                    # calculamos el siguiente índice en base al timestamp actual para evitar "acumulación"
                    # por ejemplo si el frame está muy adelantado saltamos los targets intermedios
                    target_index = int(math.floor(t / interval_s)) + 1
                    target_time = target_index * interval_s

                    if max_frames is not None and saved >= max_frames:
                        container.close()
                        print(f"Total frames captured: {len(frames_capturados)}")
                        return frames_capturados
    except Exception as e:
        print(f"Error durante la decodificación: {e}")
    finally:
        container.close()

    print(f"Total frames captured: {len(frames_capturados)}")
    return frames_capturados

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


app = FaceAnalysis(name='buffalo_l', providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])
app.prepare(ctx_id=0, det_size=(640, 640))


def recognize(frames_ref, img2_path, threshold=0.34):

    facesRefs = []

    for frame in frames_ref:
        faces = app.get(frame)
        if faces:
            # Usar la cara con mayor score en el frame
            main_face = max(faces, key=lambda f: f.det_score)
            facesRefs.append(main_face)

    faces_doc = app.get(img2_path)

    # Validamos que haya embedding de referencia y rostros en el documento
    if not facesRefs or not faces_doc:
        return False, 0.0001

    similarities = []
    for face in faces_doc:
        faceNormed = face.normed_embedding
        for ref_face in facesRefs:
            scoreEmbeddng = ref_face.normed_embedding
            similarity = np.dot(scoreEmbeddng, faceNormed)
            similarities.append(similarity)

    max_similarity = max(similarities)
    is_same = max_similarity > threshold

    return bool(is_same), float(max_similarity)
