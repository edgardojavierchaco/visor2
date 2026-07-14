from django.core.exceptions import PermissionDenied
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.sirtee.services.permisos import PermisosSirtee

class PermisoSirteeMixin(
    LoginRequiredMixin
):
    permiso = None

    def dispatch(
        self,
        request,
        *args,
        **kwargs
    ):

        if self.permiso is None:

            raise PermissionDenied(
                "Permiso no configurado"
            )

        if not self.permiso(
            request.user
        ):
            raise PermissionDenied(
                "No tiene permisos SIRTEE"
            )

        return super().dispatch(
            request,
            *args,
            **kwargs
        )



class MapaSirteeMixin(
    PermisoSirteeMixin
):
    permiso = (
        PermisosSirtee.puede_ver_mapa
    )
    

class IndicadoresSirteeMixin(
    PermisoSirteeMixin
):
    permiso = (
        PermisosSirtee.puede_ver_indicadores
    )


class RelevamientosSirteeMixin(
    PermisoSirteeMixin
):
    permiso = (
        PermisosSirtee.puede_ver_relevamientos
    )
    

class HallazgosSirteeMixin(
    PermisoSirteeMixin
):
    permiso = (
        PermisosSirtee.puede_ver_hallazgos
    )


class IntervencionesSirteeMixin(
    PermisoSirteeMixin
):
    permiso = (
        PermisosSirtee.puede_ver_intervenciones
    )