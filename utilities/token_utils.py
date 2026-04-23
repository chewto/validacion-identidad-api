from functools import wraps
from flask import request, jsonify, current_app
import jwt
import os

ALGORITHM = "HS256"
SECRET_KEY = os.getenv("SECRET_KEY")

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        # El token suele venir en el header 'Authorization'
        if 'Authorization' in request.headers:
            # Esperamos el formato: "Bearer <token>"
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({'message': 'Formato de token inválido'}), 401

        if not token:
            return jsonify({'message': 'Falta el token de sesión'}), 401

        try:
            # Validamos el token
            data = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            # Guardamos los datos del token en el contexto de la petición por si los necesitas
            request.token_data = data 
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'La sesión ha expirado'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Token no válido'}), 401

        return f(*args, **kwargs)
    
    return decorated
