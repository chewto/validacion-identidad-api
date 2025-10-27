FROM python:3.11-slim-bookworm

RUN apt update && apt install -y python3-opencv libgl1 libopencv-dev python3-pil tesseract-ocr ffmpeg cmake libmariadb-dev-compat libmariadb-dev

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["gunicorn", "-c", "gunicorn_config.py", "main:app"]