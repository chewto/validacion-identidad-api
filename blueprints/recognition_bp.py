import os

import ffmpeg
from flask import Blueprint, request, jsonify
# from reconocimiento import recognize

from reconocimiento import getFrames, recognize
from utilities.utilidades import fileCv2, readDataURL
import cv2

recognition_bp = Blueprint('recognition', __name__, url_prefix="/recognition")


@recognition_bp.route('/verify', methods=['POST'])
def recog():

    testing = request.args.get("testing", "false").lower() == "true"

    if testing:
        documentImage = fileCv2(request.files.get("imagenDocumento", None))
        # personImage = fileCv2(request.files.get("imagenPersona", None))
        personVideoPath = request.form.get("videoPersona", None)
        print(personVideoPath)
    else:
        data = request.get_json()
        documentImage = readDataURL(data["imagenDocumento"])
        # personImage = readDataURL(data["imagenPersona"])
        personVideoPath = data["videoPersona"]

    print(personVideoPath)

    video_dir = os.path.join('.', 'videos_normalized')
    os.makedirs(video_dir, exist_ok=True)
    video_name = os.path.splitext(os.path.basename(personVideoPath))[0] + '_normalized.mp4'
    print(video_name)
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

    # frames_dir = os.path.join('.', 'frames')
    # os.makedirs(frames_dir, exist_ok=True)
    # for idx, frame in enumerate(frames):
    #     frame_path = os.path.join(frames_dir, f'frame_{idx:03d}.jpg')
    #     # frame is a numpy array (BGR), save with cv2
    #     cv2.imwrite(frame_path, frame)

    result = recognize(frames, documentImage)

    print(result)
    return jsonify({"message": 'result'})
