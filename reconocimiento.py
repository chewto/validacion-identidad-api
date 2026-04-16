import cv2
from PIL import Image
import base64
import io
from deepface import DeepFace
import os
from typing import List, Optional, Tuple
import numpy as np
from insightface.app import FaceAnalysis
import math

try:
    import av
except Exception as e:
    raise ImportError("PyAV no está instalado. Instala con: pip install av") from e


haarscascade_frontal_face = 'haarcascade_frontalface_alt.xml'
haarscascade_eye = 'haarcascade_eye.xml'

# ─────────────────────────────────────────────────────────────────────────────
# PUNTO 1.1 — Utilidades de calidad de imagen
# ─────────────────────────────────────────────────────────────────────────────

def calcular_blur_score(img: np.ndarray) -> float:
    """
    Calcula la nitidez de una imagen usando la varianza del Laplaciano.
    Valores altos = imagen nítida.
    Valores bajos = imagen borrosa / deteriorada.
    Referencia práctica: <200 malo, 200-500 medio, >500 bueno.
    """
    if img is None or img.size == 0:
        return 0.0
    if img.ndim == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def get_threshold_adaptativo(img_documento: np.ndarray) -> float:
    """
    Ajusta el umbral de similitud facial según la calidad estimada del documento.
    Cédulas colombianas viejas (sin fecha de vencimiento) suelen tener blur score bajo,
    por lo que se les aplica un threshold más permisivo para no rechazarlas.

    | Calidad    | Blur Score | Threshold |
    |------------|------------|-----------|
    | Alta       | > 500      | 0.34      |
    | Media      | 200–500    | 0.28      |
    | Baja       | < 200      | 0.22      |
    """
    score = calcular_blur_score(img_documento)
    print(f"[Reconocimiento] Blur score del documento: {score:.1f}")
    if score > 500:
        return 0.34, 0.6
    if score > 200:
        return 0.28, 0.75
    return 0.22, 0.8


# ─────────────────────────────────────────────────────────────────────────────
# PUNTO 1.1 — Preprocesamiento de imagen del documento
# ─────────────────────────────────────────────────────────────────────────────

def preprocesar_imagen_documento(img: np.ndarray) -> np.ndarray:
    """
    Pipeline de mejora de calidad aplicado a la imagen del documento
    ANTES de extraer el embedding facial.

    Pasos:
    1. Upscale si la imagen es pequeña (< 800px ancho)
    2. CLAHE en canal L del espacio LAB para normalizar contraste
    3. Denoising rápido para reducir ruido por deterioro
    4. Sharpening suave para realzar bordes de la fotografía
    5. Corrección de rotación fina con Hough lines (deskew)
    """
    if img is None or img.size == 0:
        return img

    resultado = img.copy()

    # 1. Upscale si la resolución es baja
    h, w = resultado.shape[:2]
    if w < 800:
        scale = 800 / w
        resultado = cv2.resize(
            resultado,
            (int(w * scale), int(h * scale)),
            interpolation=cv2.INTER_LANCZOS4
        )

    # 2. CLAHE en espacio LAB (preserva color, mejora contraste)
    try:
        lab = cv2.cvtColor(resultado, cv2.COLOR_BGR2LAB)
        l_ch, a_ch, b_ch = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        l_ch = clahe.apply(l_ch)
        resultado = cv2.cvtColor(cv2.merge([l_ch, a_ch, b_ch]), cv2.COLOR_LAB2BGR)
    except Exception as e:
        print(f"[Preprocesamiento] CLAHE falló: {e}")

    # 3. Denoising (h=10 es agresivo pero apropiado para fotos deterioradas)
    try:
        resultado = cv2.fastNlMeansDenoisingColored(resultado, None, h=10, hColor=10,
                                                    templateWindowSize=7, searchWindowSize=21)
    except Exception as e:
        print(f"[Preprocesamiento] Denoising falló: {e}")

    # 4. Sharpening suave (solo si la imagen no es ya muy nítida)
    blur_score = calcular_blur_score(resultado)
    if blur_score < 600:
        kernel_sharp = np.array([[0, -0.5, 0],
                                  [-0.5, 3, -0.5],
                                  [0, -0.5, 0]])
        resultado = cv2.filter2D(resultado, -1, kernel_sharp)
        resultado = np.clip(resultado, 0, 255).astype(np.uint8)

    # 5. Corrección de rotación fina (deskew) con Hough lines
    try:
        gray_deskew = cv2.cvtColor(resultado, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray_deskew, 50, 150, apertureSize=3)
        lines = cv2.HoughLines(edges, 1, np.pi / 180, threshold=100)
        if lines is not None:
            angulos = []
            for line in lines[:20]:  # solo las primeras 20 líneas más fuertes
                rho, theta = line[0]
                # Convertir a grados, normalizar al rango -45..45
                angle_deg = math.degrees(theta) - 90
                if -45 < angle_deg < 45:
                    angulos.append(angle_deg)
            if angulos:
                angulo_medio = np.median(angulos)
                # Solo corregir si el ángulo es significativo pero no extremo
                if 0.5 < abs(angulo_medio) < 15:
                    h_r, w_r = resultado.shape[:2]
                    center = (w_r // 2, h_r // 2)
                    M = cv2.getRotationMatrix2D(center, angulo_medio, 1.0)
                    resultado = cv2.warpAffine(
                        resultado, M, (w_r, h_r),
                        flags=cv2.INTER_LINEAR,
                        borderMode=cv2.BORDER_REPLICATE
                    )
                    print(f"[Preprocesamiento] Deskew aplicado: {angulo_medio:.2f}°")
    except Exception as e:
        print(f"[Preprocesamiento] Deskew falló: {e}")

    return resultado

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


def getFrames(
    video_path: str,
    frameCounter: int = 1,           # parámetro ignorado (se mantiene por compatibilidad)
    use_timestamps: bool = True,     # forzado a True internamente
    interval_ms: int = 333,          # PUNTO 1.4: 333ms → ~3fps para más candidatos de frame
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

# linux
# models_dir = os.path.expanduser('~/.insightface/models')
# os.makedirs(models_dir, exist_ok=True)

app = FaceAnalysis(name='buffalo_l', providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])
app.prepare(ctx_id=0, det_size=(640, 640))


# ─────────────────────────────────────────────────────────────────────────────
# PUNTO 1.4 — Selección de frame por calidad y pose frontal
# ─────────────────────────────────────────────────────────────────────────────

def _score_frame(frame: np.ndarray, face) -> float:
    """
    Calcula un puntaje combinado para seleccionar el mejor frame.
    Combina: det_score (confianza de detección) + frontalidad (penaliza pose lateral).
    """
    det_score = float(face.det_score) if hasattr(face, 'det_score') else 0.5

    # Penalizar rotación lateral: face.pose = [pitch, yaw, roll]
    yaw_penalty = 0.0
    if hasattr(face, 'pose') and face.pose is not None:
        yaw = abs(float(face.pose[1]))  # yaw: rotación izquierda/derecha
        # Penalizar progresivamente caras giradas más de 15°
        yaw_penalty = max(0.0, (yaw - 15) / 90.0) * 0.4

    return det_score - yaw_penalty


def _filtrar_frames_por_calidad(
    frames: List[np.ndarray],
    blur_minimo: float = 80.0
) -> List[np.ndarray]:
    """
    Descarta frames demasiado borrosos del video de liveness.
    Mantiene al menos 1 frame aunque todos sean borrosos.
    """
    if not frames:
        return frames
    buenos = [f for f in frames if calcular_blur_score(f) >= blur_minimo]
    if not buenos:
        print(f"[Frames] Todos los frames están por debajo de blur_minimo={blur_minimo}, usando todos.")
        return frames
    print(f"[Frames] {len(buenos)}/{len(frames)} frames pasaron el filtro de calidad.")
    return buenos


# ─────────────────────────────────────────────────────────────────────────────
# PUNTO 1.2/1.3 — recognize() con threshold adaptativo + ensemble
# ─────────────────────────────────────────────────────────────────────────────

def recognize(
    frames_ref: List[np.ndarray],
    img2_path: np.ndarray,
    threshold: Optional[float] = None
) -> Tuple[bool, float, Optional[np.ndarray]]:
    """
    Compara rostros de frames del video de liveness contra la imagen del documento.

    Mejoras aplicadas (Punto 1):
    - PUNTO 1.1: Preprocesamiento de la imagen del documento antes de extraer embedding.
    - PUNTO 1.2: Threshold adaptativo basado en la calidad (blur score) del documento.
    - PUNTO 1.3: Ensemble InsightFace → DeepFace como fallback si InsightFace no supera el threshold.
    - PUNTO 1.4: Filtrado de frames borrosos + selección por pose frontal.

    Returns:
        (is_same, max_similarity, best_frame)
    """
    if not frames_ref or img2_path is None:
        return False, 0.0001, None

    # ── PUNTO 1.1: Preprocesar la imagen del documento ──────────────────────
    print("[Reconocimiento] Aplicando preprocesamiento al documento...")
    img_doc_preprocesada = preprocesar_imagen_documento(img2_path)

    # ── PUNTO 1.2: Calcular threshold adaptativo ────────────────────────────
    if threshold is None:
        threshold, threshold_deepface = get_threshold_adaptativo(img2_path)  # usar imagen original para el score
    print(f"[Reconocimiento] Threshold adaptativo: {threshold}")

    # ── PUNTO 1.4: Filtrar frames por calidad ──────────────────────────────
    frames_filtrados = _filtrar_frames_por_calidad(frames_ref, blur_minimo=80.0)

    # ── InsightFace: extraer embeddings del documento ───────────────────────
    faces_doc = app.get(img_doc_preprocesada)
    if not faces_doc:
        # Intentar con imagen sin preprocesar por si el preprocesamiento afectó la detección
        print("[Reconocimiento] InsightFace no detectó cara en documento preprocesado, intentando original...")
        faces_doc = app.get(img2_path)
    if not faces_doc:
        print("[Reconocimiento] No se detectó ningún rostro en el documento.")
        return False, 0.0001, None

    best_frame: Optional[np.ndarray] = None
    max_similarity = 0.0

    # ── Iterar frames del video ─────────────────────────────────────────────
    for frame in frames_filtrados:
        faces_frame = app.get(frame)
        if not faces_frame:
            continue

        # PUNTO 1.4: Seleccionar la cara con mejor puntaje combinado (det_score + frontalidad)
        main_face = max(faces_frame, key=lambda f: _score_frame(frame, f))
        ref_embedding = main_face.normed_embedding

        for face_doc in faces_doc:
            doc_embedding = face_doc.normed_embedding
            similarity = float(np.dot(ref_embedding, doc_embedding))

            if similarity > max_similarity:
                max_similarity = similarity
                best_frame = frame

    if best_frame is None:
        print("[Reconocimiento] InsightFace no encontró correspondencias en ningún frame.")
        return False, 0.0001, None

    print(f"[Reconocimiento] InsightFace — similitud máxima: {max_similarity:.4f} (threshold: {threshold})")

    # ── Verificar resultado de InsightFace ──────────────────────────────────
    if max_similarity > threshold:
        return True, max_similarity, best_frame

    # ── PUNTO 1.3: Ensemble — fallback a DeepFace Facenet512 ───────────────
    print("[Reconocimiento] InsightFace no superó el threshold. Intentando con DeepFace (ensemble)...")
    try:
        df_result = DeepFace.verify(
            img1_path=best_frame,
            img2_path=img_doc_preprocesada,
            model_name='Facenet512',
            detector_backend='retinaface',
            enforce_detection=False,
            align=True
        )
        # df_verified = df_result.get('verified', False)
        df_verified = float(df_result.get('distance', 1.0)) < threshold_deepface
        df_distance = float(df_result.get('distance', 1.0))
        # Convertir distancia a similitud aproximada para devolver un valor consistente
        df_similarity = max(0.0, 1.0 - df_distance)
        print(f"[Reconocimiento] DeepFace — verificado: {df_verified}, distancia: {df_distance:.4f}")

        if df_verified:
            # Usar la similitud de InsightFace como referencia pero marcar como verificado
            return True, max(max_similarity, df_similarity), best_frame
        else:
            # Ningún modelo verificó — devolver la mejor similitud disponible
            return False, max_similarity, best_frame

    except Exception as e:
        print(f"[Reconocimiento] DeepFace ensemble falló: {e}")
        return False, max_similarity, best_frame


def recognize_con_info(
    frames_ref: List[np.ndarray],
    img2_path: np.ndarray,
    threshold: Optional[float] = None
) -> dict:
    """
    Versión extendida de recognize() que devuelve información diagnóstica.
    Útil para el logging de razón de fallo (Punto 4 del plan).
    """
    blur_doc = calcular_blur_score(img2_path) if img2_path is not None else 0.0
    threshold_usado = threshold if threshold is not None else get_threshold_adaptativo(img2_path)
    frames_validos = _filtrar_frames_por_calidad(frames_ref) if frames_ref else []

    is_same, similarity, best_frame = recognize(frames_ref, img2_path, threshold)

    failure_reason = None
    if not is_same:
        if best_frame is None:
            failure_reason = 'face_not_detected_selfie'
        else:
            failure_reason = 'face_similarity_low'

    return {
        'is_same': is_same,
        'similarity': similarity,
        'best_frame': best_frame,
        'blur_score_documento': round(blur_doc, 2),
        'threshold_usado': threshold_usado,
        'frames_totales': len(frames_ref) if frames_ref else 0,
        'frames_validos': len(frames_validos),
        'failure_reason': failure_reason,
    }