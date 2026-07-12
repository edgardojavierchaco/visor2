# apps/sirtee/permissions.py

from django.core.exceptions import PermissionDenied

from apps.sirtee.services.permisos import PermisosSirtee



class BaseSirteePermission:
    """
    Clase base de permisos SIRTEE.
    """

    message = (
        "No posee permisos "
        "para acceder a este recurso"
    )


    @classmethod
    def has_permission(
        cls,
        user
    ):

        if not user.is_authenticated:

            return False


        return False



# ======================================================
# MAPA
# ======================================================

class PuedeVerMapa(BaseSirteePermission):

    message = (
        "No posee permisos "
        "para acceder al Mapa"
    )


    @classmethod
    def has_permission(
        cls,
        user
    ):

        return (
            PermisosSirtee
            .puede_ver_mapa(user)
        )



# ======================================================
# INDICADORES
# ======================================================

class PuedeVerIndicadores(BaseSirteePermission):

    message = (
        "No posee permisos "
        "para acceder a Indicadores"
    )


    @classmethod
    def has_permission(
        cls,
        user
    ):

        return (
            PermisosSirtee
            .puede_ver_indicadores(user)
        )



# ======================================================
# RELEVAMIENTOS
# ======================================================

class PuedeVerRelevamientos(BaseSirteePermission):

    message = (
        "No posee permisos "
        "para acceder a Relevamientos"
    )


    @classmethod
    def has_permission(
        cls,
        user
    ):

        return (
            PermisosSirtee
            .puede_ver_relevamientos(user)
        )



# ======================================================
# HALLAZGOS
# ======================================================

class PuedeVerHallazgos(BaseSirteePermission):

    message = (
        "No posee permisos "
        "para acceder a Hallazgos"
    )


    @classmethod
    def has_permission(
        cls,
        user
    ):

        return (
            PermisosSirtee
            .puede_ver_hallazgos(user)
        )



# ======================================================
# INTERVENCIONES
# ======================================================

class PuedeVerIntervenciones(BaseSirteePermission):

    message = (
        "No posee permisos "
        "para acceder a Intervenciones"
    )


    @classmethod
    def has_permission(
        cls,
        user
    ):

        return (
            PermisosSirtee
            .puede_ver_intervenciones(user)
        )



# ======================================================
# VALIDACIÓN GENERAL
# ======================================================

def validar_permiso(
    permiso,
    user
):

    if not permiso.has_permission(user):

        raise PermissionDenied(
            permiso.message
        )

    return True