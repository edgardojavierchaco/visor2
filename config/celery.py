import os
from celery import Celery

# ======================================================
# DJANGO SETTINGS
# ======================================================

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    os.environ.get(
        "DJANGO_SETTINGS_MODULE",
        "config.settings.local"
    )
)

# ======================================================
# CELERY APP
# ======================================================

app = Celery("visor2")

# ======================================================
# LOAD DJANGO SETTINGS
# ======================================================

app.config_from_object(
    "django.conf:settings",
    namespace="CELERY"
)

# ======================================================
# AUTODISCOVER TASKS
# ======================================================

app.autodiscover_tasks()

# ======================================================
# EXTRA SAFE CONFIG
# ======================================================

app.conf.update(
    broker_connection_retry_on_startup=True,
)