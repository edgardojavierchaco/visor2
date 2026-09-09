"""Única política de alcance. Nunca se aceptan regiones provenientes del cliente."""
import re
from functools import wraps
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import CharField, F, Q, Value
from django.db.models.functions import Cast, Replace
from apps.consultasge.models_padron import CapaUnicaOfertas


def normalize_cuil(value):
    return re.sub(r"[^0-9]", "", str(value or ""))


def get_user_cuil(user):
    return normalize_cuil(user.get_username()) if authenticated(user) else ""


def authenticated(user):
    return bool(user and user.is_authenticated and user.is_active)


def role(user):
    return str(getattr(user, "nivelacceso", ""))


def is_admin(user):
    return authenticated(user) and (user.is_superuser or role(user) in getattr(settings, "BNH_ADMIN_ROLES", ("Administrador",)))


def is_regional(user):
    return authenticated(user) and role(user) in getattr(settings, "BNH_REGIONAL_ROLES", ("Regional",))


def is_director(user):
    return authenticated(user) and role(user) in getattr(settings, "BNH_DIRECTOR_ROLES", ("Director/a", "Director"))


def scoped_offers(user):
    qs = CapaUnicaOfertas.objects.annotate(cueanexo_str=Cast("cueanexo", CharField()))
    if not authenticated(user):
        return qs.none()
    if is_admin(user):
        return qs
    if is_regional(user):
        from ..models import AccesoRegional
        regiones = AccesoRegional.objects.filter(usuario=user, activo=True).values("region")
        return qs.filter(region_loc__in=regiones)
    if is_director(user):
        cuil = get_user_cuil(user)
        if len(cuil) != 11:
            return qs.none()
        expr = Cast(F("resploc_cuitcuil"), CharField())
        for separator in ("-", ".", " ", "\t", "\n", "\r"):
            expr = Replace(expr, Value(separator), Value(""))
        return qs.annotate(cuil_limpio=expr).filter(cuil_limpio=cuil)
    return qs.none()


def get_user_cueanexos(user):
    return scoped_offers(user).order_by().values_list("cueanexo_str", flat=True).distinct()


def user_has_cueanexo_access(user, cueanexo):
    return scoped_offers(user).filter(cueanexo_str=str(cueanexo)).exists()


def activity_scope(user, include_deleted=False):
    from ..models import RegistroActividades
    qs = RegistroActividades.objects.filter(cueanexo__in=get_user_cueanexos(user))
    return qs if include_deleted else qs.filter(eliminado=False, persona__archivada=False)


def person_scope(user):
    from ..models import Personas
    qs = Personas.objects.filter(archivada=False)
    if is_admin(user):
        return qs
    return qs.filter(actividades__in=activity_scope(user, include_deleted=True)).distinct()


def operator_required(view):
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not authenticated(request.user) or not (is_admin(request.user) or get_user_cueanexos(request.user).exists()):
            raise PermissionDenied("No tiene instituciones habilitadas para BNH Personal.")
        response = view(request, *args, **kwargs)
        response["Cache-Control"] = "private, no-store"
        return response
    return wrapped
