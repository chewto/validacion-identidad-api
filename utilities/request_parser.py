from utilities.utilidades import fileCv2, readDataURL
import cv2
import numpy as np


def _dataURL_to_cv2(dataurl):
    """Convierte un dataURL base64 a un array cv2 (numpy ndarray BGR)."""
    if dataurl is None:
        return None
    # dataURL format: data:image/jpeg;base64,<base64data>
    if ',' in dataurl:
        dataurl = dataurl.split(',')[1]
    import base64
    img_bytes = base64.b64decode(dataurl)
    img_np = np.frombuffer(img_bytes, dtype=np.uint8)
    return cv2.imdecode(img_np, cv2.IMREAD_COLOR)


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
        all_frames_raw = req.files.getlist('allFrames')
        # lectura de imágenes para testing
        persona_data = fileCv2(imagen_persona) if imagen_persona else None
        documento_data = fileCv2(imagen_documento) if imagen_documento else None
        all_frames = [fileCv2(f) for f in all_frames_raw] if all_frames_raw else None
    else:
        body = req.get_json() or {}
        efirma_id = body.get('id')
        imagen_persona = body.get('imagenPersona')
        imagen_documento = body.get('imagen')
        ocr = body.get('ocr') or []
        text_angle = body.get('textAngle')
        tries = int(body.get('tries') or 0)
        all_frames_raw = body.get('allFrames')
        # lectura de imágenes para producción (data URLs)
        persona_data = readDataURL(imagen_persona) if imagen_persona else None
        documento_data = readDataURL(imagen_documento) if imagen_documento else None
        all_frames = [_dataURL_to_cv2(f) for f in all_frames_raw] if all_frames_raw else None

    parsed = {
        'is_testing': is_testing,
        'efirma_id': efirma_id,
        'persona_data': persona_data,
        'documento_data': documento_data,
        'all_frames': all_frames,
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