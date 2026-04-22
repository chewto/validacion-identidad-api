import datetime
from flask import Blueprint, request, jsonify
from utilities.token_utils import token_required
import jwt

secret_key = 'secret_key'
ALGORITHM = "HS256"

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/generate-token', methods=['GET'])
def generateToken():
    """Genera el pase de visitante efímero"""
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