import csv
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, Http404, StreamingHttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET
from .access import get_scope
from . import services as s
from django.conf import settings


def _filter_fields(facetas):
    labels = {'region': 'Región educativa', 'departamento': 'Departamento',
              'localidad': 'Localidad', 'sector': 'Sector de gestión',
              'nivel': 'Nivel', 'ambito': 'Ámbito', 'carrera': 'Carrera', 'titulo': 'Título'}
    return [{'key': k, 'label': v, 'options': facetas[k]} for k, v in labels.items()]


def _scope(request, ministerial):
    # No aceptar 'modo=ministerial' de un usuario anónimo.
    # get_scope debe implementar el control de autorización propio del proyecto.
    if ministerial and not request.user.is_authenticated:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied('Debe iniciar sesión para realizar consultas ministeriales.')
    return get_scope(request.user) if ministerial else None


@require_GET
def public(request):
    return render(
        request,
        'carrerastitulos/public.html',
        {
            'filtros': _filter_fields(s.filters()),
            'carto_api_key': getattr(settings, 'CARTO_BASEMAPS_API_KEY', ''),
        }
    )

@login_required
@require_GET
def observatorio(request):
    scope = get_scope(request.user)
    return render(request, 'carrerastitulos/observatorio.html',
                  {'filtros': _filter_fields(s.filters(scope)),
                   'es_regional': scope.kind == 'regional',
                   'carto_api_key': getattr(settings, 'CARTO_BASEMAPS_API_KEY', '')})


@require_GET
def api_resultados(request):
    scope = _scope(request, request.GET.get('modo') == 'ministerial')
    return JsonResponse(s.results(request.GET, scope))


@require_GET
def api_resumen(request):
    scope = _scope(request, request.GET.get('modo') == 'ministerial')
    return JsonResponse(s.summary(request.GET, scope))


@login_required
@require_GET
def api_analisis(request):
    return JsonResponse(s.group_stats(request.GET, get_scope(request.user)))


@require_GET
def api_mapa(request):
    scope = _scope(request, request.GET.get('modo') == 'ministerial')
    return JsonResponse({'puntos': s.map_points(request.GET, scope)})


@require_GET
def api_institucion(request, cueanexo):
    scope = _scope(request, request.GET.get('modo') == 'ministerial')
    if not cueanexo or len(cueanexo) > 25:
        raise Http404
    rows = s.institution(cueanexo, scope)
    if not rows:
        raise Http404('Establecimiento no encontrado')
    first = rows[0]
    info = {k: v for k, v in first.items() if k not in ('nivel', 'carrera', 'titulo')}
    # Defensa adicional frente a variaciones de datos dentro de una misma ficha.
    ofertas, seen = [], set()
    for row in rows:
        nivel = (row.get('nivel') or '').strip()
        carrera = (row.get('carrera') or '').strip()
        titulo = (row.get('titulo') or '').strip()
        key = (nivel.casefold(), carrera.casefold(), titulo.casefold())
        if key in seen:
            continue
        seen.add(key)
        ofertas.append({'nivel': nivel, 'carrera': carrera, 'titulo': titulo})
    info['ofertas'] = ofertas
    return JsonResponse(info)


class Echo:
    def write(self, value):
        return value


@require_GET
def exportar_csv(request):
    scope = _scope(request, request.GET.get('modo') == 'ministerial')
    cols, sql, args = s.export_rows(request.GET, scope)

    def rows():
        writer = csv.writer(Echo(), delimiter=';')
        yield '\ufeff' + writer.writerow(cols)
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute(sql, args)
            while True:
                batch = cursor.fetchmany(500)
                if not batch:
                    break
                for row in batch:
                    safe = []
                    for value in row:
                        txt = '' if value is None else str(value).replace('\r', ' ').replace('\n', ' ')
                        if txt.lstrip().startswith(('=', '+', '-', '@')):
                            txt = "'" + txt
                        safe.append(txt)
                    yield writer.writerow(safe)

    response = StreamingHttpResponse(rows(), content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="carreras_titulos_snu.csv"'
    response['X-Content-Type-Options'] = 'nosniff'
    return response
