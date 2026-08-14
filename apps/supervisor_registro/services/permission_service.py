#services/permission_service.py
from ..models import ResponsableRegional
from apps.supervisa2.models import Region


ROLES_ADMIN = {
    "Administrador",
    "Funcionario",
}


class PermissionDenied(Exception):
    """Excepción de dominio para permisos del módulo."""


def es_admin(user):
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    return getattr(user, "nivelacceso", None) in ROLES_ADMIN


def get_responsable(user):
    if not user or not getattr(user, "is_authenticated", False):
        return None

    return (
        ResponsableRegional.objects
        .filter(usuario=user, activo=True)
        .prefetch_related("regiones")
        .first()
    )


def assert_responsable(user):
    obj = get_responsable(user)
    if not obj:
        raise PermissionDenied("No responsable regional asignado")
    return obj


def get_regiones_usuario(user):
    """
    None  -> acceso global (Administrador/Funcionario/superuser)
    [ids] -> regiones permitidas para un Responsable Regional
    []    -> usuario sin alcance
    """
    if es_admin(user):
        return None

    responsable = get_responsable(user)
    if not responsable:
        return []

    return list(
        responsable.regiones.values_list("id", flat=True)
    )


def get_regiones_queryset(user):
    """QuerySet de Region visible para el usuario."""
    regiones = get_regiones_usuario(user)
    if regiones is None:
        return Region.objects.all().order_by("nombre")
    if not regiones:
        return Region.objects.none()
    return Region.objects.filter(id__in=regiones).order_by("nombre")


def puede_ver_supervisores(user):
    return es_admin(user) or get_responsable(user) is not None


def puede_operar_region(user, region_id, accion="modificar"):
    """
    Comprueba acceso a una región y, para responsables regionales,
    respeta las banderas de operación.
    """
    if es_admin(user):
        return True

    responsable = get_responsable(user)
    if not responsable:
        return False

    if not responsable.regiones.filter(pk=region_id).exists():
        return False

    permisos = {
        "crear": responsable.puede_crear_supervisores,
        "modificar": responsable.puede_modificar_supervisores,
        "eliminar": responsable.puede_eliminar_supervisores,
        "ver": True,
    }
    return permisos.get(accion, False)


def puede_operar_supervisor(user, supervisor, accion="modificar"):
    """Comprueba que el usuario puede operar sobre el supervisor."""
    if es_admin(user):
        return True

    regiones = get_regiones_usuario(user)
    if not regiones:
        return False

    return supervisor.asignaciones_regionales.filter(
        activo=True,
        region_id__in=regiones,
    ).exists() and _permiso_accion(user, accion)


def _permiso_accion(user, accion):
    responsable = get_responsable(user)
    if not responsable:
        return False
    return {
        "crear": responsable.puede_crear_supervisores,
        "modificar": responsable.puede_modificar_supervisores,
        "eliminar": responsable.puede_eliminar_supervisores,
        "ver": True,
    }.get(accion, False)


def puede_crear_supervisor(user):
    return es_admin(user) or _permiso_accion(user, "crear")


def puede_modificar_supervisor(user):
    return es_admin(user) or _permiso_accion(user, "modificar")


def puede_eliminar_supervisor(user):
    return es_admin(user) or _permiso_accion(user, "eliminar")
