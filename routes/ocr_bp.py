
from flask import Blueprint, request, jsonify

ocrBp = Blueprint('ocr', __name__)

@ocrBp.route('/ocr-test', methods=['POST'])
def prueba():
  return 'test'