"""Acceso EIB: denegación por defecto, alcance centralizado, sin confiar en POST."""
from django.conf import settings
from django.core.exceptions import PermissionDenied

PROVINCIAL = {"administrador", "ministro", "subsecretario", "director general", "director_general", "admin"}
REGIONAL = {"director regional", "regional", "director_regional"}
SUPERVISION = {"supervisor"}

def role(user):
    if user.is_superuser:
        return "administrador"
    names = []
    for attr in ("rol", "role", "nivelacceso"):
        v = getattr(user, attr, None)
        if v is not None:
            names.append(str(getattr(v, "nombre", v)).strip().lower())
    try:
        names += [str(g).strip().lower() for g in user.groups.all()]
    except (AttributeError, TypeError):
        pass
    for group in (PROVINCIAL, REGIONAL, SUPERVISION):
        for n in names:
            if n in group:
                return n
    return "institucional"

def scope(request):
    """Devuelve None (provincial), set de CUE autorizados, o conjunto vacío."""
    if not request.user.is_authenticated or not getattr(request.user, 'is_active', False):
        raise PermissionDenied('Acceso no habilitado')
    resolver = getattr(settings, 'INTERCULTURAL_SCOPE_RESOLVER', None)
    if resolver:
        from django.utils.module_loading import import_string
        result = import_string(resolver)(request.user, request)
        if result is None:
            return None
        return {str(x).strip() for x in result if str(x).strip()}
    r = role(request.user)
    if r in PROVINCIAL:
        return None
    if r in REGIONAL or r in SUPERVISION:
        # Debe configurarse el resolvedor central de competencias. No ampliar privilegios.
        return set()
    cues = getattr(request, 'cueanexos_validos', None)
    if cues is None:
        try:
            from apps.core.security.padron_access import user_cueanexos
            cues = user_cueanexos(request.user)
        except ImportError:
            cues = []
    return {str(x).strip() for x in cues if x is not None and str(x).strip()}

def require_editor(request):
    r=role(request.user)
    if r in REGIONAL or r in SUPERVISION or r in {'ministro','subsecretario','director general','director_general'}:
        raise PermissionDenied('El perfil tiene permiso de consulta, no de edición.')
    if r == 'institucional' and scope(request) == set():
        raise PermissionDenied('Sin establecimientos autorizados.')
