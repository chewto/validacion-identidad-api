import base64
from flask import Flask, request, jsonify, render_template_string, url_for
from flask_cors import CORS
from blueprints.document_bp import document_bp
from reconocimiento import extractFaces, getFrames, faceDetection, movementDetection
import controlador_db
from utilidades import fileCv2, imageToDataURL, readDataURL
import os
from blueprints.country_bp import country_bp
from blueprints.ocr_bp import ocr_bp
from blueprints.validation_bp import validation_bp
from lector_codigo import barcodeReader
from PIL import Image
import numpy as np

import cv2
from ultralytics import YOLO
import easyocr

app = Flask(__name__)


CORS(app, resources={
  r"/*":{
    "origins":"*"
  }
}, supports_credentials=True)
app.config['CORS_HEADER'] = 'Content-type'

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
MODEL_PATH = 'models/modelov11-medium.pt'             # tu modelo YOLO entrenado
OCR_LANGS = ['es', 'en']                              # idiomas OCR
CONF_THRESHOLD = 0.3                                  # umbral de confianza YOLO
CLASS_NAMES = ['dni_anverso','nombre','apellido','numero_documento',
               'fecha_nacimiento','fecha_expiracion','tipo_documento',
               'foto_persona','firma','nacionalidad','lugar_nacimiento','ghost']

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# CORS(app, resources={r"/validation/*": {"origins": "*"}})

app.register_blueprint(ocr_bp)
app.register_blueprint(validation_bp)
app.register_blueprint(country_bp)
app.register_blueprint(document_bp)


# Cargar modelos
yolo_model = YOLO(MODEL_PATH)
ocr_reader = easyocr.Reader(OCR_LANGS, gpu=False)

# HTML template
HTML = '''
<!doctype html>
<title>Detección DNI Honduras</title>
<h2>Sube imagen del anverso del DNI</h2>
<form method=post enctype=multipart/form-data>
  <input type=file name=file accept="image/*">
  <input type=submit value=Subir>
</form>
{% if crops %}
  <h3>Recortes detectados:</h3>
  {% for label, img_url in crops %}
    <div style="display:inline-block; margin:10px; text-align:center;">
      <p>{{ label }}</p>
      <img src="{{ img_url }}" style="max-width:200px; max-height:200px;"><br>
    </div>
  {% endfor %}
{% endif %}
{% if result_img %}
<h3>Resultado Anotado:</h3>
<img src="{{ result_img }}" style="max-width:500px;"><br>
{% endif %}
{% if ocr_text %}
<h3>Resultado OCR (anverso):</h3>
<pre>{{ ocr_text }}</pre>
{% endif %}
''' 

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def preprocess_crop(img_crop: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(img_crop, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresh


@app.route('/prueba-modelo', methods=['GET','POST'])
def upload_and_detect():
    result_img = None
    ocr_text = ''
    crops = []  # lista de (label, url)

    if request.method == 'POST':
        file = request.files.get('file')
        if file and allowed_file(file.filename):
            img = fileCv2(file)
            h, w = img.shape[:2]

            # Inference YOLO
            results = yolo_model(img)[0]

            # Procesar detecciones
            for i, (box, score, cls) in enumerate(zip(results.boxes.xyxy, results.boxes.conf, results.boxes.cls)):
                if score < CONF_THRESHOLD:
                    continue
                x1, y1, x2, y2 = map(int, box)
                label = CLASS_NAMES[int(cls)] if int(cls) < len(CLASS_NAMES) else str(int(cls))
                crop = img[y1:y2, x1:x2]

                cropUrl = imageToDataURL(crop)

                # crop_fname = f"crop_{label}{i}{filename}"
                # crop_path = os.path.join(app.config['UPLOAD_FOLDER'], crop_fname)
                # cv2.imwrite(crop_path, crop)
                # crop_url = url_for('static', filename='uploads/' + crop_fname)
                crops.append((label, cropUrl))

                # Si es anverso, hacer OCR
                if label == 'dni_anverso':
                    proc = preprocess_crop(crop)
                    ocr_res = ocr_reader.readtext(proc)
                    texts = [res[1] for res in ocr_res]
                    ocr_text = "\n".join(texts)

                # Dibujar cuadro y etiqueta en la imagen principal
                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(img, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            result_img = imageToDataURL(img)

    return render_template_string(HTML, result_img=result_img, ocr_text=ocr_text, crops=crops)



@app.route('/obtener-firmador/<id>', methods=['GET'])
def obtenerFirmador(id):
  return jsonify({
    "dato": {
        "id": 11,
        "firmaElectronicaId": 11,
        "nombre": "MARIA DOLORES",
        "apellido": "MARTINEZ CASTRO",
        "correo": "jesuselozada@gmail.com",
        "tipoDocumento": "CEDULA",
        "documento": "423105",
        "evidenciasCargadas": False,
        "enlaceTemporal": "nhxNYeTyF8",
        "ordenFirma": 1,
        "fechaCreacion": "2023-10-07T11:13:52-05:00"
    }
})

carpetaPruebaVida = "./evidencias-vida"

@app.route('/anti-spoof', methods=['POST'])
def antiSpoofing():
  
  id = request.args.get("id")

  formato = "webm"

  video = request.files.get("video")

  usuarioId, entidadId = controlador_db.obtenerEntidad(id)

  pathEntidad = f"{carpetaPruebaVida}/{entidadId}"

  pathUsuario = f"{pathEntidad}/{usuarioId}"

  existenciaCarpetaEntidad = os.path.exists(pathEntidad)

  existenciaCarpetaUsuario = os.path.exists(pathUsuario)

  creadoEntidad = False
  creadoUsuario = False

  if(not existenciaCarpetaEntidad):
    os.mkdir(pathEntidad)
    creadoEntidad = True

  if(not existenciaCarpetaUsuario):
    os.mkdir(pathUsuario)
    creadoUsuario = True

  pathPrueba = ""

  if((creadoEntidad and creadoUsuario)or( existenciaCarpetaEntidad and existenciaCarpetaUsuario) or (creadoEntidad and existenciaCarpetaUsuario) or (creadoUsuario and existenciaCarpetaEntidad)):
    pathPrueba = f"{pathUsuario}/{entidadId}-{usuarioId}.{formato}"
    video.save(pathPrueba)

  messages = []

  frames = getFrames(pathPrueba)

  photoDataURL, rostroReferencia, rostrosComparacion = faceDetection(frames)

  photoAccess = readDataURL(photoDataURL)

  result = extractFaces(imageArray=photoAccess, anti_spoofing=True)

  movimientoDetectado = movementDetection(rostroReferencia, rostrosComparacion)

  isRealFilter = filter(lambda x: x['isReal'] != True, result)
  isRealFilter = list(isRealFilter)

  if(len(photoDataURL) <= 0):
    messages.append('No se ha detectado ningun rostro, vuelva a intentarlo.')

  if(len(isRealFilter) >= 1 and len(photoDataURL) >= 1):
    messages.append('Por favor, tome la foto de un rostro real.')

  return jsonify({"idCarpetaUsuario":f"{usuarioId}", "idCarpetaEntidad":f"{entidadId}", "movimientoDetectado":movimientoDetectado, "photo":photoDataURL, "photoResult": result, "messages": messages})


@app.route('/get-media', methods=['GET'])
def getUserMedia():

  carpetaPruebaVida = "./evidencias-vida"
  
  id = request.args.get("id")
  hash = request.args.get('hash')


  usuarioId, entidadId = [0,0]

  if(id == None):
    usuarioId = controlador_db.obtenerEntidadHash(hash)
    entidadId = usuarioId

    print('usar hash')
  else:
    usuarioId, entidadId = controlador_db.obtenerEntidad(f'SELECT fe.usuario_id,usu.entity_id from pki_firma_electronica.firma_electronica_pki as fe INNER JOIN pki_firma_electronica.firmador_pki fi ON fe.id=fi.firma_electronica_id INNER JOIN usuarios.usuarios usu ON usu.id=fe.usuario_id WHERE fi.id={id}')

    print('usar id')
  pathPrueba = "validacion_independiente"if(id == None) else "firma"

  # pathEntidad = f"{carpetaPruebaVida}/{pathPrueba}/{entidadId}"

  # pathUsuario = f"{pathEntidad}/{usuarioId}"

  pathEntidad =f"{carpetaPruebaVida}/{pathPrueba}/{usuarioId}" if(id is  None) else f"{carpetaPruebaVida}/{pathPrueba}/{entidadId}" 
  pathUsuario = f"{pathEntidad}/{hash}" if id is  None  else f"{pathEntidad}/{usuarioId}"
  
  try:
      image_files = [f for f in os.listdir(pathUsuario) if f.endswith('.jpeg')]
      video_files = [f for f in os.listdir(pathUsuario) if f.endswith('.webm') or f.endswith('.mp4')]
  except Exception as e:
      return jsonify({"evidencias": False})

  if not image_files:
      return jsonify({'error': 'No image found'}), 404

  if not video_files:
      return jsonify({'error': 'No video found'}), 404

  image_path = os.path.join(pathUsuario, image_files[0])
  video_path = os.path.join(pathUsuario, video_files[0])

  with open(image_path, "rb") as image_file:
      image_data = image_file.read()
      image_data_url = f"data:image/jpeg;base64,{base64.b64encode(image_data).decode('utf-8')}"

  image_name = os.path.basename(image_path)
  splitedName = image_name.split("_")
  splitedTest = splitedName[1].split("-")
  lifeTest = splitedTest[0].replace('.jpeg', '')

  response = {
      "idCarpetaUsuario": f"{usuarioId}",
      "idCarpetaEntidad": f"{entidadId}",
      "lifeTest": lifeTest,
      "photo": image_data_url,
      "videoHash": os.path.basename(video_path)
  }

  return jsonify(response)

  # result = extractFaces(imageArray=imageArray, anti_spoofing=True)

  # isRealFilter = filter(lambda x: x['isReal'] != True, result)
  # isRealFilter = list(isRealFilter)
  
  # # imageResult = 'OK' if (validationSuccess == 'true' and isRealFilter) else '!OK'
  # imageResultBool = True if (validationSuccess == 'true' and isRealFilter) else False
  
  # if((creadoEntidad and creadoUsuario)or( existenciaCarpetaEntidad and existenciaCarpetaUsuario) or (creadoEntidad and existenciaCarpetaUsuario) or (creadoUsuario and existenciaCarpetaEntidad)):
  #   pathVideo = f"{pathUsuario}/{entidadId}-{usuarioId}.{formato}"
  #   pathImage = f"{pathUsuario}/{entidadId}-{usuarioId}_{imageResult}.jpeg"
    
  #   # Delete all .jpeg images in the user's folder
  #   for file in os.listdir(pathUsuario):
  #       if file.endswith(".jpeg"):
  #           os.remove(os.path.join(pathUsuario, file))
    
  #   video.save(pathVideo)
  #   imageOpen.save(pathImage, format='JPEG')



# @app.route('/anti-spoof', methods=['POST'])
# def antiSpoofing():

#   carpetaPruebaVida = "./evidencias-vida"
  
#   id = request.args.get("id")
#   hash = request.args.get('hash')


#   formato = "webm"

#   video = request.files.get("video")
#   image = request.files.get("image")
#   imageOpen = Image.open(image)
#   imageArray = np.array(imageOpen)
#   validationSuccess = request.form.get("validationSuccess")

#   usuarioId, entidadId = [0,0]

#   if(id == None):
#     usuarioId = controlador_db.obtenerEntidadHash(hash)
#     entidadId = usuarioId

#     print('usar hash')
#   else:
#     usuarioId, entidadId = controlador_db.obtenerEntidad(f'SELECT fe.usuario_id,usu.entity_id from pki_firma_electronica.firma_electronica_pki as fe INNER JOIN pki_firma_electronica.firmador_pki fi ON fe.id=fi.firma_electronica_id INNER JOIN usuarios.usuarios usu ON usu.id=fe.usuario_id WHERE fi.id={id}')

#     print('usar id')
#   pathPrueba = "validacion_independiente"if(id == None) else "firma"

#   pathEntidad = f"{carpetaPruebaVida}/{pathPrueba}/{entidadId}"

#   pathUsuario = f"{pathEntidad}/{usuarioId}"

#   existenciaCarpetaEntidad = os.path.exists(pathEntidad)

#   existenciaCarpetaUsuario = os.path.exists(pathUsuario)

#   creadoEntidad = False
#   creadoUsuario = False

#   if(not existenciaCarpetaEntidad):
#     os.mkdir(pathEntidad)
#     creadoEntidad = True

#   if(not existenciaCarpetaUsuario):
#     os.mkdir(pathUsuario)
#     creadoUsuario = True

#   # result = extractFaces(imageArray=imageArray, anti_spoofing=True)

#   # isRealFilter = filter(lambda x: x['isReal'] != True, result)
#   # isRealFilter = list(isRealFilter)
  
#   lifeTest = 'OK' if (validationSuccess == 'true') else '!OK'
#   imageResultBool = True if (validationSuccess == 'true') else False
  
#   if((creadoEntidad and creadoUsuario)or( existenciaCarpetaEntidad and existenciaCarpetaUsuario) or (creadoEntidad and existenciaCarpetaUsuario) or (creadoUsuario and existenciaCarpetaEntidad)):
#     pathVideo = f"{pathUsuario}/{entidadId}-{usuarioId}.{formato}"
#     pathImage = f"{pathUsuario}/{entidadId}-{usuarioId}_{lifeTest}.jpeg"
    
#     # Delete all .jpeg images in the user's folder
#     for file in os.listdir(pathUsuario):
#         if file.endswith(".jpeg"):
#             os.remove(os.path.join(pathUsuario, file))
    
#     video.save(pathVideo)
#     imageOpen.save(pathImage, format='JPEG')

#   return jsonify({"result":imageResultBool})

@app.route('/liveness-test', methods=['POST'])
def livenessTest():
    # Base directory for storing evidence
    carpetaPruebaVida = "./evidencias-vida"
    
    # Retrieve query parameters
    id = request.args.get("id")
    hash = request.args.get('hash')
    
    # File format for video
    formato = "webm"

    # Retrieve files from the request
    video = request.files.get("video")
    image = request.files.get("image")
    if not video or not image:
        return jsonify({"error": "Missing video or image file"}), 400

    # Open the image and convert it to a NumPy array
    try:
        imageOpen = Image.open(image)
        imageArray = np.array(imageOpen)
    except Exception as e:
        return jsonify({"error": f"Failed to process image: {str(e)}"}), 500

    # Retrieve validation success flag
    validationSuccess = request.form.get("validationSuccess")

    # Initialize user and entity IDs
    usuarioId, entidadId = [0, 0]

    # Determine user and entity IDs based on the presence of 'id' or 'hash'
    if id is None:
        usuarioId = controlador_db.obtenerEntidadHash(hash)
        entidadId = usuarioId
        print('Using hash to identify user and entity')
    else:
        query = f'''
        SELECT fe.usuario_id, usu.entity_id 
        FROM pki_firma_electronica.firma_electronica_pki AS fe
        INNER JOIN pki_firma_electronica.firmador_pki fi ON fe.id = fi.firma_electronica_id
        INNER JOIN usuarios.usuarios usu ON usu.id = fe.usuario_id
        WHERE fi.id = {id}
        '''
        usuarioId, entidadId = controlador_db.obtenerEntidad(query)
        print('Using ID to identify user and entity')

    # Determine the path for storing evidence
    pathPrueba = "validacion_independiente" if id is None else "firma"
    pathEntidad =f"{carpetaPruebaVida}/{pathPrueba}/{usuarioId}" if(id is  None) else f"{carpetaPruebaVida}/{pathPrueba}/{entidadId}" 
    pathUsuario = f"{pathEntidad}/{hash}" if id is  None  else f"{pathEntidad}/{usuarioId}"

    # Create directories if they do not exist
    try:
        if not os.path.exists(pathEntidad):
            os.makedirs(pathEntidad)  # Create parent directories if needed
            print(f"Created directory: {pathEntidad}")
        if not os.path.exists(pathUsuario):
            os.makedirs(pathUsuario)  # Create parent directories if needed
            print(f"Created directory: {pathUsuario}")
    except Exception as e:
        return jsonify({"error": f"Failed to create directories: {str(e)}"}), 500

    # Determine the validation result
    lifeTest = 'OK' if validationSuccess == 'true' else '!OK'
    imageResultBool = True if validationSuccess == 'true' else False

  
    pathVideo =f"{pathUsuario}/ {video.filename}" if id is None else  f"{pathUsuario}/{id}-{video.filename}"
    pathImage = f"{pathUsuario}/{hash}_{lifeTest}.jpeg" if id is None else f"{pathUsuario}/{id}-{video.filename}_{lifeTest}.jpeg"

    # Delete all existing .jpeg files in the user's folder before saving the new image
    try:
        for file in os.listdir(pathUsuario):
            if file.endswith(".jpeg"):
                os.remove(os.path.join(pathUsuario, file))
                print(f"Deleted file: {file}")
    except Exception as e:
        return jsonify({"error": f"Failed to clean up old files: {str(e)}"}), 500

    # Save the video and image files
    try:
        video.save(pathVideo)
        print(f"Saved video to: {pathVideo}")
    except Exception as e:
        return jsonify({"error": f"Failed to save video: {str(e)}"}), 500

    try:
        imageOpen.save(pathImage, format='JPEG')
        print(f"Saved image to: {pathImage}")
    except Exception as e:
        return jsonify({"error": f"Failed to save image: {str(e)}"}), 500

    # Return the result of the validation
    return jsonify({"result": imageResultBool})

@app.route('/obtener-usuario', methods=['GET'])
def getUser():

  id = request.args.get('id')

  user = controlador_db.getUser('documento_usuario',id)

  return jsonify({'user':user})


@app.route('/obtener-evidencias', methods=['GET'])
def obtenerEvidencias():

  id = request.args.get('id')
  tipo = request.args.get('tipo')

  usuario = controlador_db.getUser('documento_usuario', id)

  idEvidencias = usuario[6]
  idEvidenciasAdicionales = usuario[7]

  return jsonify({'idEvidencias':idEvidencias, 'idEvidenciasAdicionales':idEvidenciasAdicionales, "tipo": tipo})

@app.route('/comprobacion-proceso', methods=['GET'])
def comprobacionProceso():
    idUsuarioEFirma = request.args.get('idUsuarioEFirma')

    peticionProceso = controlador_db.comprobarProceso(idUsuarioEFirma)

    if peticionProceso:
        return jsonify(peticionProceso)
    else:
        return jsonify({"validaciones": 0, "estado":""})

@app.route('/', methods=['GET'])
def health():
  return 'Servicio activo'

if __name__ == "__main__":
  try:
    app.static_folder = '.'
    app.run(debug=True,host="0.0.0.0", port=4000)
  finally:
    print('para reiniciar use el siguiente comando = python main.py')