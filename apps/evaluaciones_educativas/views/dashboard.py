from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.urls import reverse


@login_required
def dashboard(request):
    usuario = request.user
    rol = usuario.nivelacceso_id

    es_director = (rol == 'Director/a')
    es_regional = (rol == 'Regional')
    es_funcionario = rol in ['Funcionario', 'Ministro', 'Subse']

    # ──────────────────────────────────────────────────────────────
    # OPERATIVOS: Lista de módulos.
    # Cada operativo tiene una lista de "links".
    # Cada link define qué URL corresponde a cada rol.
    #   - url: URL fija (todos los roles que lo ven van al mismo lugar)
    #   - url_director / url_regional / url_funcionario: URL diferente por rol
    #   - roles: lista de nivelacceso_id que pueden VER este link
    #
    # ► PARA AGREGAR UN NUEVO OPERATIVO: copiar un bloque y ajustar datos.
    # ► PARA AGREGAR UN LINK A UN OPERATIVO: agregar un dict a su lista 'links'.
    # ──────────────────────────────────────────────────────────────
    operativos = [
        {
            'id': 'fluidez_2026',
            'titulo': 'Fluidez Lectora 2026',
            'descripcion': 'Evaluación de fluidez lectora — Junio 2026',
            'icono': 'bi-book-half',
            'color': '#00bcd4',
            'links': [
                {
                    'titulo': 'Carga de datos',
                    'icono': 'bi-pencil-square',
                    'url': 'evaluaciones_educativas:fluidez_2026:lista',
                    'roles': ['Director/a'],
                },
                {
                    'titulo': 'Análisis de Resultados',
                    'icono': 'bi-bar-chart-line',
                    'url_director': 'evaluaciones_educativas:fluidez_2026:analisis_evaluacion',
                    'url_regional': 'evaluaciones_educativas:fluidez_2026:analisis_evaluacion_junio_2026',
                    'url_funcionario': 'evaluaciones_educativas:fluidez_2026:analisis_completo_evaluacion_junio_2026',
                    'roles': ['Director/a', 'Regional', 'Funcionario', 'Ministro', 'Subse'],
                },
            ],
        },
        {
            'id': 'diagnostico_2026',
            'titulo': 'Diagnóstico 2026',
            'descripcion': 'Evaluación diagnóstica — 2026',
            'icono': 'bi-journal-medical',
            'color': '#6366f1',
            'links': [
                {
                    'titulo': 'Carga de datos',
                    'icono': 'bi-pencil-square',
                    'url': 'evaluaciones_educativas:diagnostico_2026:inicio',
                    'roles': ['Director/a'],
                },
                {
                    'titulo': 'Análisis de Resultados',
                    'icono': 'bi-graph-up-arrow',
                    'url': 'evaluaciones_educativas:diagnostico_2026:analisis_evaluacion',
                    'roles': ['Director/a', 'Regional', 'Funcionario', 'Ministro', 'Subse'],
                },
                {
                    'titulo': 'Progreso de Alumnos',
                    'icono': 'bi-person-lines-fill',
                    'url': 'evaluaciones_educativas:diagnostico_2026:progreso_alumnos',
                    'roles': ['Director/a', 'Regional', 'Funcionario', 'Ministro', 'Subse'],
                },
            ],
        },
        {
            'id': 'fluidez_2025',
            'titulo': 'Fluidez Lectora 2025',
            'descripcion': 'Datos históricos de fluidez lectora — 2025',
            'icono': 'bi-clock-history',
            'color': '#f59e0b',
            'links': [
                {
                    'titulo': 'Carga de datos',
                    'icono': 'bi-pencil-square',
                    'url': 'evaluaciones_educativas:fluidez_2025:grados',
                    'roles': ['Director/a'],
                },
                {
                    'titulo': 'Análisis de Resultados',
                    'icono': 'bi-bar-chart-steps',
                    'url_director': 'evaluaciones_educativas:fluidez_2025:analisis_evaluacion',
                    'url_regional': 'evaluaciones_educativas:fluidez_2025:analisis_evaluacion_noviembre_2025',
                    'url_funcionario': 'evaluaciones_educativas:fluidez_2025:analisis_completo_evaluacion_noviembre_2025',
                    'roles': ['Director/a', 'Regional', 'Funcionario', 'Ministro', 'Subse'],
                },
                {
                    'titulo': 'Análisis Mayo 2025',
                    'icono': 'bi-calendar2-range',
                    'url': 'evaluaciones_educativas:fluidez_2025:analisis_evaluacion_mayo_2025',
                    'roles': ['Director/a'],
                },
            ],
        },
        {
            'id': 'diagnostico_2025',
            'titulo': 'Diagnóstico 2025',
            'descripcion': 'Datos históricos de evaluación diagnóstica — 2025',
            'icono': 'bi-clipboard-data',
            'color': '#14b8a6',
            'links': [
                {
                    'titulo': 'Análisis de Resultados',
                    'icono': 'bi-graph-up-arrow',
                    'url': 'evaluaciones_educativas:diagnostico_2025:analisis_evaluacion',
                    'roles': ['Director/a', 'Regional', 'Funcionario', 'Ministro', 'Subse'],
                },
            ],
        },
        {
            'id': 'validaciones_2026',
            'titulo': 'Validaciones Aprender 2026',
            'descripcion': 'Validar secciones, establecimientos y matrículas',
            'icono': 'bi-check2-circle',
            'color': '#06b6d4',
            'links': [
                {
                    'titulo': 'Gestión de Validaciones',
                    'icono': 'bi-shield-check',
                    'url': 'evaluaciones_educativas:validaciones_2026:lista',
                    'roles': ['Regional', 'Funcionario', 'Ministro', 'Subse'],
                },
            ],
        },
        # ──────────────────────────────────────────────────
        # ► EJEMPLO PARA AGREGAR NUEVOS OPERATIVOS:
        # {
        #     'id': 'nuevo_operativo',
        #     'titulo': 'Nombre del Operativo',
        #     'descripcion': 'Descripción breve',
        #     'icono': 'bi-journal-check',
        #     'color': '#10b981',
        #     'links': [
        #         {
        #             'titulo': 'Nombre del Link',
        #             'icono': 'bi-arrow-right-circle',
        #             'url': 'evaluaciones_educativas:namespace:name',
        #             'roles': ['Director/a', 'Regional', 'Funcionario', 'Ministro', 'Subse'],
        #         },
        #     ],
        # },
    ]

    # ── Filtrar por rol y resolver URLs ──────────────────────────
    operativos_visibles = []
    for op in operativos:
        links_visibles = []
        for link in op['links']:
            if rol not in link['roles']:
                continue
            # Resolver URL según rol
            if 'url' in link:
                url_resuelta = reverse(link['url'])
            elif es_director and 'url_director' in link:
                url_resuelta = reverse(link['url_director'])
            elif es_regional and 'url_regional' in link:
                url_resuelta = reverse(link['url_regional'])
            elif es_funcionario and 'url_funcionario' in link:
                url_resuelta = reverse(link['url_funcionario'])
            else:
                continue
            links_visibles.append({
                'titulo': link['titulo'],
                'icono': link['icono'],
                'url': url_resuelta,
            })
        # Solo mostrar el operativo si tiene al menos 1 link visible
        if links_visibles:
            operativos_visibles.append({
                'id': op['id'],
                'titulo': op['titulo'],
                'descripcion': op['descripcion'],
                'icono': op['icono'],
                'color': op['color'],
                'links': links_visibles,
            })

    context = {
        'usuario': usuario,
        'rol': rol,
        'es_director': es_director,
        'es_regional': es_regional,
        'es_funcionario': es_funcionario,
        'operativos': operativos_visibles,
    }
    return render(request, 'evaluaciones_educativas/dashboard.html', context)
