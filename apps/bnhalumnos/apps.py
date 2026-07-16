"""Configuracion de la app Django del modulo BNH Alumnos."""

from django.apps import AppConfig


class BnhalumnosConfig(AppConfig):
    """Configuración Django del módulo BNH Alumnos."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.bnhalumnos"
