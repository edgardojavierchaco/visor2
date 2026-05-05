class AuditStep:

    @staticmethod
    def apply(obj, user):

        if user and user.is_authenticated:

            if not getattr(obj, "pk", None):
                obj.usuario_creacion = user

            obj.usuario_modificacion = user

        return obj