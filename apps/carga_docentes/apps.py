from django.apps import AppConfig


class CargaDocentesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = 'apps.carga_docentes'
    
    def ready(self):
        import apps.carga_docentes.signals
