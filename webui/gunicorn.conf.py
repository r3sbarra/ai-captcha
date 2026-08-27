"""Production WSGI config for gunicorn (webui extra)."""

bind = "0.0.0.0:5100"
workers = 2
timeout = 30
accesslog = "-"
errorlog = "-"
