from django.core.exceptions import PermissionDenied
from apps.supervisa2.models.supervisor import (
    Supervisor2,
    SupervisorRegion,
    RegionalUsuario
)

# =========================================================
# 🔥 REGIONES DEL USUARIO (MULTI-REGIÓN)
# =========================================================
def get_region_usuario(user):

    return list(
        RegionalUsuario.objects
        .filter(usuario=user)
        .values_list("region_loc", flat=True)
    )


# =========================================================
# 🔥 SUPERVISORES POR REGIÓN (MULTI-REGIÓN)
# =========================================================
def get_supervisores_regional(user):

    regiones = get_region_usuario(user)

    if not regiones:
        return Supervisor2.objects.none()

    return (
        Supervisor2.objects
        .select_related("situacion_revista", "usuario")
        .filter(
            supervisor_regiones__region__nombre__in=regiones
        )
        .distinct()
    )


# =========================================================
# 🔥 PENDIENTES REGIONAL (MULTI-REGIÓN)
# =========================================================
def get_pendientes_regional(user):

    regiones = get_region_usuario(user)

    if not regiones:
        return Supervisor2.objects.none()

    return (
        Supervisor2.objects
        .filter(
            estado_validacion="EN_REVISION",
            supervisor_regiones__region__nombre__in=regiones
        )
        .distinct()
    )


# =========================================================
# 🔥 VALIDACIÓN REGIONAL SEGURA (MULTI-REGIÓN)
# =========================================================
def validar_supervisor_regional(supervisor, user, aprobar=True):

    regiones = get_region_usuario(user)

    if not regiones:
        raise PermissionDenied("Usuario sin región asignada")

    autorizado = SupervisorRegion.objects.filter(
        supervisor=supervisor,
        region_loc__in=regiones
    ).exists()

    if not autorizado:
        raise PermissionDenied("No pertenece a ninguna de sus regiones")

    supervisor.estado_validacion = (
        "APROBADO" if aprobar else "RECHAZADO"
    )

    supervisor.save(update_fields=["estado_validacion"])