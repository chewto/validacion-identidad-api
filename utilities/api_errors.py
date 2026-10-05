"""Shape unico de error para los endpoints nuevos.

El frontend (pki-validacion-identidad) lee `error.code` del body
`{ "error": { "code", "message" } }` y tolera `{ "code", "message" }` plano
como fallback. Ante un 403 sin codigo asume VPN_DETECTED y ante un 400 sin
codigo asume LOCATION_REQUIRED, asi que conviene siempre mandar el codigo.
"""
from flask import jsonify

LOCATION_REQUIRED = "LOCATION_REQUIRED"
LOCATION_MISMATCH = "LOCATION_MISMATCH"
LOCATION_UNAVAILABLE = "LOCATION_UNAVAILABLE"
VPN_DETECTED = "VPN_DETECTED"
PROXY_DETECTED = "PROXY_DETECTED"
INVALID_PARAMS = "INVALID_PARAMS"

MESSAGES = {
    LOCATION_REQUIRED: (
        "Tu ubicación es requerida para completar la firma. "
        "Activa la ubicación e inténtalo de nuevo."
    ),
    LOCATION_MISMATCH: (
        "Tu ubicación no coincide con la región permitida para esta firma."
    ),
    LOCATION_UNAVAILABLE: (
        "No pudimos verificar tu ubicación. Inténtalo de nuevo."
    ),
    VPN_DETECTED: "Se detectó uso de VPN. Desactívala para continuar.",
    PROXY_DETECTED: "Se detectó uso de proxy. Desactívalo para continuar.",
    INVALID_PARAMS: "Se requiere hash o efirmaId.",
}


def error_response(code, status=400, message=None):
    """Devuelve (body, status) con el shape `{ "error": { "code", "message" } }`."""
    text = message or MESSAGES.get(code, "No se pudo completar la operación.")
    return jsonify({"error": {"code": code, "message": text}}), status
