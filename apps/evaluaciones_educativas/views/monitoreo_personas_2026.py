import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import DatabaseError
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone

from apps.evaluaciones_educativas.services import monitoreo_personas_2026 as monitoreo
from apps.usuarios.services.user_context import get_user_rol

logger = logging.getLogger(__name__)

TABS = ('fluidez', 'aprender')
ERROR_SGE = (
    'No se pudieron consultar las secciones en SGE. Los aplicadores de Fluidez '
    'se muestran sin el total esperado; intentá de nuevo en unos minutos.'
)


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------
def _es_evaluacion(usuario):
    return (
        usuario.is_superuser
        or getattr(usuario, 'nivelacceso_id', None) == 'Evaluacion'
        or get_user_rol(usuario) == 'Evaluacion'
    )


def _sin_permiso(request):
    messages.error(request, 'No tienes permiso para acceder a esta página.')
    return redirect(reverse('evaluaciones_educativas:dashboard'))


def _tab(request):
    tab = request.GET.get('tab')
    return tab if tab in TABS else TABS[0]


def _secciones_sge(request):
    """Secciones de SGE por escuela, o None si sge_nacion no responde."""
    refrescar = request.GET.get('refrescar') == '1'
    try:
        return monitoreo.secciones_sge_por_escuela(
            monitoreo.escuelas_fluidez(refrescar=refrescar).keys(),
            refrescar=refrescar,
        )
    except DatabaseError:
        logger.exception('Monitoreo de personas: error consultando secciones en sge_nacion')
        messages.warning(request, ERROR_SGE)
        return None


# ---------------------------------------------------------------------------
# VISTAS
# ---------------------------------------------------------------------------
@login_required
def monitoreo_regionales(request):
    """Avance de carga de personas de cada regional, en los dos operativos."""
    if not _es_evaluacion(request.user):
        return _sin_permiso(request)

    secciones_sge = _secciones_sge(request)
    fluidez = monitoreo.resumen_fluidez(secciones_sge)
    aprender = monitoreo.resumen_aprender()

    contexto = {
        'tab': _tab(request),
        'fluidez': fluidez,
        'aprender': aprender,
        'sge_ok': secciones_sge is not None,
        'actualizado': timezone.localtime(),
    }
    return render(request, 'monitoreo_personas_2026/monitoreo.html', contexto)


@login_required
def detalle_regional(request, region):
    """Escuelas de una regional con lo que tienen cargado y lo que les falta."""
    if not _es_evaluacion(request.user):
        return _sin_permiso(request)

    tab = _tab(request)
    if tab == 'fluidez':
        secciones_sge = _secciones_sge(request)
        resumen = monitoreo.resumen_fluidez(secciones_sge)
        escuelas = monitoreo.detalle_fluidez(region, secciones_sge)
    else:
        secciones_sge = None
        resumen = monitoreo.resumen_aprender()
        escuelas = monitoreo.detalle_aprender(region)

    fila = next((f for f in resumen['filas'] if f['region'] == region), None)
    if fila is None:
        messages.error(request, f'No se encontró la regional {region}.')
        return redirect(f"{reverse('evaluaciones_educativas:monitoreo_personas_2026:monitoreo')}?tab={tab}")

    contexto = {
        'tab': tab,
        'region': region,
        'regiones': [f['region'] for f in resumen['filas']],
        'fila': fila,
        'escuelas': escuelas,
        'estados': {
            'pendiente': sum(1 for e in escuelas if e['pendiente']),
            'completa': sum(1 for e in escuelas if not e['pendiente']),
        },
        'sge_ok': tab != 'fluidez' or secciones_sge is not None,
        'actualizado': timezone.localtime(),
    }
    return render(request, 'monitoreo_personas_2026/detalle_regional.html', contexto)
