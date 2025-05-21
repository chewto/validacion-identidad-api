from flask import Blueprint, Flask, render_template_string, request
from PIL import Image
import io, time, base64
import cv2
import numpy as np
import easyocr

test_bp = Blueprint('test', __name__, url_prefix='/test')

TEMPLATE = """
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>OCR con EasyOCR y Métricas Optimizadas</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    .img-preview { max-width: 100%; height: auto; border: 1px solid #ddd; padding: 5px; }
    .metric { font-size: .9rem; }
  </style>
</head>
<body class="bg-light">
  <div class="container py-4">
    <h1 class="mb-4">OCR con EasyOCR y Métricas Optimizadas</h1>
    <form method="POST" enctype="multipart/form-data" class="card p-4 mb-4 bg-white">
      <div class="mb-3">
        <label class="form-label">Subir imagen</label>
        <input type="file" class="form-control" name="image" required accept="image/*">
      </div>
      <div class="mb-3">
        <label for="resolution" class="form-label">Resolución para OCR: <span id="resVal">{{ defaults.resolution }}</span> px</label>
        <input type="range" class="form-range" id="resolution" name="resolution"
               min="300" max="{{ defaults.max_width }}" value="{{ defaults.resolution }}"
               oninput="resVal.innerText=this.value">
      </div>
      <fieldset class="mb-3">
        <legend class="col-form-label">Filtros (pueden combinarse)</legend>
        {% for f in filters %}
        <div class="form-check form-check-inline">
          <input class="form-check-input" type="checkbox" id="f_{{ f }}" name="filter_{{ f }}"
                 {% if defaults['filter_' + f] %}checked{% endif %}>
          <label class="form-check-label" for="f_{{ f }}">{{ labels[f] }}</label>
        </div>
        {% endfor %}
      </fieldset>
      <button type="submit" class="btn btn-primary">Realizar OCR</button>
    </form>

    {% if processed %}
    <div class="card p-3 bg-white mb-4">
      <h5>Tiempos de proceso</h5>
      <p class="metric mb-1">Carga imagen: {{ '%.3f'|format(times.load) }} s</p>
      <p class="metric mb-1">Redimensionado: {{ '%.3f'|format(times.resize) }} s</p>
      <p class="metric mb-1">Aplicar filtros: {{ '%.3f'|format(times.filter) }} s</p>
      <p class="metric mb-1">OCR: {{ '%.3f'|format(times.ocr) }} s</p>
      <p class="metric mb-1">Anotación: {{ '%.3f'|format(times.annotate) }} s</p>
      <p class="metric mb-1">Codificar Base64: {{ '%.3f'|format(times.encode) }} s</p>
      <p class="metric fw-bold">Tiempo total: {{ '%.3f'|format(times.total) }} s</p>
    </div>

    <div class="row">
      <div class="col-md-6">
        <h5>Imagen Original</h5>
        <img src="data:image/png;base64,{{ images.original }}" class="img-preview mb-3">
      </div>
      <div class="col-md-6">
        <h5>Imagen Procesada con OCR</h5>
        <img src="data:image/png;base64,{{ images.annotated }}" class="img-preview mb-3">
      </div>
    </div>

    <div class="card p-3 bg-white mb-4">
      <h5>Métricas de tamaño</h5>
      <p class="metric mb-1">Original: {{ '%.1f'|format(metrics.original_kb) }} KB</p>
      <p class="metric mb-1">Para OCR: {{ '%.1f'|format(metrics.resized_kb) }} KB ({{ metrics.res_w }}×{{ metrics.res_h }} px)</p>
      <p class="metric mb-1">Procesada: {{ '%.1f'|format(metrics.processed_kb) }} KB</p>
    </div>

    <div class="card p-3 bg-white">
      <h5>Texto Reconocido</h5>
      <pre>{{ metrics.text }}</pre>
    </div>
    {% endif %}
  </div>
</body>
</html>
"""

filters = ['gray','thresh','blur','hist','sharp']
labels = {
    'gray': 'Escala de grises',
    'thresh': 'Umbralización',
    'blur': 'Desenfoque mediano',
    'hist': 'Equalización de histograma (CLAHE)',
    'sharp': 'Enfoque (Sharpen)'
}

reader = easyocr.Reader(['es'], gpu=False)

def pil_to_base64(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return base64.b64encode(buf.getvalue()).decode('ascii')

@test_bp.route('/', methods=['GET','POST'])
def index():
    defaults = {'resolution': 1080, 'max_width': 4000}
    for f in filters:
        defaults['filter_' + f] = (f == 'sharp')  # Activar sharpen por defecto

    if request.method == 'POST':
        t0 = time.time()
        # Carga rápida con OpenCV
        file_bytes = request.files['image'].read()
        np_arr = np.frombuffer(file_bytes, np.uint8)
        arr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        load_end = time.time()

        # Guardar original base64 directamente
        original_kb = len(file_bytes) / 1024
        original_b64 = base64.b64encode(file_bytes).decode('ascii')

        # Resolución y filtros
        w0, h0 = arr.shape[1], arr.shape[0]
        target_w = int(request.form.get('resolution', defaults['resolution']))
        defaults['resolution'] = target_w
        defaults['max_width'] = w0
        applied = {}
        for f in filters:
            applied[f] = ('filter_' + f) in request.form
            defaults['filter_' + f] = applied[f]

        # Redimensionado eficiente
        if target_w < w0:
            h1 = int(h0 * target_w / w0)
            resized = cv2.resize(arr, (target_w, h1), interpolation=cv2.INTER_AREA)
        else:
            resized = arr
            h1 = h0
        resize_end = time.time()
        resized_kb = len(cv2.imencode('.png', resized)[1].tobytes()) / 1024

        # Filtros (mantener separado para claridad)
        proc = resized.copy()
        if applied['gray']:
            proc = cv2.cvtColor(proc, cv2.COLOR_BGR2GRAY)
        if applied['hist']:
            gray = proc if proc.ndim == 2 else cv2.cvtColor(proc, cv2.COLOR_BGR2GRAY)
            proc = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8)).apply(gray)
        if applied['sharp']:
            kernel = np.array([[0,-1,0],[-1,5,-1],[0,-1,0]])
            proc = cv2.filter2D(proc, -1, kernel)
        if applied['blur']:
            proc = cv2.medianBlur(proc, 3)
        if applied['thresh']:
            src = proc if proc.ndim > 2 else proc
            _, proc = cv2.threshold(src, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        filter_end = time.time()

        enc = proc if proc.ndim == 3 else cv2.cvtColor(proc, cv2.COLOR_GRAY2BGR)
        processed_kb = len(cv2.imencode('.png', enc)[1].tobytes()) / 1024

        # OCR (detail=0, parámetros de contraste por defecto)
        
        ocr_start = time.time()
        results = reader.readtext(enc, detail=0)
        ocr_end = time.time()

        # Anotación (sólo conversión de espacio de color)
        ann = cv2.cvtColor(enc, cv2.COLOR_BGR2RGB)
        text_out = "\n".join(results)
        annotate_end = time.time()

        # Codificar anotada
        encode_start = time.time()
        annotated_b64 = base64.b64encode(cv2.imencode('.PNG', ann)[1]).decode('ascii')
        encode_end = time.time()

        times = {
            'load': load_end - t0,
            'resize': resize_end - load_end,
            'filter': filter_end - resize_end,
            'ocr': ocr_end - ocr_start,
            'annotate': annotate_end - ocr_end,
            'encode': encode_end - annotate_end,
            'total': encode_end - t0
        }

        metrics = {
            'original_kb': original_kb,
            'resized_kb': resized_kb,
            'processed_kb': processed_kb,
            'res_w': target_w,
            'res_h': h1,
            'text': text_out
        }
        images = {'original': original_b64, 'annotated': annotated_b64}

        return render_template_string(
            TEMPLATE,
            processed=True,
            images=images,
            metrics=metrics,
            times=times,
            defaults=defaults,
            filters=filters,
            labels=labels
        )

    return render_template_string(
        TEMPLATE,
        processed=False,
        defaults=defaults,
        filters=filters,
        labels=labels
    )
