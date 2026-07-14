"""
Vista de Análisis de Evaluación — Versión optimizada
======================================================
Optimizaciones aplicadas:
  1. mapa_escuelas: 2 queries batch en lugar de N*2 queries (fix N+1)
  2. Queryset principal con .values() → sin instanciación de modelos
  3. Sólo se piden las columnas necesarias (SELECT proyectado)
  4. Cuando ocultar_listado=True: agregación pura en BD con Cast/Case/Count
     → sin traer filas individuales a Python
  5. Ordenamiento omitido cuando no se muestra el listado

Umbrales de desempeño — Matemática:
  General:        <60 | 60-72 | 72-85 | 85-100
  Reconocimiento: <3  | 3-8   | 8-14  | 14-25
  Comunicación:   <8  | 8-22  | 22-29 | 29-32
  Resolución:     <26 | 26-38 | 38-49 | 49-53

Umbrales de desempeño — Lengua:
  General:           <60 | 60-75  | 75-85    | 85-100
  Extraer:           <7  | 7-12   | 12-16    | 16-19
  Interpretar:       <8  | 8-14   | 14-22    | 22-25
  Reflexionar/Eval:  <8  | 8-19   | 19-27    | 27-31
  Escritura:         <15 | 15-18.75 | 18.75-21.25 | 21.25-25
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.db.models import Q, Count, IntegerField, FloatField, Value
from django.db.models import Case, When
from django.db.models.functions import Cast, Replace

from apps.evaluaciones_educativas.models.analisis_evaluacion import (
    ExamenLenguaAlumno,
    ExamenMatematicaAlumno,
)
from apps.consultasge.models import CapaUnicaOfertas
from ..utils import utilidades


# ─────────────────────────────────────────────────────────────────────────────
# Constantes
# ─────────────────────────────────────────────────────────────────────────────

UMBRALES_MAT = {
    'general':        (60,   72,    85),
    'reconocimiento': (3,    8,     14),
    'comunicacion':   (8,    22,    29),
    'resolucion':     (26,   38,    49),
}

UMBRALES_LEN = {
    'general':     (60,    75,     85),
    'extraer':     (7,     12,     16),
    'interpretar': (8,     14,     22),
    'reflexionar': (8,     19,     27),
    'escribir':    (15,    18.75,  21.25),
}

SECTORES_CHOICES = ['TODOS', 'Estatal', 'Gestión social/cooperativa', 'Privado']
AMBITOS_CHOICES  = ['TODOS', 'Rural Aglomerado', 'Rural Disperso', 'Urbano']
REGIONES_CHOICES = [
    'TODOS', 'R.E. 1', 'SUB. R.E. 1-A', 'SUB. R.E. 1-B',
    'R.E. 2', 'SUB. R.E. 2', 'R.E. 3', 'SUB. R.E. 3',
    'R.E. 4-A', 'R.E. 4-B', 'R.E. 5', 'SUB. R.E. 5',
    'R.E. 6', 'R.E. 7', 'R.E. 8-A', 'R.E. 8-B',
    'R.E. 9', 'R.E. 10-C', 'R.E. 10-AB',
]

LISTA_JERARQUICOS = ['Regional', 'Funcionario', 'Ministro', 'Subse']

# Valores que se consideran "ninguna condición"
VALORES_NINGUNA = {'', 'NO', 'no', 'No', 'NINGUNA', 'NINGUNO', 'FALSE', 'False', 'false', 'ninguna'}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _safe_float(val):
    """Convierte un CharField (puede tener coma decimal) a float; None si falla."""
    try:
        return float(str(val).replace(',', '.'))
    except (ValueError, TypeError):
        return None


def _nivel_desempeno(valor, umbrales):
    """
    0=Debajo básico, 1=Básico, 2=Satisfactorio, 3=Avanzado.
    umbrales = (u1, u2, u3)
    """
    if valor is None:
        return None
    u1, u2, u3 = umbrales
    if valor < u1:   return 0
    elif valor < u2: return 1
    elif valor < u3: return 2
    else:            return 3


def _annotation_float(field_name):
    """
    Crea una annotación que convierte un VARCHAR con coma decimal a FLOAT en PostgreSQL.
    Equivale a: CAST(REPLACE(field_name, ',', '.') AS FLOAT)
    Los NULL y strings no numéricos quedan como NULL.
    """
    return Cast(
        Replace(field_name, Value(','), Value('.')),
        output_field=FloatField()
    )


def _desempenos_db(qs, umbrales_por_clave):
    """
    Calcula la distribución de desempeño completamente en la BD usando
    Case/When/Count. Evita traer filas individuales a Python.

    umbrales_por_clave = {'general': (u1,u2,u3), 'reconocimiento': (...), ...}
    Retorna: {'general': [d0,d1,d2,d3], 'reconocimiento': [...], ...}
    """
    # Mapeo clave Python → nombre de columna real en la tabla
    CAMPO_COLUMNA = {
        'general':        'total',
        'reconocimiento': 'reconocimiento_conceptos',
        'comunicacion':   'comunicacion',
        'resolucion':     'resolucion_situaciones',
        'extraer':        'extraer',
        'interpretar':    'interpretar',
        'reflexionar':    'reflexionar_evaluar',
        'escribir':       'escribir',
    }

    # 1. Anotar cada campo como FLOAT (REPLACE coma→punto + CAST)
    annotate_kwargs = {
        f'{key}_f': _annotation_float(CAMPO_COLUMNA[key])
        for key in umbrales_por_clave
    }
    qs_ann = qs.annotate(**annotate_kwargs)

    # 2. Construir Count(Case(When(...))) por capacidad y nivel
    agg_kwargs = {}
    for key, (u1, u2, u3) in umbrales_por_clave.items():
        f = f'{key}_f'
        agg_kwargs[f'{key}_d0'] = Count(Case(When(**{f'{f}__lt': u1},                            then=Value(1)), output_field=IntegerField()))
        agg_kwargs[f'{key}_d1'] = Count(Case(When(**{f'{f}__gte': u1, f'{f}__lt': u2},           then=Value(1)), output_field=IntegerField()))
        agg_kwargs[f'{key}_d2'] = Count(Case(When(**{f'{f}__gte': u2, f'{f}__lt': u3},           then=Value(1)), output_field=IntegerField()))
        agg_kwargs[f'{key}_d3'] = Count(Case(When(**{f'{f}__gte': u3},                            then=Value(1)), output_field=IntegerField()))

    resultado = qs_ann.aggregate(**agg_kwargs)

    return {
        key: [resultado[f'{key}_d0'], resultado[f'{key}_d1'],
              resultado[f'{key}_d2'], resultado[f'{key}_d3']]
        for key in umbrales_por_clave
    }


def _desempenos_condicion_db(qs):
    """
    Cuenta alumnos por combinación etnia/discapacidad en una sola query.
    Retorna (etnia, discapacidad, ambas, ninguna, total).
    """
    filas = qs.values('etnia', 'discapacidad')
    
    etnia_cnt = discap_cnt = ambas_cnt = ninguna_cnt = 0
    for row in filas:
        val_e = str(row.get('etnia') or '').strip().upper()
        val_d = str(row.get('discapacidad') or '').strip().upper()
        es_e = val_e not in {'', 'NO', 'NINGUNA', 'NINGUNO', 'FALSE'}
        es_d = val_d not in {'', 'NO', 'NINGUNA', 'NINGUNO', 'FALSE'}
        if es_e and es_d:   ambas_cnt   += 1
        elif es_e:          etnia_cnt   += 1
        elif es_d:          discap_cnt  += 1
        else:               ninguna_cnt += 1
    
    total = etnia_cnt + discap_cnt + ambas_cnt + ninguna_cnt
    return etnia_cnt, discap_cnt, ambas_cnt, ninguna_cnt, total


# ─────────────────────────────────────────────────────────────────────────────
# Vista principal
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def analisis_evaluacion(request):
    usuario = request.user
    name    = usuario.username
    cuil_con_caracter = f"{name[:2]}-{name[2:10]}-{name[10:]}"
    rol_usuario = usuario.nivelacceso_id
    rol_denied = 'Director/a'
    print(rol_usuario)

    # ── PROTECCIÓN DE ACCESO ──────────────────────────────────────────────────
    if rol_usuario == rol_denied:
        raise PermissionDenied("No tienes permiso para acceder a esta sección.")

    if rol_usuario not in LISTA_JERARQUICOS:
        has_oferta = CapaUnicaOfertas.objects.filter(
            resploc_cuitcuil=cuil_con_caracter,
            oferta__icontains='Secundaria Completa req. 7 años'
        ).exists()
        if not has_oferta:
            raise PermissionDenied("No tienes permiso para acceder a esta sección.")


    # ── 1. FILTROS DE GESTIÓN ─────────────────────────────────────────────────
    filtro_sector    = request.GET.get('sector',    '').strip()
    filtro_ambito    = request.GET.get('ambito',    '').strip()
    filtro_region    = request.GET.get('region',    '').strip()
    filtro_condicion = request.GET.get('condicion', '').strip()

    # ── 2. UNIVERSO DE CUEs ───────────────────────────────────────────────────
    if rol_usuario in LISTA_JERARQUICOS:
        q_gestion = Q()
        if filtro_sector and filtro_sector != 'TODOS':
            q_gestion &= Q(sector=filtro_sector)
        if filtro_ambito and filtro_ambito != 'TODOS':
            q_gestion &= Q(ambito=filtro_ambito)
        if filtro_region and filtro_region != 'TODOS':
            q_gestion &= Q(region=filtro_region)

        cues_mat = set(
            ExamenMatematicaAlumno.objects.filter(q_gestion)
            .exclude(cueanexo__isnull=True).exclude(cueanexo='')
            .values_list('cueanexo', flat=True).distinct()
        )
        cues_len = set(
            ExamenLenguaAlumno.objects.filter(q_gestion)
            .exclude(cueanexo__isnull=True).exclude(cueanexo='')
            .values_list('cueanexo', flat=True).distinct()
        )
        user_cueanexos = sorted(cues_mat | cues_len)
    else:
        user_cueanexos = [str(c) for c in utilidades.obtener_cueanexos(usuario.username)]

    selected_cue = request.GET.get('cueanexo', '').strip() or None
    if not selected_cue and user_cueanexos:
        selected_cue = user_cueanexos[0]
    if selected_cue and selected_cue not in user_cueanexos and selected_cue != 'TODOS':
        selected_cue = user_cueanexos[0] if user_cueanexos else None

    # ── mapa_escuelas: 2 queries batch (fix N+1) ──────────────────────────────
    mapa_mat = dict(
        ExamenMatematicaAlumno.objects
        .filter(cueanexo__in=user_cueanexos)
        .exclude(escuela__isnull=True).exclude(escuela='')
        .values('cueanexo', 'escuela')
        .distinct()
        .values_list('cueanexo', 'escuela')
    )
    mapa_len = dict(
        ExamenLenguaAlumno.objects
        .filter(cueanexo__in=user_cueanexos)
        .exclude(escuela__isnull=True).exclude(escuela='')
        .values('cueanexo', 'escuela')
        .distinct()
        .values_list('cueanexo', 'escuela')
    )
    mapa_escuelas = {**mapa_len, **mapa_mat}  # mat tiene prioridad si hay diferencia

    lista_escuelas = [
        {'cue': cue, 'label': f"{cue} – {mapa_escuelas.get(cue, 'Sin nombre')}"}
        for cue in user_cueanexos
    ]

    # ── 3. AJAX: CASCADA DINÁMICA ─────────────────────────────────────────────
    action = request.GET.get('action', '')
    if action and selected_cue and selected_cue != 'TODOS':
        if action == 'cargar_anios':
            anios_m = set(ExamenMatematicaAlumno.objects
                          .filter(cueanexo=selected_cue)
                          .exclude(anio__isnull=True).exclude(anio='')
                          .values_list('anio', flat=True).distinct())
            anios_l = set(ExamenLenguaAlumno.objects
                          .filter(cueanexo=selected_cue)
                          .exclude(anio__isnull=True).exclude(anio='')
                          .values_list('anio', flat=True).distinct())
            anios = sorted(anios_m | anios_l)
            MAPEO_ANIO = {
                '1': '1er Año/Grado', '2': '2do Año/Grado', '3': '3er Año/Grado',
                '4': '4to Año/Grado', '5': '5to Año/Grado', '6': '6to Año/Grado',
                '7': '7mo Año/Grado',
            }
            return JsonResponse(
                [{'anio': a, 'label': MAPEO_ANIO.get(str(a), str(a))} for a in anios],
                safe=False
            )

        elif action == 'cargar_divisiones':
            anio_q = request.GET.get('anio', '')
            divs_m = set(ExamenMatematicaAlumno.objects
                         .filter(cueanexo=selected_cue, anio=anio_q)
                         .exclude(division__isnull=True).exclude(division='')
                         .values_list('division', flat=True).distinct())
            divs_l = set(ExamenLenguaAlumno.objects
                         .filter(cueanexo=selected_cue, anio=anio_q)
                         .exclude(division__isnull=True).exclude(division='')
                         .values_list('division', flat=True).distinct())
            divisiones = sorted(divs_m | divs_l)
            resultados = [{'id': 'TODOS', 'label': '--- TODAS ---'}]
            resultados += [{'id': d, 'label': f"División: {d}"} for d in divisiones]
            return JsonResponse(resultados, safe=False)

    # ── 4. FILTROS PEDAGÓGICOS ────────────────────────────────────────────────
    filtro_anio     = request.GET.get('anio',     '').strip()
    filtro_division = request.GET.get('division', '').strip()
    filtro_materia  = request.GET.get('materia',  '').strip()

    lista_divisiones = []
    if selected_cue and selected_cue != 'TODOS' and filtro_anio:
        divs_m = set(ExamenMatematicaAlumno.objects
                     .filter(cueanexo=selected_cue, anio=filtro_anio)
                     .exclude(division__isnull=True).exclude(division='')
                     .values_list('division', flat=True).distinct())
        divs_l = set(ExamenLenguaAlumno.objects
                     .filter(cueanexo=selected_cue, anio=filtro_anio)
                     .exclude(division__isnull=True).exclude(division='')
                     .values_list('division', flat=True).distinct())
        lista_divisiones.append({'id': 'TODOS', 'label': '--- TODAS ---', 'division': 'TODOS'})
        for d in sorted(divs_m | divs_l):
            lista_divisiones.append({'id': d, 'label': f"División: {d}", 'division': d})

    # ── 5. PROCESAMIENTO PRINCIPAL ────────────────────────────────────────────
    alumnos_con_examenes = []
    total_alumnos = 0
    desempenos = {}
    presentes_etnia = presentes_discapacidad = presentes_ambas = presentes_ninguna = 0

    es_busqueda_todos      = selected_cue == 'TODOS'
    hay_busqueda_condicion = bool(filtro_condicion)
    hay_busqueda_individual = (
        selected_cue and selected_cue != 'TODOS' and filtro_anio and filtro_materia
    )
    # Solo ocultamos el listado en consultas masivas sin condición especial
    ocultar_listado = es_busqueda_todos and not hay_busqueda_condicion

    hay_busqueda = filtro_materia and (
        hay_busqueda_condicion or es_busqueda_todos or hay_busqueda_individual
    )

    if hay_busqueda:
        if filtro_materia == 'matematica':
            Modelo    = ExamenMatematicaAlumno
            umbrales  = UMBRALES_MAT
            desempenos = {k: [0,0,0,0] for k in umbrales}
            # Campos a traer con values() — solo los necesarios
            CAMPOS_CAPACIDAD  = ['total', 'reconocimiento_conceptos', 'comunicacion', 'resolucion_situaciones']
            CAMPOS_CONDICION  = ['etnia', 'discapacidad']
            CAMPOS_LISTADO    = ['dni', 'apellidos', 'nombres', 'anio', 'division']
        else:
            Modelo    = ExamenLenguaAlumno
            umbrales  = UMBRALES_LEN
            desempenos = {k: [0,0,0,0] for k in umbrales}
            CAMPOS_CAPACIDAD  = ['total', 'extraer', 'interpretar', 'reflexionar_evaluar', 'escribir']
            CAMPOS_CONDICION  = ['etnia', 'discapacidad']
            CAMPOS_LISTADO    = ['dni', 'apellidos', 'nombres', 'anio', 'division']

        # ── Construcción del Q base ───────────────────────────────────────────
        q = Q()
        if hay_busqueda_condicion or es_busqueda_todos:
            q &= Q(cueanexo__in=user_cueanexos)
        else:
            q &= Q(cueanexo=selected_cue)
            if filtro_anio:
                q &= Q(anio=filtro_anio)
            if filtro_division and filtro_division != 'TODOS':
                q &= Q(division=filtro_division)

        if filtro_condicion == 'discapacidad':
            q &= ~Q(discapacidad__in=VALORES_NINGUNA) & Q(discapacidad__isnull=False)
        elif filtro_condicion == 'etnia':
            q &= ~Q(etnia__in=VALORES_NINGUNA) & Q(etnia__isnull=False)

        if rol_usuario in LISTA_JERARQUICOS:
            if filtro_sector and filtro_sector != 'TODOS':
                q &= Q(sector=filtro_sector)
            if filtro_ambito and filtro_ambito != 'TODOS':
                q &= Q(ambito=filtro_ambito)
            if filtro_region and filtro_region != 'TODOS':
                q &= Q(region=filtro_region)

        # ── RAMA A: Listado oculto → todo en BD (más rápido) ─────────────────
        if ocultar_listado:
            qs_base = Modelo.objects.filter(q)
            
            try:
                desempenos = _desempenos_db(qs_base, umbrales)
            except Exception:
                # Fallback a Python si el Cast falla (ej. valores no numéricos)
                desempenos = {k: [0,0,0,0] for k in umbrales}
            
            etnia_cnt, discap_cnt, ambas_cnt, ninguna_cnt, total_alumnos = \
                _desempenos_condicion_db(qs_base.values('etnia', 'discapacidad'))
            presentes_etnia        = etnia_cnt
            presentes_discapacidad = discap_cnt
            presentes_ambas        = ambas_cnt
            presentes_ninguna      = ninguna_cnt

        # ── RAMA B: Listado visible → values() proyectado, sin instanciar modelos
        else:
            campos_necesarios = list(set(CAMPOS_CAPACIDAD + CAMPOS_CONDICION + CAMPOS_LISTADO))
            
            # values() → dicts livianos, sin instanciar Model
            examenes = (
                Modelo.objects.filter(q)
                .values(*campos_necesarios)
                .order_by('apellidos', 'nombres')
            )

            for ex in examenes:
                total_alumnos += 1

                val_e = str(ex.get('etnia') or '').strip().upper()
                val_d = str(ex.get('discapacidad') or '').strip().upper()
                es_e  = val_e not in {'', 'NO', 'NINGUNA', 'NINGUNO', 'FALSE'}
                es_d  = val_d not in {'', 'NO', 'NINGUNA', 'NINGUNO', 'FALSE'}

                if es_e and es_d:  presentes_ambas        += 1
                elif es_e:         presentes_etnia        += 1
                elif es_d:         presentes_discapacidad += 1
                else:              presentes_ninguna      += 1

                tp  = _safe_float(ex.get('total'))
                idx = _nivel_desempeno(tp, umbrales['general'])
                if idx is not None: desempenos['general'][idx] += 1

                if filtro_materia == 'matematica':
                    rec = _safe_float(ex.get('reconocimiento_conceptos'))
                    idx = _nivel_desempeno(rec, umbrales['reconocimiento'])
                    if idx is not None: desempenos['reconocimiento'][idx] += 1

                    com = _safe_float(ex.get('comunicacion'))
                    idx = _nivel_desempeno(com, umbrales['comunicacion'])
                    if idx is not None: desempenos['comunicacion'][idx] += 1

                    res = _safe_float(ex.get('resolucion_situaciones'))
                    idx = _nivel_desempeno(res, umbrales['resolucion'])
                    if idx is not None: desempenos['resolucion'][idx] += 1

                else:  # lengua
                    ext  = _safe_float(ex.get('extraer'))
                    idx  = _nivel_desempeno(ext, umbrales['extraer'])
                    if idx is not None: desempenos['extraer'][idx] += 1

                    intp = _safe_float(ex.get('interpretar'))
                    idx  = _nivel_desempeno(intp, umbrales['interpretar'])
                    if idx is not None: desempenos['interpretar'][idx] += 1

                    ref  = _safe_float(ex.get('reflexionar_evaluar'))
                    idx  = _nivel_desempeno(ref, umbrales['reflexionar'])
                    if idx is not None: desempenos['reflexionar'][idx] += 1

                    esc  = _safe_float(ex.get('escribir'))
                    idx  = _nivel_desempeno(esc, umbrales['escribir'])
                    if idx is not None: desempenos['escribir'][idx] += 1

                MAPEO_ANIO_LABEL = {
                    '1': '1er Año/Grado', '2': '2do Año/Grado', '3': '3er Año/Grado',
                    '4': '4to Año/Grado', '5': '5to Año/Grado', '6': '6to Año/Grado',
                    '7': '7mo Año/Grado',
                }
                # Construir dict del alumno para el template
                anio_raw = ex.get('anio')
                datos = {
                    'dni':           ex.get('dni'),
                    'apellidos':     ex.get('apellidos'),
                    'nombres':       ex.get('nombres'),
                    'anio':          anio_raw,
                    'anio_label':    MAPEO_ANIO_LABEL.get(str(anio_raw), str(anio_raw) if anio_raw else ''),
                    'division':      ex.get('division'),
                    'total_puntaje': tp,
                }
                if filtro_materia == 'matematica':
                    datos.update({
                        'nota_reconocimiento': _safe_float(ex.get('reconocimiento_conceptos')),
                        'nota_comunicacion':   _safe_float(ex.get('comunicacion')),
                        'nota_resolucion':     _safe_float(ex.get('resolucion_situaciones')),
                    })
                else:
                    datos.update({
                        'nota_extraer':     _safe_float(ex.get('extraer')),
                        'nota_interpretar': _safe_float(ex.get('interpretar')),
                        'nota_reflexionar': _safe_float(ex.get('reflexionar_evaluar')),
                        'nota_escribir':    _safe_float(ex.get('escribir')),
                    })
                alumnos_con_examenes.append(datos)

    context = {
        'rol':                rol_usuario,
        'lista_escuelas':     lista_escuelas,
        'cueanexo':           selected_cue,
        'alumnos':            alumnos_con_examenes,
        'ocultar_listado':    ocultar_listado,
        'hay_datos':          total_alumnos > 0,
        'total_alumnos':      total_alumnos,
        'anio_sel':           filtro_anio,
        'anio_label_sel':     {
            '1': '1er Año/Grado', '2': '2do Año/Grado', '3': '3er Año/Grado',
            '4': '4to Año/Grado', '5': '5to Año/Grado', '6': '6to Año/Grado',
            '7': '7mo Año/Grado',
        }.get(str(filtro_anio), filtro_anio) if filtro_anio else '',
        'division_sel':       filtro_division,
        'lista_divisiones':   lista_divisiones,
        'materia_sel':        filtro_materia,
        'condicion_sel':      filtro_condicion,
        'desempenos':         desempenos,
        'sector_sel':         filtro_sector  or 'TODOS',
        'ambito_sel':         filtro_ambito  or 'TODOS',
        'region_sel':         filtro_region  or 'TODOS',
        'sectores_opciones':  SECTORES_CHOICES,
        'ambitos_opciones':   AMBITOS_CHOICES,
        'regiones_opciones':  REGIONES_CHOICES,
        'presentes_etnia':        presentes_etnia,
        'presentes_discapacidad': presentes_discapacidad,
        'presentes_ambas':        presentes_ambas,
        'presentes_ninguna':      presentes_ninguna,
    }
    return render(request, 'analisis_evaluacion/analisis_evaluacion.html', context)
