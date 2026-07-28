from django.apps import AppConfig


# Configuracion de la app Django de Padron Interno.
# Django usa esta clase para conocer el nombre importable del modulo.
class PadroninternoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.padroninterno'  # Si está dentro de la carpeta apps
