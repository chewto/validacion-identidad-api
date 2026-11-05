# OJO con el WebSocket de progreso (utilities/ws_server.py):
# el servidor WS vive dentro del proceso Flask, así que sólo es correcto con UN
# worker (`WS_ENABLED=1` explícito). Con varios workers, el estado de
# suscripciones no se comparte: un mensaje emitido en otro worker se pierde y
# sólo uno puede tomar el puerto. Por eso, con `WS_ENABLED` sin definir (auto),
# el WS queda deshabilitado bajo gunicorn y el frontend usa `GET /progress`.
# Además, el hilo asyncio junto a `worker_class = 'eventlet'` (que monkey-patcha
# sockets/hilos) no es una combinación probada: si necesitás WS en producción,
# evaluá `worker_class = 'gthread'` y un único worker, o correr el WS aparte.
workers = 3
worker_class = 'eventlet'  # Use gevent async workers
worker_connections = 2000  # Maximum concurrent connections per worker
timeout = 30
graceful_timeout = 30
keepalive = 2

max_requests = 1000
max_requests_jitter = 50

...
accesslog = "/Logs/ekyc/gunicorn_access.log"  # Log HTTP requests to a file
errorlog = "/Logs/ekyc/gunicorn_error.log"  # Log errors to a file
loglevel = "info"  # Set log verbosity (debug, info, warning, error, critical)


# workers = 3
bind = "0.0.0.0:4000"
