import os

import ffmpeg
from flask import Blueprint, request, jsonify
from reconocimiento import getFrames, recognize
from utilities.utilidades import fileCv2, readDataURL

recognition_bp = Blueprint('recognition', __name__, url_prefix="/recognition")


@recognition_bp.route('/verify', methods=['POST'])
def recog():

    testing = request.args.get("testing", "false").lower() == "true"

    if testing:
        documentImage = fileCv2(request.files.get("imagenDocumento", None))
        # personImage = fileCv2(request.files.get("imagenPersona", None))
        personVideoPath = request.form.get("videoPersona", None)
    else:
        data = request.get_json()
        documentImage = readDataURL(data["imagenDocumento"])
        # personImage = readDataURL(data["imagenPersona"])
        personVideoPath = data["videoPersona"]

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

    isSame, result = recognize(frames, documentImage)

    # Delete the normalized video after processing
    if os.path.isfile(video):
        try:
            os.remove(video)
        except Exception as e:
            print(f"Error al eliminar el video normalizado: {e}")

    return jsonify({"similitud": result, "esMismaPersona": isSame}), 200
