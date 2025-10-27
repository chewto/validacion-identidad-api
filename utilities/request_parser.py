from utilities.utilidades import fileCv2, readDataURL


def _parse_request(req):
    """Normaliza y unifica la lectura de datos tanto para testing (form/files)
    como para peticiones normales (JSON con dataURL)."""
    is_testing = req.args.get('testing', 'false').lower() == 'true'

    if is_testing:
        body = req.form
        efirma_id = body.get('id')
        imagen_persona = req.files.get('imagenPersona')
        imagen_documento = req.files.get('imagen')
        ocr_raw = body.get('ocr')
        ocr = ocr_raw.split(',') if ocr_raw else []
        text_angle = body.get('textAngle')
        tries = int(body.get('tries') or 0)
        # lectura de imágenes para testing
        persona_data = fileCv2(imagen_persona) if imagen_persona else None
        documento_data = fileCv2(imagen_documento) if imagen_documento else None
    else:
        body = req.get_json() or {}
        efirma_id = body.get('id')
        imagen_persona = body.get('imagenPersona')
        imagen_documento = body.get('imagen')
        ocr = body.get('ocr') or []
        text_angle = body.get('textAngle')
        tries = int(body.get('tries') or 0)
        # lectura de imágenes para producción (data URLs)
        persona_data = readDataURL(imagen_persona) if imagen_persona else None
        documento_data = readDataURL(imagen_documento) if imagen_documento else None

    parsed = {
        'is_testing': is_testing,
        'efirma_id': efirma_id,
        'persona_data': persona_data,
        'documento_data': documento_data,
        'lado_documento': body.get('ladoDocumento'),
        'tipo_documento': body.get('tipoDocumento'),
        'nombre': body.get('nombre'),
        'apellido': body.get('apellido'),
        'numero_documento': body.get('documento'),
        'user_country': body.get('country'),
        'tries': tries,
        'ocr': ocr,
        'text_angle': text_angle,
    }

    return parsed