import os


bind = f"0.0.0.0:{os.getenv('PORT', '5000')}"

workers = int(os.getenv("WEB_CONCURRENCY", "2"))
threads = int(os.getenv("GUNICORN_THREADS", "4"))
timeout = int(os.getenv("GUNICORN_TIMEOUT", "120"))

worker_class = "gthread"

# Cloud platforms collect stdout/stderr. These defaults also make local Docker
# logs visible through `docker compose logs`.
accesslog = os.getenv("GUNICORN_ACCESS_LOG", "-")
errorlog = os.getenv("GUNICORN_ERROR_LOG", "-")

loglevel = os.getenv("LOG_LEVEL", "info")
