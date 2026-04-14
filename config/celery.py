import os
from celery import Celery

# Toma el settings desde variable de entorno (clave para prod)
os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    os.environ.get("DJANGO_SETTINGS_MODULE", "config.settings.local")
)

app = Celery("visor2")

# Lee configuración desde Django (CELERY_*)
app.config_from_object("django.conf:settings", namespace="CELERY")

# Descubre tasks automáticamente
app.autodiscover_tasks()

# Configuración robusta para producción
app.conf.update(
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,
    task_track_started=True,
)