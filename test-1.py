from PIL import Image
from deepface import DeepFace
import numpy as np
import cv2
# if result["verified"]:
#     print("Las imágenes pertenecen a la misma persona.")
# else:
#     print("Las imágenes no pertenecen a la misma persona.")
import time

def cronometro():
    inicio = time.time()  # Tiempo de inicio

    foto_cara = "../fotos-prueba/foto_usuario.jpeg"

    models = [
    "VGG-Face", 
    "Facenet", 
    "Facenet512", 
    "OpenFace", 
    "DeepFace", 
    "DeepID", 
    "ArcFace", 
    "Dlib", 
    "SFace",
    "GhostFaceNet",
    ]




    # try:
    #     result512 = DeepFace.verify(
    #         img1_path=foto_cara,
    #         img2_path="../fotos-prueba/frontal_benito.jpeg",
    #         model_name=models[2],
    #         enforce_detection=False,
    #     )

    #     print(result512)
    # except ValueError as e:
    #     print(e)
    # resultVGG = DeepFace.verify(
    #     img1_path=foto_cara,
    #     img2_path="../fotos-prueba/frontal_benito.jpeg",
    #     model_name=models[0]
    # )

    # obs = DeepFace.analyze(
    # img_path=foto_cara,
    # actions=['gender']
    # )


    facePerson = DeepFace.extract_faces(
        img_path=foto_cara,
        detector_backend='opencv',
        anti_spoofing=True,
        align=True
    )

    faceDocument = DeepFace.extract_faces(
        img_path='../fotos-prueba/frontal_benito.jpeg',
        detector_backend='opencv',
        align=True,
        enforce_detection=False
    )

    print(faceDocument)
    print(facePerson)
    # data = faceDocument[0]['face']

    # image_array = data.astype(np.uint8)

    # image_array = PIL.Image.fromarray(image_array).convert('RGB')

    # image_array.show()

    # print(resultVGG)
    # print(obs)
    # print(facePerson)
    # print(faceDocument)
    # # Simula una operación (puedes reemplazar esto con tu propia operación)

    for _ in range(1000000):
        pass

    fin = time.time()  # Tiempo de finalización
    duracion = fin - inicio

    print(f"La operación tardó aproximadamente {duracion:.4f} segundos.")

# Ejecuta el cronómetro
cronometro()
