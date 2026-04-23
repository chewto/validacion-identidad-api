import datetime
from flask import Blueprint, request, jsonify
from utilities.token_utils import token_required
import jwt
import os

secret_key = 'secret_key'
ALGORITHM = "HS256"
API_KEY = os.getenv("API_KEY")

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/generate-token', methods=['GET'])
def generateToken():
    """Genera el pase de visitante efímero"""

    client_api_key = request.headers.get('x-api-key')
    
    if client_api_key != API_KEY:
        return jsonify({'message': 'Acceso no autorizado'}), 403

    expiration = datetime.datetime.utcnow() + datetime.timedelta(minutes=20)
    
    payload = {
        'exp': expiration,
        'iat': datetime.datetime.utcnow(),
        'purpose': 'ekyc_flow'
    }
    
    token = jwt.encode(payload, secret_key, algorithm=ALGORITHM)
    
    return jsonify({
        'token': token,
        'expires_at': expiration.strftime("%Y-%m-%d %H:%M:%S")
    })