from flask import Blueprint, request, jsonify

import controlador_db
from reconocimiento import obtencionEncodings, orientacionImagen, reconocimiento
from utilidades import cv2Blob, readDataURL, recorteData, stringBool

validation_bp = Blueprint('validation', __name__, url_prefix="/validation")

@validation_bp.route('/type-3', methods=['POST'])
def validacionIdentidadTipo3():

  id = request.args.get('id')
  idUsuario = request.args.get('idUsuario')
  idUsuario = int(idUsuario)
  tipo = request.args.get('tipo')

  idCarpetaEntidad = request.form.get('carpeta_entidad_prueba_vida')
  idCarpetaUsuario = request.form.get('carpeta_usuario_prueba_vida')
  movimiento = request.form.get('movimiento_prueba_vida')

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

  nombreCodigoBarras = request.form.get('nombre_CB')
  apellidoCodigoBarras = request.form.get('apellido_CB')
  documentoCodigoBarras = request.form.get('documento_CB')

  nombreCodigoBarras = stringBool(nombreCodigoBarras)
  apellidoCodigoBarras = stringBool(apellidoCodigoBarras)
  documentoCodigoBarras =stringBool(documentoCodigoBarras)

  #leer data url
  fotoPersonaData = readDataURL(fotoPersona)
  anversoData = readDataURL(anverso)
  reversoData = readDataURL(reverso)

  anversoOrientado, documentoValido = orientacionImagen(anversoData)
  selfie, selfieValida = orientacionImagen(fotoPersonaData)

  documentoEncodings = obtencionEncodings(documentoValido)
  selfieEncodings = obtencionEncodings(selfieValida)

  coincidencia = reconocimiento(selfieEncodings, documentoEncodings)

  estadoVericacion = ''

  if(coincidencia is True):
    estadoVericacion = 'Procesando segunda validación'
  else:
    estadoVericacion = 'Iniciando segunda validación'

  anversoOrientado = cv2Blob(anversoOrientado)
  fotoPersonaBlob = cv2Blob(selfie)
  reversoBlob = cv2Blob(reversoData)

  elementosVerificacion = [coincidencia, nombreCodigoBarras, apellidoCodigoBarras, documentoCodigoBarras]

  verificacionDirecta = all(elementosVerificacion)

  if(verificacionDirecta is True):
    estadoVericacion = 'Procesando Verificado'

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


  tablaActualizar = 'documento_usuario'

  #tabla evidencias 
  columnasEvidencias = ('anverso_documento', 'reverso_documento', 'foto_usuario', 'estado_verificacion', 'tipo_documento')
  tablaEvidencias = 'evidencias_usuario'
  valoresEvidencias = (anversoOrientado, reversoBlob, fotoPersonaBlob, '', '')
  idEvidenciasUsuario = controlador_db.insertTabla(columnasEvidencias, tablaEvidencias, valoresEvidencias)

  #tabla evidencias adicionales

  columnasEvidenciasAdicionales = ('estado_verificacion', 'dispositivo', 'navegador', 'ip_publica', 'ip_privada', 'latitud', 'longitud', 'hora', 'fecha', 'validacion_nombre_ocr', 'validacion_apellido_ocr', 'validacion_documento_ocr', 'nombre_ocr', 'apellido_ocr', 'documento_ocr', 'validacion_vida', 'id_carpeta_entidad', 'id_carpeta_usuario')
  tablaEvidenciasAdicionales = 'evidencias_adicionales'
  valoresEvidenciasAdicionales = (estadoVericacion, dispositivo, navegador, ipPublica, ipPrivada, latitud, longitud, hora,fecha, ocrNombre, ocrApellido, ocrDocumento, dataOCRNombre, dataOCRApellido, dataOCRDocumento, movimiento, idCarpetaEntidad, idCarpetaUsuario)
  idEvidenciasAdicionales = controlador_db.insertTabla(columnasEvidenciasAdicionales, tablaEvidenciasAdicionales, valoresEvidenciasAdicionales)

  columnasDocumentoUsuario = ('nombres', 'apellidos', 'numero_documento', 'tipo_documento', 'email', 'id_evidencias', 'id_evidencias_adicionales', 'id_usuario_efirma')
  tablaDocumento = 'documento_usuario'
  valoresDocumento = (nombres, apellidos, documento, tipoDocumento, email, idEvidenciasUsuario, idEvidenciasAdicionales, idUsuario)
  documentoUsuario = controlador_db.insertTabla(columnasDocumentoUsuario, tablaDocumento, valoresDocumento)

  return jsonify({"idValidacion":documentoUsuario, "idUsuario":idUsuario, "coincidenciaDocumentoRostro":coincidencia, "estadoVerificacion":estadoVericacion})
