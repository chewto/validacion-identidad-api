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
