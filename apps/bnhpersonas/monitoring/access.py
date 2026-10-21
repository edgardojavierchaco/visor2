from dataclasses import dataclass
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.exceptions import PermissionDenied

from apps.consultasge.models_padron import CapaUnicaOfertas
from apps.supervisor_registro.models import SupervisorRegionalOferta
from apps.supervisor_registro.services.permission_service import get_responsable

from .roles import role_kind, user_role


CACHE_TTL = 60 * 5
CACHE_VERSION = "v2"


GLOBAL_ROLES = {
    "administrador",
    "admin",
    "ministro",
    "subsecretario",
    "director general",
}


@dataclass(frozen=True)
class MonitoringScope:
    kind: str
    role: str
    cueanexos: tuple[str, ...] = ()
    regiones: tuple[str, ...] = ()

    @property
    def global_access(self):
        return self.kind == "global"

    @property
    def has_access(self):
        if self.global_access:
            return True

        if self.kind == "supervisor":
            return bool(self.cueanexos)

        if self.kind == "regional":
            return bool(self.regiones)

        return False

    @property
    def label(self):
        if self.kind == "global":
            return "Alcance jurisdiccional"

        if self.kind == "supervisor":
            return f"{len(self.cueanexos)} CUEANEXO asignados"

        if self.kind == "regional":
            return (
                ", ".join(self.regiones)
                if self.regiones
                else "Sin regionales asignadas"
            )

        return "Sin alcance habilitado"


def _cue(value):
    value = str(value or "").strip()
    return value.zfill(9) if value.isdigit() else value


def _scope_cache_key(user):
    return f"bnh:{CACHE_VERSION}:monitor-scope:{user.pk}"


def _normalize_role(value):
    """
    Normaliza el nombre del rol para evitar diferencias por:
    - mayúsculas/minúsculas
    - espacios al principio/final
    """
    return str(value or "").strip().lower()


def supervisor_cueanexos(user):
    qs = (
        SupervisorRegionalOferta.objects.filter(
            supervisor_regional__supervisor__usuario=user,
            supervisor_regional__supervisor__activo=True,
            supervisor_regional__activo=True,
            activo=True,
        )
        .values_list("cueanexo", flat=True)
        .distinct()
    )

    return tuple(
        sorted(
            {
                _cue(value)
                for value in qs
                if value
            }
        )
    )


def regional_names(user):
    responsable = get_responsable(user)

    if not responsable or not responsable.activo:
        return ()

    values = (
        responsable.regiones
        .values_list("nombre", flat=True)
        .distinct()
    )

    return tuple(
        sorted(
            {
                str(value).strip()
                for value in values
                if value
            }
        )
    )


def resolve_scope(user):
    """
    Resuelve el alcance del usuario para Seguimiento BNH.

    Alcances:
        global:
            - superusuario
            - Administrador
            - Admin
            - Ministro
            - Subsecretario
            - Director General

        regional:
            - Referentes de Estadística
            - roles regionales definidos por role_kind()

        supervisor:
            - Supervisores con CUEANEXO asignados

        none:
            - usuario sin alcance habilitado
    """

    if not user or not getattr(user, "is_authenticated", False):
        return MonitoringScope(
            kind="none",
            role="",
        )

    # ------------------------------------------------------------------
    # REFERENTES DE ESTADÍSTICA
    # ------------------------------------------------------------------
    # Autorización independiente del nivelacceso.
    # No se almacena en caché para respetar inmediatamente
    # cambios de estado o de regionales asignadas.
    # ------------------------------------------------------------------

    perfil = getattr(user, "perfil", None)
    categoria = getattr(
        getattr(perfil, "rol", None),
        "categoria_acceso",
        None,
    )

    if categoria == "refestadistica":
        from apps.usuarios.services.acceso_referentes import (
            obtener_regiones_referente,
        )

        regiones = (
            tuple(obtener_regiones_referente(user))
            if getattr(user, "is_active", False)
            else ()
        )

        return MonitoringScope(
            kind="regional" if regiones else "none",
            role="refestadistica",
            regiones=regiones,
        )

    # ------------------------------------------------------------------
    # CACHE
    # ------------------------------------------------------------------

    key = _scope_cache_key(user)
    cached = cache.get(key)

    if cached is not None:
        return MonitoringScope(**cached)

    # ------------------------------------------------------------------
    # ROL
    # ------------------------------------------------------------------

    role = user_role(user)
    normalized_role = _normalize_role(role)

    # ------------------------------------------------------------------
    # ACCESO GLOBAL
    # ------------------------------------------------------------------
    #
    # Tienen el mismo alcance jurisdiccional que el Administrador:
    #
    # - Administrador
    # - Admin
    # - Ministro
    # - Subsecretario
    # - Director General
    #
    # Los superusuarios también tienen alcance global.
    # ------------------------------------------------------------------

    if (
        getattr(user, "is_superuser", False)
        or normalized_role in GLOBAL_ROLES
    ):
        scope = MonitoringScope(
            kind="global",
            role=role,
        )

    else:
        # Para el resto de los usuarios se mantiene
        # la lógica centralizada existente en roles.py.
        kind = role_kind(user)

        if kind == "global":
            scope = MonitoringScope(
                kind="global",
                role=role,
            )

        elif kind == "supervisor":
            scope = MonitoringScope(
                kind="supervisor",
                role=role,
                cueanexos=supervisor_cueanexos(user),
            )

        elif kind == "regional":
            scope = MonitoringScope(
                kind="regional",
                role=role,
                regiones=regional_names(user),
            )

        else:
            scope = MonitoringScope(
                kind="none",
                role=role,
            )

    # ------------------------------------------------------------------
    # GUARDAR EN CACHE
    # ------------------------------------------------------------------

    cache.set(
        key,
        {
            "kind": scope.kind,
            "role": scope.role,
            "cueanexos": scope.cueanexos,
            "regiones": scope.regiones,
        },
        CACHE_TTL,
    )

    return scope


def invalidate_scope_cache(user):
    if user and getattr(user, "pk", None):
        cache.delete(_scope_cache_key(user))


def scoped_offers(user):
    """
    Devuelve las ofertas visibles para el usuario según su alcance.
    """

    qs = CapaUnicaOfertas.objects.all()
    scope = resolve_scope(user)

    if scope.kind == "global":
        return qs

    if scope.kind == "supervisor":
        if scope.cueanexos:
            return qs.filter(
                cueanexo__in=scope.cueanexos
            )

        return qs.none()

    if scope.kind == "regional":
        if scope.regiones:
            return qs.filter(
                region_loc__in=scope.regiones
            )

        return qs.none()

    return qs.none()


def allowed_cueanexos(user):
    """
    Devuelve todos los CUEANEXO permitidos para el usuario.
    """

    scope = resolve_scope(user)

    if scope.kind == "supervisor":
        return scope.cueanexos

    return tuple(
        sorted(
            {
                _cue(value)
                for value in (
                    scoped_offers(user)
                    .values_list("cueanexo", flat=True)
                    .distinct()
                )
                if value is not None
            }
        )
    )


def can_monitor(user):
    """
    Indica si el usuario puede ingresar al Seguimiento BNH.
    """

    return bool(
        user
        and getattr(user, "is_authenticated", False)
        and getattr(user, "is_active", True)
        and resolve_scope(user).has_access
    )


def assert_cue_access(user, cueanexo):
    """
    Verifica que el usuario tenga autorización para consultar
    un CUEANEXO determinado.

    Devuelve el CUEANEXO normalizado si tiene acceso.
    Lanza PermissionDenied en caso contrario.
    """

    cueanexo = _cue(cueanexo)
    scope = resolve_scope(user)

    # Acceso jurisdiccional completo.
    if scope.kind == "global":
        return cueanexo

    # Supervisor: sólo CUEANEXO explícitamente asignados.
    if scope.kind == "supervisor":
        if cueanexo in scope.cueanexos:
            return cueanexo

        raise PermissionDenied(
            "No posee autorización para consultar este CUEANEXO."
        )

    # Referentes / responsables regionales:
    # solamente CUEANEXO pertenecientes a sus regionales.
    if scope.kind == "regional":
        if (
            scoped_offers(user)
            .filter(cueanexo=cueanexo)
            .exists()
        ):
            return cueanexo

    raise PermissionDenied(
        "No posee autorización para consultar este CUEANEXO."
    )


def monitoring_required(view):
    """
    Decorador de acceso al módulo de Seguimiento BNH.
    """

    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):

        if not can_monitor(request.user):
            raise PermissionDenied(
                "No posee un nivel de acceso habilitado "
                "para Seguimiento BNH."
            )

        response = view(
            request,
            *args,
            **kwargs,
        )

        response["Cache-Control"] = (
            "private, no-store, max-age=0"
        )
        response["Pragma"] = "no-cache"
        response["X-Robots-Tag"] = "noindex, nofollow"

        return response

    return wrapped