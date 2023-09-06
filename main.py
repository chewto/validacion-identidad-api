from flask import Flask, request, jsonify
from requests import get
import face_recognition
import io
import mariadb
import json


app = Flask(__name__)


@app.route("/cedula", methods=['POST'])
def agregarCedula():
  nombreCompleto = request.form.get('nombre')
  anverso = request.files['anverso']
  reverso = request.files['reverso']

  nombreCompleto = nombreCompleto.lower()
  anversoBlob = anverso.stream.read()
  reversoBlob = reverso.stream.read()

  if len(anversoBlob) >= 200 and len(reversoBlob) >= 200:
    conn = mariadb.connect(
      user='root',
      password="30265611",
      host='localhost',
      port=3306,
      database='pki_validacion_identidad'
    )

    cursor = conn.cursor()

    cursor.execute("SELECT * FROM documento_usuario")

    rows = cursor.fetchall()

    global duplicado
    duplicado = False

    for row in rows:
      nombre = row[1]
      if nombre == nombreCompleto:
        duplicado = True

    if duplicado == False:
      cursor.execute("INSERT INTO documento_usuario (nombre_completo, anverso, reverso) VALUES (?,?,?)", (nombreCompleto, anversoBlob, reversoBlob))

      conn.commit()
      cursor.close()
      conn.close()
      return jsonify({"mensaje":"documento registrado", "nombre_documento":nombreCompleto})
    
    if duplicado:
      conn.commit()
      cursor.close()
      conn.close()
      return jsonify({"mensaje":"el documento ya se encuentra registrado"})


@app.route("/verificacion-rostro-rostro", methods=['POST'])
def verificacion():

  archivo = request.files['file']

  obtenerImagenSnippet = '''
for row in filas:
  b = io.BytesIO(row[1])
  imagenes.append(b)

print(imagenes)
'''

  comparacion = reconocimiento(archivo, 'usuarios', obtenerImagenSnippet);

  reconocido = comparacion[1]

  print(comparacion[1])

  return jsonify({"proceso":"realizado con exito" , "reconocido": reconocido})


@app.route("/verificacion-rostro-documento", methods=['POST'])
def verfificacionRostroDocumento():
  foto = request.files['file']

  print(foto)

  snippet = '''

for row in filas:
  b = io.BytesIO(row[2])
  imagenes.append(b)
  nombre = row[1]
  nombres.append(nombre)

'''

  comparacion = reconocimiento(foto, 'documento_usuario', snippet)

  reconocido = comparacion[1]
  nombre = comparacion[0]

  return jsonify({"proceso":"realizado con exito", "persona_reconocida":nombre,"reconocido":reconocido })


@app.route("/webhook", methods=['POST'])
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
    
      if mediaData.get("videoUrl") is not None:
        videoURL = mediaData['videoUrl']

      spriteBlob = descargarRecursos(selfieURL)

      videoBlob = descargarRecursos(videoURL)

      if isinstance(spriteBlob, str) == False and isinstance(videoBlob, str) == False:
        spriteRead = spriteBlob.read()
        videoRead = videoBlob.read()

      else:
        return jsonify({"mensaje":"la url no era valida y devolvio un string"})

      if len(spriteRead) >= 200 and len(videoRead) >= 200:

        conn = mariadb.connect(
          user='root',
          password="30265611",
          host='localhost',
          port=3306,
          database='pki_validacion_identidad'
        )
        cursor = conn.cursor()

        cursor.execute('INSERT INTO usuarios (foto) VALUES (?)', (spriteRead,))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"status":"exitoso", "video":videoURL, "selfie":selfieURL, "id":mediaID})
      else:
        return jsonify({"status":"la data no cumple con los requerimentos"})




    if mediaID == 'document-reading':
      if mediaData.get("fullName") is not None:
        nombreCompleto = mediaData['fullName']['value']

      if mediaData.get("frontUrl") is not None:
        anverso = mediaData['frontUrl']

      if mediaData.get("backUrl") is not None:
        reverso = mediaData['backUrl']

      anversoBlob = descargarRecursos(anverso)

      reversoBlob = descargarRecursos(reverso)

      if isinstance(anversoBlob, str) == False and isinstance(reversoBlob, str) == False:
        anversoRead = anversoBlob.read()
        reversoRead = reversoBlob.read()

      else:
        return jsonify({"mensaje":"la url no era valida y devolvio un string"})

      if len(anversoRead) >= 200 and len(reversoRead) >= 200:

        conn = mariadb.connect(
          user='root',
          password="30265611",
          host='localhost',
          port=3306,
          database='pki_validacion_identidad'
        )
        cursor = conn.cursor()

        cursor.execute('INSERT INTO cedula_usuario (nombre_completo, anverso, reverso) VALUES (?,?,?) ', (nombreCompleto,anversoRead,reversoRead))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"status":"exitoso","nombreCompleto":nombreCompleto ,"anverso":anverso, "reverso":reverso, "id":mediaID})
      else:
        return jsonify({"status":"la data no cumple con los requerimentos"})
      

  if event != "step_completed":
    return jsonify({"mensaje":"este evento no posee la informacion que se busca"})


def reconocimiento(img, tabla, snippet):

    conn = mariadb.connect(
      user='root',
      password="30265611",
      host='localhost',
      port=3306,
      database='pki_validacion_identidad'
    )
    cursor = conn.cursor()

    cursor.execute(f'SELECT * FROM {tabla}')

    filas = cursor.fetchall()

    cursor.close()
    conn.close()

    cargarImg = face_recognition.load_image_file(img)
    reconocerImagen = face_recognition.face_encodings(cargarImg)
    if len(reconocerImagen) == 0:
        return 'no se encontro ninguna persona', False
    else:
        reconocerImagen = reconocerImagen[0]

    reconocido = False
    nombre = ''
    vueltas = 0

    nombres = []
    imagenes = []

    exec(snippet)


    dbData = [imagen for imagen in imagenes]

    while ((not reconocido) and (vueltas < len(dbData))):
        imagenComparar = imagenes[vueltas]

        nombreUsuario = nombres[vueltas]


        cargarImgComparar = face_recognition.load_image_file(imagenComparar)
        reconocerImagenComparar = face_recognition.face_encodings(cargarImgComparar)

        if len(reconocerImagenComparar) == 0:
            return 'no se ha reconocido a una persona'
        else:
            reconocerImagenComparar = reconocerImagenComparar[0]

        reconocido = face_recognition.compare_faces([reconocerImagenComparar], reconocerImagen)

        reconocido = reconocido[0]

        vueltas+= 1

    if reconocido:
        return nombreUsuario, True
    else:
        return 'no reconocido', False

def descargarRecursos(url):
  if len(url) >= 1:
    response = get(url, stream=True)
    stream = io.BytesIO(response.content)
    return stream
  else:
    return "url invalida"


if __name__ == "__main__":
  app.run(debug=False,host="0.0.0.0")