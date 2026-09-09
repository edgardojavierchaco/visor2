from django.core.exceptions import ValidationError

class BulkService:
    @staticmethod
    def safe_bulk_create(*args, **kwargs):
        raise ValidationError("La importación masiva anterior quedó deshabilitada. Utilice los servicios transaccionales; no omita permisos, versiones y auditoría.")
