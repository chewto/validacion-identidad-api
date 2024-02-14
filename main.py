from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin
from reconocimiento import reconocerRostro, pruebaVida, prueba_reco, prueba_varia
import controlador_db
from utilidades import leerDataUrl, cv2Blob, recorteData
from ocr import validarOCR, verificacionRostro, validarLadoDocumento, ocr, validacionOCR, comparacionOCR
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine, MetaData, Table, update
from sqlalchemy.orm.exc import NoResultFound

# passwordDB = '30265611'
# nombreDB = 'pki_validacion'
# hostDB = '93.93.119.219'
# portDB = 3306
# userDB = 'administrador'

passwordDB = '30265611'
nombreDB = 'pki_validacion'
hostDB = 'localhost'
portDB = 3306
userDB = 'root'

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql://{userDB}:{passwordDB}@{hostDB}:{portDB}/{nombreDB}'
db = SQLAlchemy(app)

engine = create_engine(f'mysql://{userDB}:{passwordDB}@{hostDB}:{portDB}/{nombreDB}')

metadata = MetaData()

documento_usuario_table = Table('documento_usuario', metadata, autoload_with=engine)
evidencias_adicionales_table = Table('evidencias_adicionales', metadata, autoload_with=engine)
evidencias_usuario_table = Table('evidencias_usuario', metadata, autoload_with=engine)
comprobar_proceso_table = Table('comprobacion_proceso', metadata, autoload_with=engine)

class DocumentoUsuario(db.Model):
    __table__ = documento_usuario_table

class EvidenciasAdicionales(db.Model):
    __table__ = evidencias_adicionales_table

class EvidenciasUsuario(db.Model):
    __table__ = evidencias_usuario_table

class ComprobarProceso(db.Model):
   __table__ = comprobar_proceso_table


cors = CORS(app, resources={
  r"/*":{
    "origins":"*"
  }
})
app.config['CORS_HEADER'] = 'Content-type'

@app.route('/obtener-firmador/<id>', methods=['GET'])
def obtenerFirmador(id):
  return jsonify({
    "dato": {
        "id": 11,
        "firmaElectronicaId": 11,
        "nombre": "Sandra Paola",
        "apellido": "Lopez Angarita",
        "correo": "jesuselozada@gmail.com",
        "tipoDocumento": "CEDULA",
        "documento": "8339375",
        "evidenciasCargadas": False,
        "enlaceTemporal": "nhxNYeTyF8",
        "ordenFirma": 1,
        "fechaCreacion": "2023-10-07T11:13:52-05:00"
    }
})


@app.route('/prueba', methods=['POST'])
def prueba():


  data = request.get_json()

  selfie = data['selfie']
  documento = data['anverso']

  reconocimeinto = prueba_reco(selfie, documento)

  recon = prueba_varia(selfie, documento)

  return reconocimeinto, recon


@app.route('/frame', methods=['POST'])
def frame():

  data = request.get_json()

  selfie = data['selfie']
  documento = data['anverso']

  return 'a'

#rutas para el front
@app.route('/ocr', methods=['POST'])
def verificarDocumento():
    
    dataOCR = {
      'numeroDocumentoOCR': 'no encontrado',
      'nombreOCR': 'no encontrado',
      'apellidoOCR': 'no encontrado'
    }
    
    documento = request.get_json()

    imagenPersona = documento['imagenPersona']

    imagenDocumento = documento['imagen']

    ladoDocumento = documento['ladoDocumento']

    tipoDocumento = documento['tipoDocumento']

    documentoData = leerDataUrl(imagenDocumento)

    personaData = leerDataUrl(imagenPersona)

    buscarRostro, a,b = reconocerRostro(personaData, documentoData)

    validarLado = validarLadoDocumento(tipoDocumento, ladoDocumento, imagenDocumento)

    nombre = documento['nombre']

    nombre = nombre.upper()
    nombre = nombre.strip()

    apellido = documento['apellido']

    apellido = apellido.upper()
    apellido = apellido.strip()

    numeroDocumento = documento['documento']

    documentoOCRSencillo = ocr(imagenDocumento, 'sencillo')

    documentoOCRPre = ocr(imagenDocumento, 'preprocesado')

    #ocr sencillo
    nombreOCR, porcentajeNombre = validacionOCR(documentoOCRSencillo, nombre)
    apellidoOCR, porcentajeApellido = validacionOCR(documentoOCRSencillo, apellido)
    numeroDocumentoOCR, porcentajeDocumento = validacionOCR(documentoOCRSencillo, numeroDocumento)

    nombrePreOCR, porcentajeNombrePre = validacionOCR(documentoOCRPre, nombre)
    apellidoPreOCR, porcentajeApellidoPre = validacionOCR(documentoOCRPre, apellido)
    numeroDocumentoPreOCR, porcentajeDocumentoPre = validacionOCR(documentoOCRPre, numeroDocumento)

    nombreComparado, porcentajeNombreComparado = comparacionOCR(porcentajePre=porcentajeNombrePre, porcentajeSencillo=porcentajeNombre, ocrPre=nombrePreOCR, ocrSencillo=nombreOCR)
    apellidoComparado, porcentajeApellidoComparado = comparacionOCR(porcentajePre=porcentajeApellidoPre, porcentajeSencillo=porcentajeApellido, ocrPre=apellidoPreOCR, ocrSencillo=apellidoOCR)
    documentoComparado, porcentajeDocumentoComparado = comparacionOCR(porcentajePre=porcentajeDocumentoPre, porcentajeSencillo=porcentajeDocumento, ocrPre=numeroDocumentoPreOCR, ocrSencillo=numeroDocumento)

    return jsonify({
      'ocr': {
          'nombreOCR': nombreComparado,
          'apellidoOCR': apellidoComparado,
          'documentoOCR': documentoComparado
      },
      'porcentajes': {
          'porcentajeNombreOCR': porcentajeNombreComparado,
          'porcentajeApellidoOCR': porcentajeApellidoComparado,
          'porcentajeDocumentoOCR': porcentajeDocumentoComparado
        },
      'rostro': buscarRostro,
      'ladoValido': validarLado
      })


@app.route('/validacion-vida', methods=['POST'])
def validacionVida():

  data = request.get_json()

  imagenes = data['imagenes']

  imagenBaseContador = 0
  imagenComaparacionContador = 1

  porcentaje = 0

  while imagenBaseContador <= 7 and imagenComaparacionContador <= 8:

    print(f"vuelta: {imagenComaparacionContador}")
    imagenBase = imagenes[imagenBaseContador]
    imagenComparacion = imagenes[imagenComaparacionContador]

    imagenBaseData = leerDataUrl(imagenBase)
    imagenComparacionData = leerDataUrl(imagenComparacion)

    comparacion = pruebaVida(imagenBaseData, imagenComparacionData)

    coincidencia = comparacion[0]

    resultado = comparacion[1]

    porcentaje = porcentaje + resultado

    print(comparacion)
    print(f'{porcentaje}%')

    imagenBaseContador = imagenBaseContador + 1
    imagenComaparacionContador = imagenComaparacionContador + 1


  return jsonify({'porcentajePruebaVida':porcentaje})


@app.route('/obtener-usuario', methods=['GET'])
def obtenerUsuario():
  id = request.args.get('id')


  usuario = controlador_db.obtenerUsuario('documento_usuario',id)

  print(usuario)

  return jsonify({'dato':usuario})


@app.route('/obtener-evidencias', methods=['GET'])
def obtenerEvidencias():

  id = request.args.get('id')
  tipo = request.args.get('tipo')

  usuario = controlador_db.obtenerUsuario('documento_usuario', id)

  idEvidencias = usuario[6]
  idEvidenciasAdicionales = usuario[7]

  return jsonify({'idEvidencias':idEvidencias, 'idEvidenciasAdicionales':idEvidenciasAdicionales, "tipo": tipo})


@app.route('/comprobar-proceso', methods=['GET'])
def comprobacionProceso():
    id = request.args.get('id')

    peticionProceso = ComprobarProceso().query.filter_by(id_proceso=id).first()

    if(peticionProceso):
      return jsonify({"id":peticionProceso.id, "idProceso": peticionProceso.id_proceso, "estado": peticionProceso.estado})
    else:
      return jsonify({"estado": 'no iniciada'})


@app.route('/iniciar-proceso', methods=['POST'])
def inciarProceso():
    id = request.args.get('id')

    peticionProceso = ComprobarProceso().query.filter_by(id_proceso=id).first()

    print(peticionProceso)

    if(peticionProceso):
      return jsonify({'estado':'el proceso ya esta iniciado'})
    
    if(peticionProceso is None):
      inicioProceso = ComprobarProceso(id_proceso=id, estado='iniciado')
      db.session.add(inicioProceso)
      db.session.commit()
      return jsonify({'estado':'proceso iniciado'})

@app.route('/finalizar-proceso', methods=['POST'])
def finalizarProceso():
  id = request.args.get('id')

  peticionProceso = ComprobarProceso().query.filter_by(id_proceso=id).first()

  print(peticionProceso)

  if(peticionProceso):
      stmt = (
          update(comprobar_proceso_table)
          .where(comprobar_proceso_table.c.id_proceso == id)
          .values(estado="finalizado")
      )
      db.session.execute(stmt)  # Ejecutar la sentencia de actualización
      db.session.commit()  # Confirmar los cambios en la base de datos
      return jsonify({'estado':'finalizando'})
  else:
    return jsonify({'estado': 'no se finalizó la validación'})

@app.route('/validacion-identidad-tipo-3', methods=['POST'])
def validacionIdentidadTipo3():

  id = request.args.get('id')
  idUsuario = request.args.get('idUsuario')
  idUsuario = int(idUsuario)
  tipo = request.args.get('tipo')

  #documento usuario
  nombres = request.form.get('nombres')
  apellidos = request.form.get('apellidos')
  email = request.form.get('email')
  tipoDocumento = request.form.get('tipo_documento')
  documento = request.form.get('numero_documento')

  #evidencias adicionales
  ipPrivada = controlador_db.obtenerIpPrivada()
  ipPublica = request.form.get('ip')

  dispositivo = request.form.get('dispositivo')
  navegador = request.form.get('navegador')
  latitud = request.form.get('latitud')
  longitud = request.form.get('longitud')
  hora = request.form.get('hora')
  fecha = request.form.get('fecha')

  #evidencias usuario
  fotoPersona = request.form.get('foto_persona')
  anverso = request.form.get('anverso')
  reverso = request.form.get('reverso')

  #validacion del ocr
  ocrNombre = request.form.get('porcentaje_nombre_ocr')
  ocrApellido = request.form.get('porcentaje_apellido_ocr')
  ocrDocumento = request.form.get('porcentaje_documento_ocr')

  dataOCRNombre = request.form.get('nombre_ocr')
  dataOCRApellido = request.form.get('apellido_ocr')
  dataOCRDocumento = request.form.get('documento_ocr')

  #leer data url
  fotoPersonaData = leerDataUrl(fotoPersona)
  anversoData = leerDataUrl(anverso)
  reversoData = leerDataUrl(reverso)

  reconocer = reconocerRostro(fotoPersonaData, anversoData)
  coincidencia = reconocer[0]
  estadoVericacion = reconocer[1]
  anversoOrientado = reconocer[2]

  fotoPersonaBlob = cv2Blob(fotoPersonaData)
  reversoBlob = cv2Blob(reversoData)


  #normalizacion
  nombres = nombres.lower()
  apellidos = apellidos.lower()
  email = email.lower()
  tipoDocumento = tipoDocumento.lower()
  documento = documento.lower()

  estadoVericacion = recorteData(estadoVericacion)
  dispositivo = recorteData(dispositivo)
  navegador = recorteData(navegador)
  ipPublica = recorteData(ipPublica)
  ipPrivada = recorteData(ipPrivada)
  latitud = recorteData(latitud)
  longitud = recorteData(longitud)
  hora = recorteData(hora)
  fecha = recorteData(fecha)
  ocrNombre = recorteData(ocrNombre)
  ocrApellido = recorteData(ocrApellido)
  ocrDocumento = recorteData(ocrDocumento)
  dataOCRNombre = recorteData(dataOCRNombre)
  dataOCRApellido = recorteData(dataOCRApellido)
  dataOCRDocumento = recorteData(dataOCRDocumento)


  evidenciasAdicionalesAdd = EvidenciasAdicionales(estado_verificacion=estadoVericacion, dispositivo=dispositivo, navegador=navegador, ip_publica=ipPublica, ip_privada=ipPrivada, latitud=latitud, longitud=longitud, hora=hora, fecha=fecha, validacion_nombre_ocr=ocrNombre, validacion_apellido_ocr=ocrApellido, validacion_documento_ocr=ocrDocumento, nombre_ocr=dataOCRNombre, apellido_ocr=dataOCRApellido, documento_ocr=dataOCRDocumento)
  db.session.add(evidenciasAdicionalesAdd)
  db.session.commit()

  evidenciasUsuarioAdd = EvidenciasUsuario(anverso_documento=anversoOrientado, reverso_documento=reversoBlob, foto_usuario=fotoPersonaBlob, estado_verificacion='', tipo_documento='')
  db.session.add(evidenciasUsuarioAdd)
  db.session.commit()

  evidenciasAdicionalesId = evidenciasAdicionalesAdd.id
  evidenciasUsuarioId = evidenciasUsuarioAdd.id

  validacionAdd = DocumentoUsuario(nombres=nombres, apellidos=apellidos, numero_documento=documento, tipo_documento=tipoDocumento, email=email, id_evidencias=evidenciasUsuarioId, id_evidencias_adicionales=evidenciasAdicionalesId, id_usuario_efirma=idUsuario)
  db.session.add(validacionAdd)
  db.session.commit()

  idValidacion = validacionAdd.id

  #creando documento_usuario
  # columnasDocumentoUsuario = ('nombres', 'apellidos', 'numero_documento', 'tipo_documento', 'email', 'id_evidencias', 'id_evidencias_adicionales', 'id_usuario_efirma')
  # tablaDocumento = 'documento_usuario'
  # valoresDocumento = (nombres, apellidos, documento, tipoDocumento, email, 0, 0, idUsuario)
  # documentoUsuario = controlador_db.agregarDocumento(columnasDocumentoUsuario, tablaDocumento, valoresDocumento)


  # tablaActualizar = 'documento_usuario'

  # #tabla evidencias 
  # columnasEvidencias = ('anverso_documento', 'reverso_documento', 'foto_usuario', 'estado_verificacion', 'tipo_documento')
  # tablaEvidencias = 'evidencias_usuario'
  # valoresEvidencias = (anversoOrientado, reversoBlob, fotoPersonaBlob, '', '')
  # evidenciasUsuario = controlador_db.agregarDocumento(columnasEvidencias, tablaEvidencias, valoresEvidencias)

  # #tabla evidencias adicionales

  # columnasEvidenciasAdicionales = ('estado_verificacion', 'dispositivo', 'navegador', 'ip_publica', 'ip_privada', 'latitud', 'longitud', 'hora', 'fecha', 'validacion_nombre_ocr', 'validacion_apellido_ocr', 'validacion_documento_ocr', 'nombre_ocr', 'apellido_ocr', 'documento_ocr')
  # tablaEvidenciasAdicionales = 'evidencias_adicionales'

  # valoresEvidenciasAdicionales = (estadoVericacion, dispositivo, navegador, ipPublica, ipPrivada, latitud, longitud, hora,fecha, ocrNombre, ocrApellido, ocrDocumento, dataOCRNombre, dataOCRApellido, dataOCRDocumento)
  # evidenciasAdicionales = controlador_db.agregarDocumento(columnasEvidenciasAdicionales, tablaEvidenciasAdicionales, valoresEvidenciasAdicionales)


  # columnaIdEvidencias = 'id_evidencias'
  # columnaIdEvidenciasA = 'id_evidencias_adicionales'

  # actualizarIdEvidencias = controlador_db.actualizarData(tablaDocumento,columnaIdEvidencias,evidenciasUsuario, documentoUsuario )
  # actualizarIdEvidenciasA = controlador_db.actualizarData(tablaDocumento,columnaIdEvidenciasA,evidenciasAdicionales, documentoUsuario )

  # #actualizar documento usuario
  # tipoDocumento = request.form.get('tipo_documento')
  # tipoDocumento = tipoDocumento.lower()

  # columnaTipoDocumento = 'tipo_documento'
  # actualizarTipoDocumento = controlador_db.actualizarData(tablaActualizar, columnaTipoDocumento, tipoDocumento, documentoUsuario)

  return jsonify({"idValidacion":idValidacion, "idUsuario":idUsuario, "coincidenciaDocumentoRostro":coincidencia, "estadoVerificacion":estadoVericacion})


@app.route('/validacion-identidad-tipo-1', methods=['POST'])
def validacionIdentidadTipo1():

  id = request.args.get('id')
  idUsuario = request.args.get('idUsuario')
  tipo = request.args.get('tipo')

  dispositivo = request.form.get('dispositivo')
  navegador = request.form.get('navegador')
  latitud = request.form.get('latitud')
  longitud = request.form.get('longitud')
  hora = request.form.get('hora')
  fecha = request.form.get('fecha')

  ipPrivada = controlador_db.obtenerIpPrivada()
  # ipPublica = controlador_db.obtenerIpPublica()
  ipPublica = request.form.get('ip')

  tablaActualizar = 'documento_usuario'

  #evidencias usuario
  fotoPersona = request.form.get('foto_persona')
  anverso = request.form.get('anverso')
  reverso = request.form.get('reverso')

  #validacion del ocr
  ocrNombre = request.form.get('porcentaje_nombre_ocr')
  ocrApellido = request.form.get('porcentaje_apellido_ocr')
  ocrDocumento = request.form.get('porcentaje_documento_ocr')

  dataOCRNombre = request.form.get('nombre_ocr')
  dataOCRApellido = request.form.get('apellido_ocr')
  dataOCRDocumento = request.form.get('documento_ocr')

  #leer data url
  fotoPersonaData = leerDataUrl(fotoPersona)
  anversoData = leerDataUrl(anverso)
  reversoData = leerDataUrl(reverso)

  reconocer = reconocerRostro(fotoPersonaData, anversoData)
  coincidencia = reconocer[0]
  estadoVericacion = reconocer[1]
  anversoOrientado = reconocer[2]

  fotoPersonaBlob = cv2Blob(fotoPersonaData)
  reversoBlob = cv2Blob(reversoData)


  columnasEvidencias = ('anverso_documento','reverso_documento','foto_usuario','estado_verificacion','tipo_documento')
  tablaEvidencias = 'evidencias_usuario'
  valoresEvidencias = (anversoOrientado, reversoBlob, fotoPersonaBlob, '', '')
  columnaActualizarEvidencias = 'id_evidencias'
  evidencias = controlador_db.agregarEvidencias(columnasEvidencias, tablaEvidencias,valoresEvidencias,tablaActualizar,columnaActualizarEvidencias, id)

  #tabla evidencias adicionales

  columnasEvidenciasAdicionales = ('estado_verificacion','dispositivo','navegador','ip_publica', 'ip_privada','latitud','longitud','hora','fecha',  'validacion_nombre_ocr', 'validacion_apellido_ocr', 'validacion_documento_ocr', 'nombre_ocr', 'apellido_ocr', 'documento_ocr')
  tablaEvidenciasAdicionales = 'evidencias_adicionales'
  valoresEvidenciasAdicionales = (estadoVericacion, dispositivo, navegador, ipPublica, ipPrivada, latitud, longitud, hora,fecha, ocrNombre, ocrApellido, ocrDocumento, dataOCRNombre, dataOCRApellido, dataOCRDocumento)
  columnaActualizarEvidenciasAdicionales = 'id_evidencias_adicionales'
  evidenciasAdicionales = controlador_db.agregarEvidencias(columnasEvidenciasAdicionales, tablaEvidenciasAdicionales,valoresEvidenciasAdicionales,tablaActualizar,columnaActualizarEvidenciasAdicionales, id)

  #actualizar documento usuario
  tipoDocumento = request.form.get('tipo_documento')
  tipoDocumento = tipoDocumento.lower()

  columnaTipoDocumento = 'tipo_documento'
  actualizarTipoDocumento = controlador_db.actualizarTipoDocumento(tablaActualizar, columnaTipoDocumento, tipoDocumento, id)

  return jsonify({"coincidenciaDocumentoRostro":coincidencia, "estadoVerificacion":estadoVericacion})
  
if __name__ == "__main__":
  app.run(debug=True,host="0.0.0.0", port=4000)