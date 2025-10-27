import multiprocessing
workers = 2 * multiprocessing.cpu_count() + 1
print(workers)
worker_class = 'eventlet'  # Use gevent async workers
worker_connections = 2000  # Maximum concurrent connections per worker

# workers = 3
bind = "0.0.0.0:4000"
