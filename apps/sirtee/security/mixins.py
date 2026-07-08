from django.core.exceptions import PermissionDenied
from apps.sirtee.security.permissions import SirteePermissions


class SirteePermissionMixin:

    required_permission = None

    def dispatch(self, request, *args, **kwargs):

        perms = SirteePermissions(request.user)

        if self.required_permission:
            if not getattr(perms, self.required_permission)():
                raise PermissionDenied("Acceso denegado")

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        qs = super().get_queryset()
        perms = SirteePermissions(self.request.user)

        model = self.model.__name__.lower()

        if model == "relevamiento":
            return perms.filter_relevamientos(qs)

        if model == "hallazgo":
            return perms.filter_hallazgos(qs)

        if model == "intervencion":
            return perms.filter_intervenciones(qs)

        return qs