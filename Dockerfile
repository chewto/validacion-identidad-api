FROM python:3.10.14-bookworm

# RUN apt update && apt install ffmpeg libsm6 libxext6 -y

RUN apt update && apt install -y python3-opencv libgl1 libopencv-dev python3-pil tesseract-ocr ffmpeg 

WORKDIR /usr/src/app

# RUN python3 -m venv entorno_v
# RUN . ./entorno_v/bin/activate


COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .


CMD [ "python", "./main.py" ]