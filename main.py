import base64
from flask import Flask, request, jsonify
from flask_cors import CORS
from reconocimiento import extractFaces, getFrames, faceDetection, movementDetection
import controlador_db
from utilidades import readDataURL
import os
from blueprints.ocr_bp import ocr_bp
from blueprints.validation_bp import validation_bp
from lector_codigo import barcodeReader
from PIL import Image
import numpy as np
import hashlib
import time

app = Flask(__name__)


CORS(app, resources={
  r"/*":{
    "origins":"*"
  }
}, supports_credentials=True)
app.config['CORS_HEADER'] = 'Content-type'

# CORS(app, resources={r"/validation/*": {"origins": "*"}})

app.register_blueprint(ocr_bp)
app.register_blueprint(validation_bp)

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
  
  image_files = [f for f in os.listdir(pathUsuario) if f.endswith('.jpeg')]

  if not image_files:
      return jsonify({'error': 'No image found'}), 404

  image_path = os.path.join(pathUsuario, image_files[0])
  with open(image_path, "rb") as image_file:
      image_data = image_file.read()
      image_data_url = f"data:image/jpeg;base64,{base64.b64encode(image_data).decode('utf-8')}"

  image_name = os.path.basename(image_path)
  splitedName = image_name.split("_")
  splitedTest = splitedName[1].split("-")
  lifeTest = splitedTest[0].replace('.jpeg', '')

  response = {"idCarpetaUsuario":f"{usuarioId}", "idCarpetaEntidad":f"{entidadId}", "lifeTest": lifeTest, "photo": image_data_url}

  if(id is not None):
     response['videoHash'] = splitedName[0]

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

@app.route('/anti-spoof', methods=['POST'])
def antiSpoofing():
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

  
    pathVideo =f"{pathUsuario}/{hash}.{formato}" if id is None else  f"{pathUsuario}/{id}-{video.filename}"
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
    app.run(debug=True,host="0.0.0.0", port=4000)
  finally:
    print('para reiniciar use el siguiente comando = python main.py')