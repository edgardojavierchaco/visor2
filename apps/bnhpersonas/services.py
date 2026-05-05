from .middleware import get_current_user


class AuditService:

    @staticmethod
    def apply(obj, user):

        if user and user.is_authenticated:

            if not getattr(obj, "pk", None):
                obj.usuario_creacion = user

            obj.usuario_modificacion = user

        return obj


class BulkNormalizer:

    @staticmethod
    def apply(obj):

        if hasattr(obj, "normalize"):
            obj.normalize()

        return obj


class BulkService:

    @staticmethod
    def safe_bulk_create(model_class, objects):

        user = get_current_user()

        prepared_objects = []

        for obj in objects:

            # 1. auditoría
            obj = AuditService.apply(obj, user)

            # 2. normalización
            obj = BulkNormalizer.apply(obj)

            prepared_objects.append(obj)

        return model_class.objects.bulk_create(prepared_objects)