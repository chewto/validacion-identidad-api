import base64
import cv2
from flask import Flask, request, jsonify, Response, render_template
from flask_cors import CORS
from flask_socketio import SocketIO, emit, send
from reconocimiento import extractFaces, getFrames, faceDetection, movementDetection, antiSpoofingTest
import controlador_db
from utilidades import readDataURL
import os
from blueprints.ocr_bp import ocr_bp
from blueprints.validation_bp import validation_bp
from lector_codigo import barcodeReader
import time
import numpy as np

app = Flask(__name__)

carpetaPruebaVida = "./evidencias-vida"

CORS(app, resources={
  r"/*":{
    "origins":"*"
  }
}, supports_credentials=True)
app.config['CORS_HEADER'] = 'Content-type'

# CORS(app, resources={r"/validation/*": {"origins": "https://localhost"}})

app.register_blueprint(ocr_bp)
app.register_blueprint(validation_bp)
# app.register_blueprint(socketio_bp)

# socketio = socketio(app)
socketio = SocketIO(app, cors_allowed_origins="*")

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

@app.route('/prueba', methods=['POST'])
def frame():
  
  reqBody = request.get_json()

  barcodes = barcodeReader(reqBody['imagen'], reqBody['id'], 'reverso')

  return jsonify({"result": barcodes})


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
    pathPrueba = f"{pathUsuario}/{entidadId}-{usuarioId}-prueba.{formato}"
    
    video.save(pathPrueba)

  frames = getFrames(pathPrueba)

  photoDataURL, rostroReferencia, rostrosComparacion = faceDetection(frames)

  photoAccess = readDataURL(photoDataURL)
  result = extractFaces(imageArray=photoAccess, anti_spoofing=True)

  movimientoDetectado = movementDetection(rostroReferencia, rostrosComparacion)

  return jsonify({"idCarpetaUsuario":f"{usuarioId}", "idCarpetaEntidad":f"{entidadId}", "movimientoDetectado":movimientoDetectado, "photo":photoDataURL, "photoResult": result})

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

@app.route('/video-template')
def index():
  return render_template('index.html')

face = './haarscascades/haarcascade_frontalface_alt.xml'
faceCascade = cv2.CascadeClassifier(face)

def genFrame():
    cap = cv2.VideoCapture(0)
    
    startTime = None

    while True:
        ret, frame = cap.read()

        if not ret:
            break
        else:
            # cv2.line(frame, (0, 0), (0, 0), (0,0,255), 2)
            height, width = frame.shape[:2]
            start_point = (width // 2, 0)
            end_point = (width// 2, height)
            cv2.line(frame, start_point, end_point, (0,0,255), 2)

            rectWidth = 200
            rectHeight = 250

            topLeft = (width //2 - rectWidth // 2, height //2 - rectHeight //2 )
            bottomRight = (width // 2 + rectWidth //2, height //2 + rectHeight // 2)

            cv2.rectangle(frame, topLeft, bottomRight, (0, 255, 0), 2)

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            faces = faceCascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=7, minSize=(50,50))

            faceDetected = False

            for(x,y,w,h)in faces:

              if(topLeft[0] <= x <= bottomRight[0] and topLeft[0] <= x + w <= bottomRight[0] and topLeft[1] <= y <= bottomRight[1] and topLeft[1] <= y + h <= bottomRight[1]):
                faceDetected = True
                
                if startTime is None:
                  startTime = time.time()

              if faceDetected:
                elapsedTime = time.time() - startTime

                if elapsedTime >= 5:
                  brightness = np.mean(gray)

                  _, encodedFrame = cv2.imencode('.jpeg', frame)
                  frameBase64 = base64.b64encode(encodedFrame).decode('utf-8')
                  frameBase64 = f"data:image/jpeg;base64,{frameBase64}"

                  readFrame = readDataURL(frameBase64)
                  antiSpoof = antiSpoofingTest(readFrame)

                  socketio.emit('video_frame', {'frame': frameBase64, 'brightness': brightness, 'antiSpoofing': antiSpoof})
                  socketio.sleep(0.1)
                  startTime = None
              else:
                startTime = None

              cv2.rectangle(frame, (x,y), (x+w, y+h), (255, 0,0), 2 )


            suc, encode = cv2.imencode('.jpeg', frame)
            serveFrame = encode.tobytes()


        yield(b'--frame\r\n'
            b'content-Type: image/jpeg\r\n\r\n' + serveFrame + b'\r\n')

@app.route('/video')
def video():

  return Response(genFrame(), mimetype='multipart/x-mixed-replace; boundary=frame')



@socketio.on('message')
def handle_message(msg):
    print('Message: ' + msg)
    send(msg, broadcast=True)

@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('broadcast')
def handle_broadcast_event(msg):
    send(msg, broadcast=True)

@socketio.on('custom_event')
def handle_custom_event(data):
    emit('response', {'data': 'Custom event received!'}, broadcast=True)



if __name__ == "__main__":
  try:
    socketio.run(app,debug=True, port=4000)
  finally:
    print('para reiniciar use el siguiente comando = python main.py')