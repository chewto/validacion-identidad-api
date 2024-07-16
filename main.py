from flask import Flask, request, jsonify
from flask_cors import CORS
from reconocimiento import extractFaces, getFrames, faceDetection, movementDetection
import controlador_db
from eKYC_request import postRequest
from utilidades import readDataURL
import os
from blueprints.ocr_bp import ocr_bp
from blueprints.validation_bp import validation_bp
import subprocess

app = Flask(__name__)

app.register_blueprint(ocr_bp)
app.register_blueprint(validation_bp)

carpetaPruebaVida = "./evidencias-vida"

cors = CORS(app, resources={
  r"/*":{
    "origins":"*"
  }
})
app.config['CORS_HEADER'] = 'Content-type'


@app.route('/cbs/get-session', methods=['POST'])
def test():

  data = request.get_json()

  dataVideoReq = {
    "login": "honducert_ekyctest",
    "password":"CW9R)(!L-7q8jYBp"
  }

  urlVideoToken = 'https://ekycvideoapiwest-test.lleida.net/api/rest/auth/get_video_token'

  videoRes = postRequest(url=urlVideoToken,data=dataVideoReq, headers={})

  token = videoRes['adminToken']

  sessionHeader = {
    'Authorization': f"Bearer {token}"
  }

  dataSession = {
    "externalId": "0132456",
    "userClientIP": "8.8.8.8",
    "latitude": "22.1462027",
    "longitude": "113.56829379999999",
    "userAgentHeader": "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:47.0) Gecko/20100101 Firefox/47.0"
  }

  sessionURL = 'https://ekycvideoapiwest-test.lleida.net/api/rest/standalone/create_session'

  print(sessionHeader)

  sessionRes = postRequest(url=sessionURL , data=dataSession,headers=sessionHeader)

  print(videoRes,sessionRes)

  return jsonify({
    "status": "200", 
    "message": "Session created", 
    "action": "create_session_response", 
    "riuSessionId": sessionRes['riuSessionId'], 
    "callToken": sessionRes['callToken'], 
    "adminToken": videoRes['adminToken'], 
    "mediaServerUrl": sessionRes['mediaServerUrl'], 
    "riuCoreUrl": sessionRes['riuCoreUrl']  
  })



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

  res = request.get_json()

  selfie = res['selfie']

  ndArray = readDataURL(selfie)
  antiSpoofingtest = extractFaces(ndArray=ndArray, anti_spoofing=True)

  return jsonify({"result": antiSpoofingtest})


@app.route('/prueba-vida', methods=['POST'])
def pruebaVida():

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
def obtenerUsuario():

  id = request.args.get('id')

  usuario = controlador_db.obtenerUsuario('documento_usuario',id)

  return jsonify({'dato':usuario})


@app.route('/obtener-evidencias', methods=['GET'])
def obtenerEvidencias():

  id = request.args.get('id')
  tipo = request.args.get('tipo')

  usuario = controlador_db.obtenerUsuario('documento_usuario', id)

  idEvidencias = usuario[6]
  idEvidenciasAdicionales = usuario[7]

  return jsonify({'idEvidencias':idEvidencias, 'idEvidenciasAdicionales':idEvidenciasAdicionales, "tipo": tipo})

@app.route('/comprobacion-proceso', methods=['GET'])
def comprobacionProceso():
    idUsuarioEFirma = request.args.get('idUsuarioEFirma')

    peticionProceso = controlador_db.comprobarProceso(idUsuarioEFirma)

    if peticionProceso:
        return jsonify({
          "validaciones":peticionProceso[0]
        })
    else:
        return jsonify({"validaciones": 0})

@app.route('/', methods=['GET'])
def health():
  return 'Servicio activo'

if __name__ == "__main__":
  try:
    app.run(debug=True,host="0.0.0.0", port=4000)
  finally:
    print('para reiniciar use el siguiente comando = python main.py')