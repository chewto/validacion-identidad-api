from flask import Blueprint, request, jsonify
from reconocimiento import recognize

from utilities.utilidades import fileCv2, readDataURL

recognition_bp = Blueprint('recognition', __name__)


@recognition_bp.route('/recognize', methods=['POST'])
def recog():

    testing = request.args.get("testing", "false").lower() == "true"

    if testing:
        documentImage = fileCv2(request.files.get("imagenDocumento", None))
        personImage = fileCv2(request.files.get("imagenPersona", None))
    else:
        data = request.get_json()
        documentImage = readDataURL(data["imagenDocumento"])
        personImage = readDataURL(data["imagenPersona"])

    result = recognize(personImage, documentImage)

    return jsonify({"message": result})
