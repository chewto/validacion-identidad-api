import os

import cv2
import ffmpeg
from flask import Blueprint, request, jsonify
from reconocimiento import extractFaces, faceDetection, getFrames, movementDetection, recognize
from utilities.utilidades import fileCv2, readDataURL
from mrz import read_mrz

recognition_bp = Blueprint('recognition', __name__, url_prefix="/recognition")


@recognition_bp.route('/verify', methods=['POST'])
def recog():

    # testing = request.args.get("testing", "false").lower() == "true"

    documentImagePath = request.form.get("imagenDocumento", None)
    documentImage = cv2.imread(documentImagePath)
    personVideoPath = request.form.get("videoPersona", None)
    # else:
    #     data = request.get_json()
    #     documentImage = readDataURL(data["imagenDocumento"])
    #     # personImage = readDataURL(data["imagenPersona"])
    #     personVideoPath = data["videoPersona"]

    if personVideoPath is None or not os.path.isfile(personVideoPath):
        return jsonify({"error": "No se proporcionó un video válido o el archivo no existe."}), 400

    video_dir = os.path.join('.', 'videos_normalized')
    os.makedirs(video_dir, exist_ok=True)
    video_name = os.path.splitext(os.path.basename(personVideoPath))[0] + '_normalized.mp4'
    video = os.path.join(video_dir, video_name)

    # Build ffmpeg command as a list for subprocess
    try:
        ffmpeg.input(personVideoPath).output(
            video,
            vf="scale='if(gt(iw,640),640,iw)':'if(gt(iw,640),-2,ih)'",
            vcodec='libx264',
            pix_fmt='yuv420p',
            preset='ultrafast',
            crf=28,
            acodec='aac',
            r=str(30),
            movflags='faststart'
        ).run(overwrite_output=True)
    except ffmpeg.Error as e:
        error_msg = e.stderr.decode() if e.stderr else str(e)
        print(f"Error durante la conversión: {error_msg}")
    except Exception as e:
        print(f"Ocurrió un error inesperado durante la conversión: {e}")

    frames = getFrames(video, frameCounter=12)

    isSame, result, bestFrame = recognize(frames, documentImage)

    _, refFace, faces = faceDetection(frames)

    move = movementDetection(refFace, faces)

    extractFace = extractFaces(bestFrame, anti_spoofing=True)

    antiSpoofing = False

    for face in extractFace:
        antiSpoofing = face['isReal']

    # Delete the normalized video after processing
    if os.path.isfile(video):
        try:
            os.remove(video)
        except Exception as e:
            print(f"Error al eliminar el video normalizado: {e}")

    return jsonify({"similitud": result, "esMismaPersona": isSame, "movimiento": move, "antiSpoofing": antiSpoofing}), 200



@recognition_bp.route('/mrz', methods=['POST'])
def mrzReader():
    # 1. Obtienes la ruta (ej: "C:/fotos/pasaporte.jpg" o "/tmp/img.png")
    ruta_imagen = request.form.get('imagen')

    if not ruta_imagen:
        return jsonify({"error": "No se proporcionó la ruta de la imagen"}), 400

    try:
        mrz = read_mrz(ruta_imagen)

        if mrz is None:
            return jsonify({"error": "No se detectó MRZ en la imagen"}), 404

        data = mrz.to_dict()
        raw = data['raw_text']

        return jsonify({"mrz": raw, "data": data})

    except Exception as e:
        return jsonify({"error": f"Error procesando MRZ: {str(e)}"}), 500
