from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from apps.evaluaciones_educativas.ver_como import (
    SESSION_KEY, puede_ver_como, registrar, usuario_objetivo,
)
from apps.evaluaciones_educativas.views.dashboard import OPERATIVOS
from apps.usuarios.models import NivelAcceso

MAX_RESULTADOS = 50


def _sin_permiso(request):
    messages.error(request, 'No tienes permiso para acceder a esta página.')
    return redirect(reverse('evaluaciones_educativas:dashboard'))


def _roles_de(operativo):
    return sorted({
        rol
        for anio in operativo['anios']
        for mes in anio['meses']
        for link in mes['links']
        for rol in link['roles']
    })


def _next_seguro(request, por_defecto):
    destino = request.POST.get('next') or ''
    if url_has_allowed_host_and_scheme(destino, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return destino
    return por_defecto


@login_required
def selector(request):
    if not puede_ver_como(request.user):
        return _sin_permiso(request)

    operativos = [
        {'id': op['id'], 'titulo': op['titulo'], 'icono': op['icono'], 'color': op['color'], 'roles': _roles_de(op)}
        for op in OPERATIVOS
    ]
    operativo = next((op for op in operativos if op['id'] == request.GET.get('operativo')), None)
    roles = operativo['roles'] if operativo else list(
        NivelAcceso.objects.order_by('tacceso').values_list('tacceso', flat=True)
    )
    rol = request.GET.get('rol', '').strip()
    if rol not in roles:
        rol = ''
    q = request.GET.get('q', '').strip()

    usuarios = None
    if rol or q:
        qs = get_user_model().objects.filter(activo=True, is_superuser=False).exclude(pk=request.user.pk)
        if rol:
            qs = qs.filter(Q(nivelacceso_id=rol) | Q(perfil__rol__nombre=rol))
        if q:
            qs = qs.filter(Q(username__icontains=q) | Q(apellido__icontains=q) | Q(nombres__icontains=q))
        usuarios = list(
            qs.select_related('nivelacceso', 'perfil__rol').order_by('apellido', 'nombres')[:MAX_RESULTADOS + 1]
        )

    contexto = {
        'operativos': operativos,
        'operativo': operativo,
        'roles': roles,
        'rol': rol,
        'q': q,
        'usuarios': usuarios[:MAX_RESULTADOS] if usuarios is not None else None,
        'hay_mas': usuarios is not None and len(usuarios) > MAX_RESULTADOS,
        'max_resultados': MAX_RESULTADOS,
        'activo': request.session.get(SESSION_KEY),
    }
    return render(request, 'ver_como/selector.html', contexto)


@login_required
@require_POST
def iniciar(request):
    if not puede_ver_como(request.user):
        return _sin_permiso(request)

    objetivo = usuario_objetivo(request.POST.get('user_id'))
    if objetivo is None or objetivo.pk == request.user.pk:
        messages.error(request, 'Ese usuario no se puede usar para "Ver como".')
        return redirect(reverse('evaluaciones_educativas:ver_como:selector'))

    request.session[SESSION_KEY] = {
        'user_id': objetivo.pk,
        'editar': False,
        'inicio': timezone.now().isoformat(),
    }
    registrar(request, request.user, 'ver_como_inicio', f'como {objetivo.username} ({objetivo.nivelacceso_id})')
    messages.info(request, f'Estás viendo como {objetivo.apellido}, {objetivo.nombres}. Modo solo lectura.')

    destino = reverse('evaluaciones_educativas:dashboard')
    operativo = request.POST.get('operativo', '')
    if any(op['id'] == operativo for op in OPERATIVOS):
        destino += f'#card-{operativo}'
    return redirect(destino)


@login_required
@require_POST
def cambiar_edicion(request):
    datos = request.session.get(SESSION_KEY)
    if not datos or not puede_ver_como(request.user):
        return _sin_permiso(request)

    objetivo = usuario_objetivo(datos.get('user_id'))
    if objetivo is None:
        request.session.pop(SESSION_KEY, None)
        return redirect(reverse('evaluaciones_educativas:ver_como:selector'))

    datos['editar'] = not datos.get('editar')
    request.session[SESSION_KEY] = datos
    accion = 'ver_como_editar_on' if datos['editar'] else 'ver_como_editar_off'
    registrar(request, request.user, accion, f'como {objetivo.username}')
    if datos['editar']:
        messages.warning(request, f'Edición habilitada: los cambios se guardan como {objetivo.apellido}, {objetivo.nombres}.')
    else:
        messages.info(request, 'Volviste a modo solo lectura.')
    return redirect(_next_seguro(request, reverse('evaluaciones_educativas:dashboard')))


@login_required
@require_POST
def salir(request):
    datos = request.session.pop(SESSION_KEY, None)
    if datos:
        registrar(request, request.user, 'ver_como_fin', f'user_id {datos.get("user_id")}')
        messages.info(request, 'Saliste del modo "Ver como".')
    return redirect(reverse('evaluaciones_educativas:ver_como:selector'))
