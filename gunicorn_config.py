import multiprocessing
workers = 2 * multiprocessing.cpu_count() + 1
print(workers)
worker_class = 'eventlet'  # Use gevent async workers
worker_connections = 2000  # Maximum concurrent connections per worker
timeout = 30
graceful_timeout = 30
keepalive = 2

max_requests = 1000
max_requests_jitter = 50

...
# Logging Settings
accesslog = "/logs_python/app-python/gunicorn_access.log"  # Log HTTP requests to a file
errorlog = "/logs_python/app-python/gunicorn_error.log"  # Log errors to a file
loglevel = "info"  # Set log verbosity (debug, info, warning, error, critical)


# workers = 3
bind = "0.0.0.0:4000"
