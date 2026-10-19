from flask import Blueprint, request, jsonify
import base64
import os
import request.controlador_db as controlador_db
from utilities.token_utils import token_required

logo_entidad_bp = Blueprint('logo_entidad', __name__, url_prefix='/logo-entidad')

LOGOS_DIR = os.getenv("LOGOS_DIR", "./logos-entidades")
PAISES_VALIDOS = ("COL", "HND")
EXTENSIONES = ((".png", "image/png"), (".jpg", "image/jpeg"))


@logo_entidad_bp.route('/get', methods=['GET'])
@token_required
def getLogoEntidad():
  idFirmador = request.args.get('id')

  if idFirmador is None:
    return jsonify({"error": "El parametro 'id' (id del firmador) es obligatorio"}), 400

  try:
    idFirmador = int(idFirmador)
  except ValueError:
    return jsonify({"error": "El parametro 'id' debe ser numerico"}), 400

  pais = controlador_db.get_country_code()
  if pais not in PAISES_VALIDOS:
    return jsonify({"error": f"Pais no soportado: {pais}"}), 400

  entidad = controlador_db.obtenerIdEntidadPorFirmador(idFirmador, pais=pais)
  if not entidad:
    return jsonify({"error": "No se encontro la entidad para el firmador indicado"}), 404

  try:
    idEntidad = int(entidad[0])
  except (TypeError, ValueError):
    return jsonify({"error": "La entidad consultada tiene un id invalido"}), 500

  logoPath = None
  mime = None
  for extension, extensionMime in EXTENSIONES:
    candidato = os.path.join(LOGOS_DIR, pais, f"{idEntidad}{extension}")
    if os.path.isfile(candidato):
      logoPath = candidato
      mime = extensionMime
      break

  if logoPath is None:
    return jsonify({"error": f"No se encontro el logo de la entidad {idEntidad} para el pais {pais}"}), 404

  try:
    with open(logoPath, "rb") as logoFile:
      encoded = base64.b64encode(logoFile.read()).decode('utf-8')
  except OSError as e:
    return jsonify({"error": f"No se pudo leer el logo: {e}"}), 500

  return jsonify({"logo": f"data:{mime};base64,{encoded}"})
