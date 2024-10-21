from flask import Flask, request, jsonify
from flask_cors import CORS
from reconocimiento import extractFaces, getFrames, faceDetection, movementDetection
import controlador_db
from utilidades import readDataURL
import os
from blueprints.ocr_bp import ocr_bp
from blueprints.validation_bp import validation_bp
from lector_codigo import barcodeReader

app = Flask(__name__)

carpetaPruebaVida = "./evidencias-vida"

CORS(app, resources={
  r"/*":{
    "origins":"*"
  }
}, supports_credentials=True)
app.config['CORS_HEADER'] = 'Content-type'

CORS(app, resources={r"/validation/*": {"origins": "https://localhost"}})

app.register_blueprint(ocr_bp)
app.register_blueprint(validation_bp)

@app.route('/obtener-firmador/<id>', methods=['GET'])
def obtenerFirmador(id):
  return jsonify({
    "dato": {
        "id": 11,
        "firmaElectronicaId": 11,
        "nombre": "Benito",
        "apellido": "Otero Carreira",
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

if __name__ == "__main__":
  try:
    app.run(debug=True,host="0.0.0.0", port=4000)
  finally:
    print('para reiniciar use el siguiente comando = python main.py')