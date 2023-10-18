import face_recognition
import numpy as np
import cv2
from utilidades import cv2Blob, ioBytesDesdeDataURL
import mediapipe as mp

mp_drawing = mp.solutions.drawing_utils
mp_hands = mp.solutions.hands

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
    
def reconocerRostro(imgPersona, imgDocumento):

    blobdocumento = cv2Blob(imgDocumento)


    reconocido = False

    orientado = False

    intentosOrientacion = 0

    while orientado == False and intentosOrientacion <= 4:
      reconocerImagenComparar = face_recognition.face_encodings(imgDocumento)

      if len(reconocerImagenComparar) == 0:
        print(False, 'pendiente revision')
        imgDocumento = cv2.rotate(imgDocumento, cv2.ROTATE_90_CLOCKWISE)
        intentosOrientacion = intentosOrientacion + 1

        
        if (intentosOrientacion == 4 and orientado == False):
          return False, 'pendiente revision, ningun rostro reconocido en el documento', blobdocumento
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

    print(reconocerImagenComparar)
    reconocido = face_recognition.compare_faces([reconocerImagenComparar], reconocerImagen)

    reconocido = reconocido[0]

    if reconocido:
        return True, 'verificado', imagenOrientadaBlob
    else:
        return False, 'pendiente revision, no reconocido', imagenOrientadaBlob


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

def detectarDedos(data_url:str):
    hands = mp_hands.Hands(static_image_mode=True, max_num_hands=2, min_detection_confidence=0.5)

    # Decode data URL
    image = ioBytesDesdeDataURL(data_url)
    image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    image = cv2.flip(image, 1)

    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    results = hands.process(rgb)

    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            mp_drawing.draw_landmarks(image, hand_landmarks, mp_hands.HAND_CONNECTIONS)

            # Detect fingers
            finger_names = ['pulgar', 'indice', 'medio', 'anular', 'meñique']
            fingers_up = []

            # Thumb
            thumb_up = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP].y < hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_IP].y
            if thumb_up:
                fingers_up.append(finger_names[0])

            # Index Finger
            index_finger_up = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP].y < hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_MCP].y
            if index_finger_up:
                fingers_up.append(finger_names[1])

            # Middle Finger
            middle_finger_up = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP].y < hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_MCP].y
            if middle_finger_up:
                fingers_up.append(finger_names[2])

            # Ring Finger
            ring_finger_up = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP].y < hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_MCP].y
            if ring_finger_up:
                fingers_up.append(finger_names[3])

            # Pinky Finger
            pinky_finger_up = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_TIP].y < hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_MCP].y
            if pinky_finger_up:
                fingers_up.append(finger_names[4])

            # Display the fingers that are up
            if fingers_up:
                finger_text = ', '.join(fingers_up)
                cv2.putText(image, f'Finger(s) Up: {finger_text}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                
                return fingers_up
            else:
                cv2.putText(image, 'No fingers up', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)


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