from django.core.exceptions import PermissionDenied


class SirteePermissionMixin:

    permiso_requerido = None

    def dispatch(self, request, *args, **kwargs):

        if not request.user.is_authenticated:
            raise PermissionDenied

        permiso = type(self).permiso_requerido

        if permiso and not permiso(request.user):
            raise PermissionDenied(
                "No posee permisos para acceder."
            )

        return super().dispatch(request, *args, **kwargs)