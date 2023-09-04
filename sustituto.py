from flask import Flask, request, jsonify
from requests import get
import uuid
import os
import face_recognition


app = Flask(__name__)

DB_PATH = './db'
for dir_ in [DB_PATH]:
    if not os.path.exists(dir_):
        os.mkdir(dir_)

@app.route("/verificacion", methods=['POST'])
def login():

    archivo = request.files['file']

    if archivo.filename != '':
      archivo.filename = f"{uuid.uuid4()}.png"
      archivo.save(archivo.filename)
    
    comparacion = recognize(archivo.filename);

    print(comparacion[1])

    return jsonify({"res":"success", "comparacion_status":comparacion[1]})


@app.route('/webhook', methods=['POST'])
def webhookListener():
  data = request.get_json()

  event = data['eventName']

  if event == "step_completed":
    mediaStep = data['step']
    mediaData = mediaStep['data']
    mediaID = mediaStep['id']

    if mediaID == 'liveness':
      if mediaData.get("spriteUrl") is not None:
        selfieURL = mediaData['spriteUrl']
      else:
        selfieURL = ''
      
      if mediaData.get("videoUrl") is not None:
        videoURL = mediaData['videoUrl']
      else:
        videoURL = ''

      descargarRecursos(videoURL, '.mkv')
      descargarRecursos(selfieURL, '.png')

      return jsonify({"status":"exitoso", "video":videoURL, "selfie":selfieURL, "id":mediaID})

    if mediaID == 'document-reading':
      if mediaData.get("fullName") is not None:
        nombreCompleto = mediaData['fullName']['value']
      else:
        nombreCompleto = ''

      if mediaData.get("frontUrl") is not None:
        anverso = mediaData['frontUrl']
      else:
        anverso = ''

      if mediaData.get("backUrl") is not None:
        reverso = mediaData['backUrl']
      else:
        reverso = ''

      descargarCedula(anverso, nombreCompleto, 'anverso', 'anverso')
      descargarCedula(reverso, nombreCompleto, 'reverso', 'reverso')

      return jsonify({"status":"exitoso","nombreCompleto":nombreCompleto ,"anverso":anverso, "reverso":reverso, "id":mediaID})


def recognize(img):
    # it is assumed there will be at most 1 match in the db
    image = face_recognition.load_image_file(img)
    embeddings_unknown = face_recognition.face_encodings(image)
    if len(embeddings_unknown) == 0:
        print('no reconocido')
        return 'no_persons_found', False
    else:
        embeddings_unknown = embeddings_unknown[0]

    match = False
    nombre = ''
    j = 0

    db_dir = sorted([j for j in os.listdir(DB_PATH) if j.endswith('.png') or j.endswith('.jpg')])

    print(db_dir)
    while ((not match) and (j < len(db_dir))):
        path_ = os.path.join(DB_PATH, db_dir[j])

        print(path_)

        loadImage = face_recognition.load_image_file(path_)
        compareImage = face_recognition.face_encodings(loadImage)

        if len(compareImage) == 0:
            return 'no se ha reconocido a una persona'
        else:
            compareImage = compareImage[0]

        match = face_recognition.compare_faces([compareImage], embeddings_unknown)

        match = match[0]

        if match:
            nombre = db_dir[j]
            nombre = nombre.replace('.jpg', '')
        else:
            nombre = ''

        j+= 1

    if match:
        print('reconocido', nombre)
        return nombre, True
    else:
        print('no reconocido')
        return 'no reconocido', False

def descargarRecursos(url,extension):
  response = get(url, stream=True)
  nombreArchivo = f"{uuid.uuid4()}.{extension}"
  path = os.path.join("./db", nombreArchivo)

  with open(path, 'wb') as file:
    for chunk in response.iter_content(chunk_size=1024):
      file.write(chunk)

def descargarCedula(url, nombre, lado, ruta):
  response = get(url, stream=True)
  nombreArchivo = f"{nombre} {lado}.png"
  path = os.path.join(f"./db/cedulas/{ruta}", nombreArchivo)

  with open(path, 'wb') as file:
    for chunk in response.iter_content(chunk_size=1024):
      file.write(chunk)

if __name__ == "__main__":
  app.run(debug=False,host="0.0.0.0")