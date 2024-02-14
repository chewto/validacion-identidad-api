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

# Load pre-trained face detection and recognition models
detector = dlib.get_frontal_face_detector()
sp = dlib.shape_predictor('shape_predictor_68_face_landmarks.dat')
facerec = dlib.face_recognition_model_v1('dlib_face_recognition_resnet_model_v1.dat')

toleranciaReconocimiento = 0.7

def data_url_to_image(data_url):
    # Extract base64 image data
    _, base64_data = data_url.split(',', 1)
    image_data = base64.b64decode(base64_data)
    # Convert to PIL Image
    img = Image.open(BytesIO(image_data))
    
    return img

def prueba_reco(imagenCara:str, imagenDocumento:str):
    imgCaraData = data_url_to_image(imagenCara)
    imgDocumentoData = data_url_to_image(imagenDocumento)

    # blobDocumento = cv2Blob(imgDocumentoData)

    dets1 = detector(np.array(imgCaraData), 1)
    dets2 = detector(np.array(imgDocumentoData), 1)

    # if(len(dets1) <= 0):
    #     return 'Falase'

    # encontrada = False
    # intentos = 0

    # while intentos <= 4 and encontrada == False:

    #     dets2 = detector(np.array(imgDocumentoData), 1)

    #     if(len(dets2) <= 0):
    #         print(False, 'girando imagen')
    #         imgDocumentoData = cv2.rotate(imgDocumentoData, cv2.ROTATE_90_CLOCKWISE)
    #         intentos = intentos + 1

    #         if(intentos == 4 and orientado == False):
    #             return False, 'pendiente revision, no hay un rostro en el documento', blobDocumento
    #     else:
    #         encontrada = True
    #         print()


    #   else:
    #     orientado = True
    #     reconocerImagenComparar = reconocerImagenComparar[0]

    # Compute face encodings
    descripcionCara = facerec.compute_face_descriptor(np.array(imgCaraData), sp(np.array(imgCaraData), dets1[0]))
    descripcionDocumento =  facerec.compute_face_descriptor(np.array(imgDocumentoData), sp(np.array(imgDocumentoData), dets2[0]))


    # Example comparison with another face descriptor
    # Calculate Euclidean distance between the face encodings
    distance = np.linalg.norm(np.array(descripcionCara) - np.array(descripcionDocumento))
    print(distance)

    # Determine if the faces belong to the same person
    # if distance < 0.6:
    if distance < toleranciaReconocimiento:
        return 'True'
    else:
        return 'False'
    
def prueba_varia(imagenCara:str, imagenDocumento:str):
    imgCaraData = data_url_to_image(imagenCara)
    imgDocumentoData = data_url_to_image(imagenDocumento)

    documentoNp = leerDataUrl(imagenDocumento)
    blobDocumento = cv2Blob(documentoNp)

    dets1 = detector(np.array(imgCaraData), 1)

    if(len(dets1) == 0):
        return 'Falase'

    encontrada = False
    intentos = 0

    data = []

    while intentos <= 4 and encontrada == False:

        dets2 = detector(np.array(imgDocumentoData), 1)
        print(len(dets2))

        for det in dets2:
            data.append(det)

        # imgDocumentoData = cv2.rotate(np.array(imgDocumentoData), cv2.ROTATE_90_CLOCKWISE)
        # imgDocumentoData = imgDocumentoData.rotate(-90)
        intentos = intentos + 1

        # if(intentos == 4 and encontrada == False):
        # #     return False, 'pendiente revision, no hay un rostro en el documento', blobDocumento
        # else:
        #     encontrada = True
        #     print('aasdasd')


    # Compute face encodings
    descripcionCara = facerec.compute_face_descriptor(np.array(imgCaraData), sp(np.array(imgCaraData), dets1[0]))

    descripcionesDocumento = []

    resultados = []

    for det in data:
        descripcionDocumento =  facerec.compute_face_descriptor(np.array(imgDocumentoData), sp(np.array(imgDocumentoData), det))
        descripcionesDocumento.append(descripcionDocumento)

    for descripcion in descripcionesDocumento:
        distance = np.linalg.norm(np.array(descripcionCara) - np.array(descripcion))

        print(distance)

        if distance < toleranciaReconocimiento:
            resultados.append(True)
        else:
            resultados.append(False)

    print(resultados)

    return 'a'

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