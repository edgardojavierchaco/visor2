"""Única política de alcance. Nunca se aceptan regiones provenientes del cliente."""

import re
from functools import wraps

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import CharField
from django.db.models.functions import Cast

from apps.consultasge.models_padron import CapaUnicaOfertas
from apps.core.security.padron_access import (
    get_cueanexos_by_cuil,
    user_has_cueanexo,
)


def normalize_cuil(value):
    return re.sub(r"[^0-9]", "", str(value or ""))


def authenticated(user):
    return bool(
        user
        and user.is_authenticated
        and user.is_active
    )


def get_user_cuil(user):
    return (
        normalize_cuil(user.get_username())
        if authenticated(user)
        else ""
    )


def role(user):
    return str(
        getattr(user, "nivelacceso", "")
    )


def is_admin(user):
    return (
        authenticated(user)
        and (
            user.is_superuser
            or role(user)
            in getattr(
                settings,
                "BNH_ADMIN_ROLES",
                ("Administrador",),
            )
        )
    )


def is_regional(user):
    return (
        authenticated(user)
        and role(user)
        in getattr(
            settings,
            "BNH_REGIONAL_ROLES",
            ("Regional",),
        )
    )


def is_director(user):
    return (
        authenticated(user)
        and role(user)
        in getattr(
            settings,
            "BNH_DIRECTOR_ROLES",
            ("Director/a", "Director"),
        )
    )


def scoped_offers(user):
    """
    QuerySet institucional.

    Para Director ya NO busca por CUIL dentro de
    v_capa_unica_ofertas_ant.

    Primero obtiene los CUEANEXOS mediante la consulta rápida
    contra Padron y después limita el queryset a esos CUE.
    """

    qs = CapaUnicaOfertas.objects.annotate(
        cueanexo_str=Cast(
            "cueanexo",
            CharField(),
        )
    )

    if not authenticated(user):
        return qs.none()

    if is_admin(user):
        return qs

    if is_regional(user):
        from ..models import AccesoRegional

        regiones = (
            AccesoRegional.objects
            .filter(
                usuario=user,
                activo=True,
            )
            .values("region")
        )

        return qs.filter(
            region_loc__in=regiones
        )

    if is_director(user):
        cueanexos = get_user_cueanexos(user)

        if not cueanexos:
            return qs.none()

        return qs.filter(
            cueanexo_str__in=cueanexos
        )

    return qs.none()


def get_user_cueanexos(user):
    """
    Retorna tuple de CUEANEXOS autorizados.

    Para Director consulta directamente Padron y Redis.
    No toca v_capa_unica_ofertas_ant.
    """

    if not authenticated(user):
        return tuple()

    if is_director(user):
        cuil = get_user_cuil(user)

        if len(cuil) != 11:
            return tuple()

        return get_cueanexos_by_cuil(cuil)

    # Para admin/regional mantenemos comportamiento institucional.
    return tuple(
        str(c).strip()
        for c in (
            scoped_offers(user)
            .order_by()
            .values_list(
                "cueanexo_str",
                flat=True,
            )
            .distinct()
        )
        if c
    )


def user_has_cueanexo_access(user, cueanexo):
    if not authenticated(user):
        return False

    if is_director(user):
        return user_has_cueanexo(
            user,
            cueanexo,
        )

    cueanexo = str(cueanexo or "").strip()

    return (
        scoped_offers(user)
        .filter(
            cueanexo_str=cueanexo
        )
        .exists()
    )


def activity_scope(
    user,
    include_deleted=False,
):
    from ..models import RegistroActividades

    cueanexos = get_user_cueanexos(user)

    if not cueanexos and not is_admin(user):
        return RegistroActividades.objects.none()

    qs = RegistroActividades.objects.filter(
        cueanexo__in=cueanexos
    )

    if include_deleted:
        return qs

    return qs.filter(
        eliminado=False,
        persona__archivada=False,
    )


def person_scope(user):
    from ..models import Personas

    qs = Personas.objects.filter(
        archivada=False
    )

    if is_admin(user):
        return qs

    return (
        qs.filter(
            actividades__in=activity_scope(
                user,
                include_deleted=True,
            )
        )
        .distinct()
    )


def operator_required(view):
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):

        if not authenticated(request.user):
            raise PermissionDenied(
                "No tiene instituciones habilitadas para BNH Personal."
            )

        autorizado = (
            is_admin(request.user)
            or bool(
                get_user_cueanexos(
                    request.user
                )
            )
        )

        if not autorizado:
            raise PermissionDenied(
                "No tiene instituciones habilitadas para BNH Personal."
            )

        response = view(
            request,
            *args,
            **kwargs,
        )

        response["Cache-Control"] = (
            "private, no-store"
        )

        return response

    return wrapped