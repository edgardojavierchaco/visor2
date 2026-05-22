from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from .models_integracion import (
    CefUsuarioPerfil,
    PADRON_DB_ALIAS,
    get_cefs_por_cuil_responsable,
    get_cueanexos_por_cuil_responsable,
    get_todos_los_cef,
    normalizar_cueanexo,
)


CEF_SESSION_KEY = "cef_cueanexo_activo"
ROL_ADMINISTRADOR = "Administrador"
ROL_DIRECTOR_SERVICIOS_COMPLEMENTARIOS = "Director de Servicios Complementarios"


def _usuario_autenticado(user):
    return bool(user and getattr(user, "is_authenticated", False))


def _cefs_none():
    return get_todos_los_cef().none()


def obtener_rol_usuario_cef(user):
    if not _usuario_autenticado(user):
        return None

    username = (getattr(user, "username", "") or "").strip()
    if not username:
        return None

    try:
        perfil = (
            CefUsuarioPerfil.objects.using(PADRON_DB_ALIAS)
            .select_related("rol")
            .get(usuario__username=username)
        )
    except CefUsuarioPerfil.DoesNotExist:
        return None

    rol_nombre = getattr(perfil.rol, "nombre", "") or ""
    return rol_nombre.strip() or None


def usuario_es_administrador(user):
    return obtener_rol_usuario_cef(user) == ROL_ADMINISTRADOR


def usuario_es_director_servicios_complementarios(user):
    return (
        obtener_rol_usuario_cef(user)
        == ROL_DIRECTOR_SERVICIOS_COMPLEMENTARIOS
    )


def usuario_es_director_comun_cef(user):
    if not _usuario_autenticado(user):
        return False
    return get_cefs_por_cuil_responsable(user).exists()


def usuario_puede_entrar_cef_director(user):
    return usuario_es_director_comun_cef(user)


def usuario_puede_entrar_cef_visualizacion(user):
    if not _usuario_autenticado(user):
        return False
    return (
        usuario_es_director_servicios_complementarios(user)
        or usuario_es_administrador(user)
    )


def usuario_puede_entrar_cef_configuracion(user):
    if not _usuario_autenticado(user):
        return False
    return usuario_es_administrador(user)


def usuario_puede_acceder_cef(user):
    return (
        usuario_puede_entrar_cef_director(user)
        or usuario_puede_entrar_cef_visualizacion(user)
        or usuario_puede_entrar_cef_configuracion(user)
    )


def get_cefs_director_usuario(user):
    if not _usuario_autenticado(user):
        return _cefs_none()
    return get_cefs_por_cuil_responsable(user)


def get_cefs_visualizacion_usuario(user):
    if not _usuario_autenticado(user):
        return _cefs_none()

    if usuario_es_director_servicios_complementarios(user):
        return get_todos_los_cef()

    if usuario_es_administrador(user):
        return get_todos_los_cef()

    return _cefs_none()


def get_cefs_cargables_usuario(user):
    if not _usuario_autenticado(user):
        return _cefs_none()

    if usuario_es_director_servicios_complementarios(user):
        return _cefs_none()

    if usuario_es_administrador(user):
        return _cefs_none()

    if usuario_es_director_comun_cef(user):
        return get_cefs_director_usuario(user)

    return _cefs_none()


def get_cueanexos_director_usuario(user):
    if not _usuario_autenticado(user):
        return []

    cueanexos = []
    for cueanexo in get_cueanexos_por_cuil_responsable(user):
        cueanexo_normalizado = normalizar_cueanexo(cueanexo)
        if cueanexo_normalizado and cueanexo_normalizado not in cueanexos:
            cueanexos.append(cueanexo_normalizado)
    return cueanexos


def _cueanexos_desde_queryset(qs):
    cueanexos = []
    for cueanexo in qs.values_list("cueanexo", flat=True).distinct():
        cueanexo_normalizado = normalizar_cueanexo(cueanexo)
        if cueanexo_normalizado and cueanexo_normalizado not in cueanexos:
            cueanexos.append(cueanexo_normalizado)
    return cueanexos


def get_cueanexos_visualizacion_usuario(user):
    if not _usuario_autenticado(user):
        return []
    return _cueanexos_desde_queryset(get_cefs_visualizacion_usuario(user))


def get_cueanexos_cargables_usuario(user):
    if not _usuario_autenticado(user):
        return []
    return _cueanexos_desde_queryset(get_cefs_cargables_usuario(user))


def get_cef_cueanexo_activo(request):
    return request.session.get(CEF_SESSION_KEY)


def set_cef_cueanexo_activo(request, cueanexo):
    cueanexo_normalizado = normalizar_cueanexo(cueanexo)
    if not cueanexo_normalizado:
        request.session.pop(CEF_SESSION_KEY, None)
        request.session.modified = True
        return None

    request.session[CEF_SESSION_KEY] = cueanexo_normalizado
    request.session.modified = True
    return cueanexo_normalizado


def resolver_cef_cueanexo_activo(request):
    cueanexos_cargables = get_cueanexos_cargables_usuario(request.user)
    cueanexo_actual = normalizar_cueanexo(get_cef_cueanexo_activo(request))

    if cueanexo_actual and cueanexo_actual in cueanexos_cargables:
        return cueanexo_actual

    if cueanexos_cargables:
        return set_cef_cueanexo_activo(request, cueanexos_cargables[0])

    request.session.pop(CEF_SESSION_KEY, None)
    request.session.modified = True
    return None


def resolver_cueanexos_visualizacion_desde_request(request):
    cueanexos_visibles = set(get_cueanexos_visualizacion_usuario(request.user))
    if not cueanexos_visibles:
        return []

    seleccion_raw = []
    seleccion_raw.extend(request.GET.getlist("cefs"))

    cueanexo_unico = request.GET.get("cueanexo")
    if cueanexo_unico:
        seleccion_raw.append(cueanexo_unico)

    seleccion_normalizada = []
    for cueanexo in seleccion_raw:
        cueanexo_normalizado = normalizar_cueanexo(cueanexo)
        if (
            cueanexo_normalizado
            and cueanexo_normalizado in cueanexos_visibles
            and cueanexo_normalizado not in seleccion_normalizada
        ):
            seleccion_normalizada.append(cueanexo_normalizado)

    if seleccion_normalizada:
        return seleccion_normalizada

    return sorted(cueanexos_visibles)


def usuario_puede_usar_cef_director(user, cueanexo):
    if not usuario_es_director_comun_cef(user):
        return False

    cueanexo_normalizado = normalizar_cueanexo(cueanexo)
    if not cueanexo_normalizado:
        return False

    return cueanexo_normalizado in get_cueanexos_cargables_usuario(user)


def usuario_puede_usar_cueanexo_cef(user, cueanexo):
    return usuario_puede_usar_cef_director(user, cueanexo)


def usuario_puede_ver_cef_visualizacion(user, cueanexo):
    if not usuario_puede_entrar_cef_visualizacion(user):
        return False

    cueanexo_normalizado = normalizar_cueanexo(cueanexo)
    if not cueanexo_normalizado:
        return False

    return cueanexo_normalizado in get_cueanexos_visualizacion_usuario(user)


def validar_cueanexo_director_o_403(user, cueanexo):
    if not usuario_puede_usar_cef_director(user, cueanexo):
        raise PermissionDenied("No tenes permisos para cargar o usar ese CEF.")
    return normalizar_cueanexo(cueanexo)


def validar_cueanexo_visualizacion_o_403(user, cueanexo):
    if not usuario_puede_ver_cef_visualizacion(user, cueanexo):
        raise PermissionDenied("No tenes permisos para visualizar ese CEF.")
    return normalizar_cueanexo(cueanexo)


def _aplicar_permiso_cef(view_func, permiso_func, mensaje):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not permiso_func(request.user):
            raise PermissionDenied(mensaje)
        return view_func(request, *args, **kwargs)

    return login_required(_wrapped)


def cef_director_required(view_func):
    return _aplicar_permiso_cef(
        view_func,
        usuario_puede_entrar_cef_director,
        "No tenes permisos para acceder al flujo de carga CEF.",
    )


def cef_visualizacion_required(view_func):
    return _aplicar_permiso_cef(
        view_func,
        usuario_puede_entrar_cef_visualizacion,
        "No tenes permisos para acceder a Visualizacion CEF.",
    )


def cef_configuracion_required(view_func):
    return _aplicar_permiso_cef(
        view_func,
        usuario_puede_entrar_cef_configuracion,
        "No tenes permisos para acceder a Configuracion CEF.",
    )


def cef_router_cueanexo_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        cueanexo = (
            kwargs.get("cueanexo")
            or request.POST.get("cueanexo")
            or request.GET.get("cueanexo")
        )
        if not usuario_puede_usar_cef_director(request.user, cueanexo):
            raise PermissionDenied("No tenes permisos para seleccionar ese CEF.")
        return view_func(request, *args, **kwargs)

    return login_required(_wrapped)


def cef_login_required(view_func):
    return _aplicar_permiso_cef(
        view_func,
        usuario_puede_acceder_cef,
        "No tenes permisos para acceder a CEF.",
    )
