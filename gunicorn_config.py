# Gunicorn configuration file
bind = "127.0.0.1:8080"
workers = 4
errorlog = "/mnt/nvme/gablab_WD/flask_app/gablab_finance/gunicorn-error.log"
accesslog = "/mnt/nvme/gablab_WD/flask_app/gablab_finance/gunicorn-access.log"
capture_output = True
timeout = 120
