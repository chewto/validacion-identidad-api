FROM python:3.11-slim-bookworm

# Instalamos las dependencias del sistema
# Se añade build-essential para tener g++ y gcc
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    cmake \
    python3-opencv \
    libgl1 \
    libopencv-dev \
    python3-pil \
    tesseract-ocr \
    ffmpeg \
    libmariadb-dev-compat \
    libmariadb-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app

# Copiamos solo los requerimientos primero (buena práctica para la caché de Docker)
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["gunicorn", "-c", "gunicorn_config.py", "main:app"]