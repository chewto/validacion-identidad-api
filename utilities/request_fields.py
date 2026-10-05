"""Lectura del body de los endpoints de firma en JSON o form-data.

Historial
---------
`/validation/standalone` nacio como un endpoint multipart/form-data con campos
planos en snake_case (`front_country_check`, `validation_percent`, ...). La SPA
dejo de construir FormData y paso a mandar el payload JSON anidado del que
tambien se sirve `/validation/type-3`, pero el backend nunca se adapto: con un
body JSON, `request.form` viene vacio y todas las lecturas devuelven `None`.

Para no reescribir la logica de validacion de `standalone` (y poder seguir
atendiendo a callers legacy en form-data) este modulo traduce el payload JSON
a la forma plana esperada, replicando los mismos encoding que el FormData
historico de la SPA:

    countryCheck (boolean) -> 'OK' | '!OK'
    isExpired    (boolean) -> 'OK' | '!OK'   (invertido: true = expirado = !OK)
    face         (boolean) -> 'OK' | '!OK'
"""
from flask import request


def request_json():
    """Body parseado como dict si el cliente mando JSON, o None."""
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else None


def body_fields():
    """Campos crudos del body: dict JSON si hay JSON, si no form-data."""
    data = request_json()
    if data is not None:
        return data
    return request.form


def _dict(value):
    return value if isinstance(value, dict) else {}


def _check(value):
    """Normaliza un check a los sentinels 'OK'/'!OK' que espera standalone."""
    if isinstance(value, str):
        normalized = value.strip().upper()
        if normalized in ("OK", "TRUE", "1", "SI", "SÍ"):
            return "OK"
        return "!OK"
    return "OK" if bool(value) else "!OK"


def _expired(value):
    """Codifica vencimiento al sentinels legacy: 'OK' = no vencido.

    En el FormData historico la SPA mandaba `isExpired ? "!OK" : "OK"`, de modo
    que `null`/ausente producia 'OK'. Se replica tal cual.
    """
    if value is None:
        return "OK"
    if isinstance(value, str):
        normalized = value.strip().upper()
        if normalized in ("!OK", "NOK", "TRUE", "1", "VENCIDO"):
            return "!OK"
        return "OK"
    return "!OK" if value else "OK"


def _norm_str(value):
    """Vacío/ausente -> sentinels legacy 'NULL' (dispara el fallback OCR)."""
    if value is None:
        return "NULL"
    text = str(value).strip()
    return text if text else "NULL"


def _truthy_check(value):
    """Presencia de un dato (codigo de barras): vacío/nulo = '!OK'."""
    if isinstance(value, str):
        return "OK" if value.strip() else "!OK"
    return "OK" if value else "!OK"


def _side(side):
    """Campos planos de un lado del documento."""
    side = _dict(side)
    return {
        "code": side.get("code"),
        "country": side.get("country"),
        "country_check": _check(side.get("countryCheck")),
        "type": side.get("type"),
        "type_check": _check(side.get("typeCheck")),
        "is_expired": _expired(side.get("isExpired")),
        "tries": side.get("tries"),
    }


def signature_payload_to_form(payload):
    """Traduce el payload JSON de firma a los campos planos legacy."""
    payload = _dict(payload)
    info = _dict(payload.get("info"))
    document = _dict(payload.get("documentValidation"))
    signer = _dict(payload.get("signInfo"))
    liveness = _dict(payload.get("livenessTest"))
    params = _dict(payload.get("params"))

    ocr = _dict(document.get("ocr"))
    ocr_data = _dict(ocr.get("data"))
    ocr_percent = _dict(ocr.get("percentage"))
    mrz = _dict(document.get("mrz"))
    mrz_data = _dict(mrz.get("data"))
    mrz_percent = _dict(mrz.get("percentages"))

    sides = _dict(document.get("sides"))
    front = _side(sides.get("front"))
    back = _side(sides.get("back"))

    return {
        # identidad (signInfo)
        "nombres": _norm_str(signer.get("nombre")),
        "apellidos": _norm_str(signer.get("apellido")),
        "numero_documento": _norm_str(signer.get("documento")),
        "email": signer.get("correo") or "",
        # dispositivo / evidencia (info)
        "tipo_documento": info.get("tipoDocumento") or "",
        "dispositivo": info.get("dispositivo"),
        "navegador": info.get("navegador"),
        "ip": info.get("ip"),
        "latitud": info.get("latitud"),
        "longitud": info.get("longitud"),
        "hora": info.get("hora"),
        "fecha": info.get("fecha"),
        "foto_persona": info.get("foto_persona"),
        "anverso": info.get("anverso"),
        "reverso": info.get("reverso"),
        # carpetas de la prueba de vida: la SPA nunca las mando
        "carpeta_entidad_prueba_vida": None,
        "carpeta_usuario_prueba_vida": None,
        # pruebas
        "movement_test": liveness.get("movimiento"),
        "video_hash": liveness.get("videoHash"),
        # OCR
        "porcentaje_nombre_ocr": ocr_percent.get("name"),
        "porcentaje_apellido_ocr": ocr_percent.get("lastName"),
        "porcentaje_documento_ocr": ocr_percent.get("ID"),
        "nombre_ocr": ocr_data.get("name"),
        "apellido_ocr": ocr_data.get("lastName"),
        "documento_ocr": ocr_data.get("ID"),
        # MRZ / codigo de barras
        "mrz": mrz.get("code"),
        "mrz_name": mrz_data.get("name"),
        "mrz_lastname": mrz_data.get("lastName"),
        "mrz_name_percent": mrz_percent.get("name"),
        "mrz_lastname_percent": mrz_percent.get("lastName"),
        "codigo_barras": _truthy_check(document.get("barcode")),
        # lados del documento
        "front_code": front["code"],
        "front_country": front["country"],
        "front_country_check": front["country_check"],
        "front_type": front["type"],
        "front_type_check": front["type_check"],
        "front_isExpired": front["is_expired"],
        "front_tries": front["tries"],
        "back_code": back["code"],
        "back_country": back["country"],
        "back_country_check": back["country_check"],
        "back_type": back["type"],
        "back_type_check": back["type_check"],
        "back_isExpired": back["is_expired"],
        "back_tries": back["tries"],
        # rostro / parametros de validacion
        "face": _check(document.get("face")),
        "confidence": document.get("confidence"),
        "face_tries": params.get("faceTries"),
        "validation_attendance": params.get("validationAttendance"),
        "validation_percent": params.get("validationPercent"),
        # fallo explicito (la SPA actual no lo envia)
        "failed": payload.get("failed"),
        "failed_back": _check(payload["failedBack"]) if "failedBack" in payload else None,
        "failed_front": _check(payload["failedFront"]) if "failedFront" in payload else None,
        "callback": payload.get("callback"),
    }


def standalone_fields():
    """Campos en la forma legacy que espera `/validation/standalone`.

    - form-data  -> se devuelve tal cual (compatibilidad con callers legacy).
    - JSON       -> se traduce del payload de firma a campos planos.
    """
    payload = request_json()
    if payload is None:
        return request.form
    return signature_payload_to_form(payload)
