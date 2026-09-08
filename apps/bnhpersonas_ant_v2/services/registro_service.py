from django.core.exceptions import ValidationError

class RegistroService:
    @staticmethod
    def sync_actividades(*args, **kwargs):
        raise ValidationError("El antiguo formset fue sustituido por servicios CRUD con alcance y auditoría explícitos.")
