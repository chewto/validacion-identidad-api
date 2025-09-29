import os
import sqlite3
import controlador_db
import requests
import base64
import json
import cv2
import numpy as np
import argparse

parser = argparse.ArgumentParser(description="Revalidación de identidad por lotes")
parser.add_argument("--initialId", type=int, required=True, help="ID inicial para comenzar la revalidación")
parser.add_argument("--revalidationBatch", type=int, default=1, help="Cantidad de registros a procesar en el lote")
args = parser.parse_args()

initialId = args.initialId
revalidationBatch = args.revalidationBatch

# Asegúrate de que la carpeta para los crops exista
output_dir = "./recortes"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

validations = controlador_db.selectValidations(f'''
  SELECT docu.nombres, docu.apellidos, docu.numero_documento, docu.tipo_documento, 
         evi.anverso_documento, evi.reverso_documento, evi.foto_usuario, docu.id_usuario_efirma, docu.id
  FROM pki_validacion.documento_usuario AS docu
  INNER JOIN pki_validacion.evidencias_usuario AS evi ON evi.id = docu.id_evidencias
  WHERE docu.id >= {initialId} LIMIT {revalidationBatch}
''', ())
# Función para guardar crops
def save_crop(base64_image, crop, label, side, id):
  img_data = base64.b64decode(base64_image.split(",")[1])
  np_arr = np.frombuffer(img_data, np.uint8)
  img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

  if img is None:
    print(f"Error: La imagen no se pudo decodificar correctamente.")
    return

  x, y, w, h = crop['x'], crop['y'], crop['width'], crop['height']

  if x < 0 or y < 0 or w <= 0 or h <= 0:
    print(f"Advertencia: Coordenadas no válidas para el crop en {side} {label}: {crop}")
    return

  crop_img = img[y:y+h, x:x+w]

  if crop_img.size != 0:
    # Crear carpeta por id si no existe
    id_dir = os.path.join(output_dir, str(id))
    if not os.path.exists(id_dir):
      os.makedirs(id_dir)
    filename = f"{side}_{label}.jpg"
    file_path = os.path.join(id_dir, filename)
    cv2.imwrite(file_path, crop_img)
    print(f"Guardado: {file_path}")
  else:
    print(f"Advertencia: El recorte está vacío para {side} {label} en las coordenadas {crop}")

# Procesamiento de cada validación
for validation in validations:
    id = validation[8]
    name = validation[0]
    lastname = validation[1]
    documentNumber = validation[2]
    documentType = validation[3]

    # Convertir blob a base64
    def convert_to_base64(blob):
        return f"data:image/jpeg;base64,{base64.b64encode(blob).decode('utf-8')}"

    frontImage = convert_to_base64(validation[4])
    backImage = convert_to_base64(validation[5])
    selfieImage = convert_to_base64(validation[6])

    signerId = validation[7]
    countrySelect = controlador_db.selectData(f'''SELECT pais.codigo, pais.yolo_labels, ent.porcentaje_acierto
        FROM pki_firma_electronica.firmador_pki AS firmador
        INNER JOIN pki_firma_electronica.firma_electronica_pki AS firma ON firma.id = firmador.firma_electronica_id
        INNER JOIN usuarios.usuarios AS usu ON usu.id = firma.usuario_id
        INNER JOIN usuarios.entidades AS ent ON usu.entity_id = ent.entity_id
        INNER JOIN pki_validacion.pais AS pais ON pais.codigo = usu.pais
        WHERE firmador.id = {signerId}''', ())

    country = countrySelect[0]
    yoloLabels = countrySelect[1]
    validationPercent = countrySelect[2]

    sides = {
        "front": {},
        "back": {}
    }

    # OCR para las imágenes de anverso y reverso
    def ocr_request(image, side):
        response = requests.post("http://127.0.0.1:4500/ocr", json={"image": image})
        sides[side]['ocr'] = json.loads(response.text)
        sides[side]['image'] = image

    ocr_request(frontImage, "front")
    ocr_request(backImage, "back")

    documentValidation = {'front': {}, 'back': {}}

    # Validación de documentos usando OCR y selfie
    for key in sides:
        endPoint = "anverso" if key == 'front' else "reverso"
        payload = {
            "imagenPersona": selfieImage,
            "imagen": sides[key]['image'],
            "nombre": name,
            "apellido": lastname,
            "documento": documentNumber,
            "tipoDocumento": documentType,
            "ocr": sides[key]['ocr']['ocr'],
            "ladoDocumento": endPoint,
            "tries": 0,
            "country": country,
            "textAngle": sides[key]['ocr']['textAngle']
        }
        response = requests.post(f"http://127.0.0.1:4000/ocr/{endPoint}", json=payload)
        documentValidation[key] = json.loads(response.text)

    # Revalidación del documento
    response = requests.post("http://127.0.0.1:4000/validation/revalidacion", json={
        "front": documentValidation['front'],
        "back": documentValidation['back'],
        "validationPercent": validationPercent,
        "documentType": documentType
    })

    resJson = json.loads(response.text)
    state = resJson['state']
    checkValues = resJson['checkValues']

    # Procesamiento de crops
    for val in documentValidation:
        payload = {
            "labels": yoloLabels,
            "image": documentValidation[val]['image'],
            "country": country
        }
        response = requests.post("http://127.0.0.1:4000/document/detection", json=payload)
        
        if response.status_code == 200:
            crops = json.loads(response.text)
            print(f"Crops detectados para {val}: {crops}")

            for crop in crops:
                print(f"Procesando crop: {crop}")
                label = crop.get('label', 'unknown')
                y1, y2 = crop['crop'][0]
                x1, x2 = crop['crop'][1]
                x = x1
                y = y1
                w = x2 - x1
                h = y2 - y1
                crop_dict = {'x': x, 'y': y, 'width': w, 'height': h}
                save_crop(documentValidation[val]['image'], crop_dict, label, val, id)
        else:
            print(f"Error en la solicitud de detección para {val}: {response.status_code}")

    columns = ('revalidacion_registro.revalidacion', 'revalidacion_registro.id_recortes', 'revalidacion_registro.estado')
    table = 'pki_validacion.revalidacion_registro'
    # Asignar valores válidos para los campos requeridos
    # Convert checkValues to JSON string to avoid constraint errors
    revalidacion_value = json.dumps(checkValues, ensure_ascii=False)
    id_recortes_value = id  # asigna el id de recortes si lo tienes
    estado_value = state  # o el estado correspondiente
    values = (revalidacion_value, id_recortes_value, estado_value)
    controlador_db.insertTabla(columns, table, values)
    print(f"finalizada revalidacion id: {id}")
