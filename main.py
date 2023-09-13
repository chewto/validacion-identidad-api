from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin
from flask_ngrok import run_with_ngrok
from reconocimiento import reconocerRostro
import controlador_db
from validar_duplicado import comprobarDuplicado



app = Flask(__name__)
cors = CORS(app, resources={
  r"/*":{
    "origins":"*"
  }
})
app.config['CORS_HEADER'] = 'Content-type'

@app.route("/agregar-documento", methods=['POST'])
def agregarCedula():
  nombres = request.form.get('nombres')
  apellidos = request.form.get('apellidos')
  numeroDocumento = request.form.get('numero_documento')
  anverso = request.files['anverso']
  reverso = request.files['reverso']

  nombres = nombres.lower()
  apellidos = apellidos.lower()
  anversoBlob = anverso.stream.read()
  reversoBlob = reverso.stream.read()

  if len(anversoBlob) >= 200 and len(reversoBlob) >= 200:

    duplicado = comprobarDuplicado('documento_usuario', numeroDocumento)

    if duplicado != numeroDocumento:
      columnasQuery:tuple = ('nombres', 'apellidos', 'numero_documento', 'anverso_documento', 'reverso_documento')
      tablaQuery:str = 'documento_usuario'
      valoresQuery:tuple = (nombres, apellidos, numeroDocumento, anversoBlob, reversoBlob,)

      mensaje:str = controlador_db.agregarDocumento(columnasQuery, tablaQuery, valoresQuery)

      return jsonify({"mensaje":mensaje, "duplicado":duplicado})
    
    if duplicado == numeroDocumento:
      return jsonify({"mensaje":"el documento ya se encuentra registrado", "duplicado":duplicado})


@app.route("/verificacion-rostro-rostro", methods=['POST'])
def verificacion():

  archivo = request.files['file']

  obtenerImagenSnippet = '''
for row in filas:
  b = io.BytesIO(row[1])
  imagenes.append(b)

print(imagenes)
'''

  comparacion = reconocerRostro(archivo, 'usuarios', obtenerImagenSnippet);

  reconocido = comparacion[1]

  print(comparacion[1])

  return jsonify({"mensaje":"realizado con exito" , "reconocido": reconocido})


@app.route("/verificacion-rostro-documento", methods=['POST'])
def verfificacionRostroDocumento():
  nombres = request.form.get('nombres')
  apellidos = request.form.get('apellidos')
  numeroDocumento = request.form.get('numero_documento')
  fotoPersona = request.files['foto_persona']
  anverso = request.files['anverso']
  reverso = request.files['reverso']

  nombres = nombres.lower()
  apellidos = apellidos.lower()
  fotoPersonaBlob = fotoPersona.stream.read()
  anversoBlob = anverso.stream.read()
  reversoBlob = reverso.stream.read()

  snippet = '''

for row in filas:
  b = io.BytesIO(row[4])
  imagenes.append(b)
  nombre = row[1]
  apellido = row[2]
  nombreCompleto = f"{nombre} {apellido}"
  nombres.append(nombreCompleto)

'''

  if len(anversoBlob) >= 200 and len(reversoBlob) >= 200 and len(fotoPersonaBlob) >= 200:
    duplicado = comprobarDuplicado('documento_usuario', numeroDocumento)

    if duplicado != numeroDocumento:

      columnasQuery:tuple = ('nombres', 'apellidos','numero_documento', 'anverso_documento', 'reverso_documento')
      tablaQuery:str = 'documento_usuario'
      valoresQuery:tuple = (nombres, apellidos, numeroDocumento, anversoBlob, reversoBlob,)

      mensaje:str = controlador_db.agregarDocumento(columnasQuery, tablaQuery, valoresQuery)

      comparacion = reconocerRostro(fotoPersona, 'documento_usuario', snippet)
      reconocido = comparacion[1]
      nombre = comparacion[0]

      return jsonify({"persona_reconocida":nombre,"coincidencia_documento_rostro":reconocido, "registradoDB_antes":False })

    if duplicado == numeroDocumento:

      comparacion = reconocerRostro(fotoPersona, 'documento_usuario', snippet)
      reconocido = comparacion[1]
      nombre = comparacion[0]
      
      return jsonify({"persona_reconocida":nombre,"coincidencia_documento_rostro":reconocido, "registradoDB_antes":True})

  else:
    return jsonify({'mensaje':'blob invalido'})


if __name__ == "__main__":
  app.run(debug=False,host="0.0.0.0")