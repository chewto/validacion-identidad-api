from flask import Blueprint, request, jsonify
import controlador_db
import json

country_bp = Blueprint('country', __name__, url_prefix='/country')


@country_bp.route('/get', methods=['GET'])
def getCountry():

  id = request.args.get('id')

  userHash = request.args.get('hash')

  data = None

  if(id is not None):
    data = controlador_db.selectData(f'''SELECT pais.codigo, pais.tipo_documento_validacion  FROM pki_firma_electronica.firmador_pki AS firmador
INNER JOIN pki_firma_electronica.firma_electronica_pki AS firma ON firma.id = firmador.firma_electronica_id
INNER JOIN usuarios.usuarios AS usu ON usu.id = firma.usuario_id
INNER JOIN pki_validacion.pais AS pais ON pais.codigo = usu.pais
WHERE firmador.id =  {id}''', ())
    
  if(userHash is not None):
    data = controlador_db.selectData(f'''SELECT pais.codigo, pais.tipo_documento_validacion FROM pki_validacion.parametros_validacion AS params
INNER JOIN usuarios.usuarios AS usu ON usu.id = params.id_usuario
INNER JOIN pki_validacion.pais AS pais ON pais.codigo = usu.pais
WHERE params.parametros_hash = '{userHash}'
''', ())

    print(data)

  if (data is not None):

    if(len(data) <= 0):
      return 'no retreive'
    code, documentTypes = data
    
    documentsArray = documentTypes.split(',')

    return jsonify({"country": code, "documentList": documentsArray})
  else:
    return 'no coutry assign'




