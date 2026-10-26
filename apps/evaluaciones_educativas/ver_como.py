"""Modo "Ver como": el rol Evaluación navega Evaluaciones Educativas con la
identidad de otro usuario. Arranca en solo lectura; la edición se habilita
aparte y cada escritura queda registrada a nombre del usuario real."""
from functools import wraps

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.urls import URLPattern, URLResolver, reverse

from apps.core.security.padron_access import user_cueanexos
from apps.usuarios.models import UsuarioAccesoLog

SESSION_KEY = 'ver_como'
METODOS_SEGUROS = ('GET', 'HEAD', 'OPTIONS', 'TRACE')
# Vistas GET que igual modifican datos.
GET_QUE_ESCRIBEN = ('/completar_carga/',)


def puede_ver_como(usuario):
    from apps.evaluaciones_educativas.views.monitoreo_personas_2026 import _es_evaluacion
    return usuario.is_authenticated and _es_evaluacion(usuario)


def usuario_objetivo(user_id):
    return (
        get_user_model().objects
        .filter(pk=user_id, activo=True, is_superuser=False)
        .select_related('nivelacceso', 'perfil__rol')
        .first()
    )


def registrar(request, usuario_real, accion, detalle):
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    ip = x_forwarded.split(',')[0].strip() if x_forwarded else request.META.get('REMOTE_ADDR') or None
    UsuarioAccesoLog.objects.create(
        username=usuario_real.username,
        ip=ip,
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:255],
        accion=accion,
        path=detalle,
    )


def _es_escritura(request):
    return request.method not in METODOS_SEGUROS or any(f in request.path for f in GET_QUE_ESCRIBEN)


def _es_ajax(request):
    return (
        request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        or 'application/json' in request.headers.get('Accept', '')
    )


def _bloquear(request):
    texto = 'Estás en modo "Ver como" de solo lectura. Habilitá la edición para hacer cambios.'
    if _es_ajax(request):
        return JsonResponse({'ok': False, 'nivel': 'error', 'mensaje': texto}, status=403)
    messages.warning(request, texto)
    return redirect(request.META.get('HTTP_REFERER') or reverse('evaluaciones_educativas:dashboard'))


def _inyectar_barra(request, response, real, objetivo, editar):
    if getattr(response, 'streaming', False) or response.status_code != 200:
        return response
    if not response.get('Content-Type', '').startswith('text/html'):
        return response
    cierre = response.content.rfind(b'</body>')
    if cierre == -1:
        return response

    barra = render_to_string('ver_como/barra.html', {
        'real': real,
        'objetivo': objetivo,
        'editar': editar,
        'csrf_token': get_token(request),
        'next': request.get_full_path(),
    }).encode(response.charset or 'utf-8')
    response.content = response.content[:cierre] + barra + response.content[cierre:]
    if response.has_header('Content-Length'):
        response['Content-Length'] = str(len(response.content))
    return response


def ver_como_view(view):
    """Hace que la vista atienda la request como el usuario simulado."""
    if getattr(view, '_ver_como', False):
        return view

    @wraps(view)
    def envuelta(request, *args, **kwargs):
        datos = request.session.get(SESSION_KEY) if hasattr(request, 'session') else None
        if not datos or not request.user.is_authenticated:
            return view(request, *args, **kwargs)

        real = request.user
        if not puede_ver_como(real):
            request.session.pop(SESSION_KEY, None)
            return view(request, *args, **kwargs)

        objetivo = usuario_objetivo(datos.get('user_id'))
        if objetivo is None:
            request.session.pop(SESSION_KEY, None)
            messages.warning(request, 'El usuario que estabas viendo ya no está disponible. Saliste del modo "Ver como".')
            return view(request, *args, **kwargs)

        editar = bool(datos.get('editar'))
        if _es_escritura(request):
            if not editar:
                return _bloquear(request)
            registrar(request, real, 'ver_como_edicion', f'{request.method} {request.path} [como {objetivo.username}]')

        request.usuario_real = real
        request.user = objetivo
        cues = {str(c).strip() for c in user_cueanexos(objetivo) if c is not None and str(c).strip()}
        request.cueanexos_validos = cues
        request.cueanexos_list = sorted(cues)
        try:
            response = view(request, *args, **kwargs)
        finally:
            request.user = real

        return _inyectar_barra(request, response, real, objetivo, editar)

    envuelta._ver_como = True
    return envuelta


def aplicar_ver_como(patrones):
    """Envuelve todas las vistas de los patrones, entrando en los include()."""
    for patron in patrones:
        if isinstance(patron, URLResolver):
            aplicar_ver_como(patron.url_patterns)
        elif isinstance(patron, URLPattern):
            patron.callback = ver_como_view(patron.callback)
    return patrones
