"""
Monitoreo de la carga de personas por regional (operativos 2026).

Dos operativos, cada uno con sus propias personas:
  - Fluidez Octubre 2026: aplicadores (uno por sección de 2º/3º grado) y
    tabuladores (cupo por región, cada uno con una lista de escuelas).
  - Aprender 2026 (validaciones_2026): aplicadores (uno por sección
    habilitada) y veedores (uno por escuela que participa, más un asistente
    opcional si la escuela tiene 2 o más secciones).

Solo lectura: acá no se escribe nada.
"""
import re
from collections import Counter

from django.core.cache import cache
from django.db.models import Count, Q

from apps.consultasge.models import CapaUnicaOfertas
from apps.evaluaciones_educativas.models.fluidez_octubre_2026 import (
    AplicadoresFluidezOctubre2026,
    SeccionesAplicadorFluidezOctubre2026,
    TabuladoresFluidezOctubre2026,
    TemporalCargaTabuladoresFluidez2026Eliminar,
)
from apps.evaluaciones_educativas.models.validaciones_2026 import (
    ValAplicador,
    ValEstablecimiento,
    ValSeccion,
    ValVeedor,
)
from apps.evaluaciones_educativas.services.fluidez_octubre_2026 import (
    CICLO_LECTIVO,
    conexion_sge,
    GRADOS_OPERATIVO,
    OFERTA_ESCUELAS,
)

# El padrón de escuelas y las secciones de SGE son consultas pesadas (la
# segunda a otra base) y cambian poco durante el operativo: se guardan unos
# minutos. Lo cargado por las regionales se lee siempre en el momento.
# Regionales que no se muestran. R.E. 10-AB es una fila de cupo que junta a
# 10-A y 10-B (su cupo es la suma de los dos); cada una ya tiene su propio cupo,
# así que mostrarla duplicaba el total de tabuladores.
REGIONES_OCULTAS = {'R.E. 10-AB'}

CACHE_ESCUELAS = 'monitoreo_personas_2026:escuelas'
CACHE_SECCIONES_SGE = 'monitoreo_personas_2026:secciones_sge'
CACHE_SEGUNDOS = 10 * 60

SQL_SECCIONES_POR_ESCUELA = """
    SELECT cueanexo, COUNT(DISTINCT id_seccion)
    FROM public.trayectoria_alumnos_sge
    WHERE cueanexo = ANY(%s)
      AND anio_grado = ANY(%s)
      AND anio_ciclo = %s
      AND id_seccion IS NOT NULL
    GROUP BY cueanexo
"""


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------
def orden_region(region):
    """'R.E. 2' antes que 'R.E. 10-A'; las subregionales al final."""
    numero = re.search(r'\d+', region or '')
    return (
        (region or '').startswith('SUB'),
        int(numero.group()) if numero else 0,
        region or '',
    )


def porcentaje(cargados, esperados):
    if not esperados:
        return None
    return min(round(cargados * 100 / esperados), 100)


def estado(cargados, esperados):
    """Semáforo: 'sin_meta' | 'sin_iniciar' | 'en_curso' | 'completa'."""
    if not esperados:
        return 'sin_meta'
    if not cargados:
        return 'sin_iniciar'
    if cargados >= esperados:
        return 'completa'
    return 'en_curso'


def _indicador(cargados, esperados):
    return {
        'cargados': cargados,
        'esperados': esperados,
        'faltan': max((esperados or 0) - cargados, 0),
        'pct': porcentaje(cargados, esperados),
        'estado': estado(cargados, esperados),
    }


def _estado_general(*indicadores):
    """Estado de la regional según el más atrasado de sus indicadores."""
    estados = [i['estado'] for i in indicadores if i['estado'] != 'sin_meta']
    if not estados:
        return 'sin_meta'
    if all(e == 'completa' for e in estados):
        return 'completa'
    if all(e == 'sin_iniciar' for e in estados):
        return 'sin_iniciar'
    return 'en_curso'


def _avance(*indicadores):
    """Promedio de los porcentajes de los indicadores; None si ninguno tiene meta."""
    pcts = [i['pct'] for i in indicadores if i['pct'] is not None]
    return round(sum(pcts) / len(pcts)) if pcts else None


def _faltantes_region(indicadores):
    """['120 secciones sin aplicador', '2 tabuladores', ...] de una regional."""
    return [
        f"{i['faltan']} {singular if i['faltan'] == 1 else plural}"
        for i, singular, plural in indicadores
        if i['faltan']
    ]


def _faltan_aplicadores(indicador):
    """Lista de faltantes de una escuela, empezando por sus aplicadores."""
    n = indicador['faltan']
    if not n:
        return []
    return [f"{n} aplicador{'es' if n != 1 else ''}"]


def _totales(filas, claves):
    totales = {'estados': Counter(f['estado'] for f in filas)}
    for clave in claves:
        cargados = sum(f[clave]['cargados'] for f in filas)
        esperados = sum(f[clave]['esperados'] or 0 for f in filas)
        totales[clave] = _indicador(cargados, esperados)
    return totales


# ---------------------------------------------------------------------------
# FLUIDEZ OCTUBRE 2026
# ---------------------------------------------------------------------------
def escuelas_fluidez(refrescar=False):
    """{cueanexo: {'escuela', 'region', 'localidad'}} de las escuelas del operativo."""
    if not refrescar:
        guardado = cache.get(CACHE_ESCUELAS)
        if guardado is not None:
            return guardado

    escuelas = {}
    for cueanexo, nombre, region, localidad in (
        CapaUnicaOfertas.objects
        .filter(oferta__icontains=OFERTA_ESCUELAS)
        .values_list('cueanexo', 'nom_est', 'region_loc', 'localidad')
    ):
        if cueanexo is None:
            continue
        escuelas[str(cueanexo).strip()] = {
            'escuela': (nombre or '').strip(),
            'region': (region or '').strip(),
            'localidad': (localidad or '').strip(),
        }
    cache.set(CACHE_ESCUELAS, escuelas, CACHE_SEGUNDOS)
    return escuelas


def secciones_sge_por_escuela(cueanexos, refrescar=False):
    """
    {cueanexo: cantidad de secciones de 2º/3º} leído de sge_nacion.
    Puede lanzar DatabaseError si sge_nacion no responde.
    """
    if not refrescar:
        guardado = cache.get(CACHE_SECCIONES_SGE)
        if guardado is not None:
            return guardado

    with conexion_sge().cursor() as cur:
        cur.execute(SQL_SECCIONES_POR_ESCUELA, [sorted(cueanexos), GRADOS_OPERATIVO, CICLO_LECTIVO])
        secciones = {str(c).strip(): n for c, n in cur.fetchall()}

    cache.set(CACHE_SECCIONES_SGE, secciones, CACHE_SEGUNDOS)
    return secciones


def _secciones_con_aplicador_por_escuela():
    return {
        str(c).strip(): n
        for c, n in (
            SeccionesAplicadorFluidezOctubre2026.objects
            .values_list('cueanexo')
            .annotate(n=Count('pk'))
        )
    }


def _tabulador_por_escuela():
    """{cueanexo: cuil del tabulador que la tiene asignada}."""
    asignadas = {}
    for cuil, lista in TabuladoresFluidezOctubre2026.objects.values_list('cuil', 'lista_cueanexos'):
        for cueanexo in (lista or []):
            asignadas[str(cueanexo).strip()] = cuil
    return asignadas


def escuelas_del_operativo(secciones_sge):
    """
    Escuelas que entran al operativo de Fluidez: las del padrón que tienen al
    menos una sección de 2º o 3º en SGE. Las bases y extensiones que solo
    tienen otros grados (1º, 4º a 7º, nivel inicial) o que SGE no tiene quedan
    afuera, porque no necesitan aplicador.

    Si SGE no respondió (`secciones_sge` es None) no se puede filtrar y se
    devuelven todas las del padrón.
    """
    escuelas = escuelas_fluidez()
    if secciones_sge is None:
        return escuelas
    return {c: e for c, e in escuelas.items() if secciones_sge.get(c, 0) > 0}


def resumen_fluidez(secciones_sge):
    """
    Una fila por regional. `secciones_sge` es el dict de
    secciones_sge_por_escuela, o None si SGE no respondió (en ese caso el
    indicador de aplicadores queda sin meta).
    """
    escuelas = escuelas_del_operativo(secciones_sge)
    con_aplicador = _secciones_con_aplicador_por_escuela()
    tabulador_de = _tabulador_por_escuela()

    aplicadores_por_region = dict(
        AplicadoresFluidezOctubre2026.objects.values_list('region').annotate(n=Count('pk'))
    )
    aplicadores_sin_seccion = dict(
        AplicadoresFluidezOctubre2026.objects
        .annotate(cant=Count('secciones'))
        .filter(cant=0)
        .values_list('region')
        .annotate(n=Count('pk'))
    )
    tabuladores_por_region = dict(
        TabuladoresFluidezOctubre2026.objects.values_list('region').annotate(n=Count('pk'))
    )
    cupos = dict(
        TemporalCargaTabuladoresFluidez2026Eliminar.objects.values_list('region', 'tabuladores_permitidos')
    )

    regiones = (
        {e['region'] for e in escuelas.values() if e['region']}
        | {r for r in cupos if r}
        | {r for r in aplicadores_por_region if r}
        | {r for r in tabuladores_por_region if r}
    ) - REGIONES_OCULTAS

    filas = []
    for region in sorted(regiones, key=orden_region):
        cues = [c for c, e in escuelas.items() if e['region'] == region]
        secciones_total = sum(secciones_sge.get(c, 0) for c in cues) if secciones_sge is not None else None
        secciones_cubiertas = sum(con_aplicador.get(c, 0) for c in cues)
        aplicadores = _indicador(secciones_cubiertas, secciones_total)

        tabuladores = _indicador(tabuladores_por_region.get(region, 0), cupos.get(region, 0))
        escuelas_tab = _indicador(sum(1 for c in cues if c in tabulador_de), len(cues))

        sin_seccion = aplicadores_sin_seccion.get(region, 0)
        filas.append({
            'region': region,
            'aplicadores': aplicadores,
            'aplicadores_cargados': aplicadores_por_region.get(region, 0),
            'aplicadores_sin_seccion': sin_seccion,
            'nota_aplicadores': (
                f"{sin_seccion} aplicador{'es' if sin_seccion != 1 else ''} sin sección asignada"
                if sin_seccion else ''
            ),
            'tabuladores': tabuladores,
            'escuelas_tabulador': escuelas_tab,
            'estado': _estado_general(aplicadores, tabuladores, escuelas_tab),
            'avance': _avance(aplicadores, tabuladores, escuelas_tab),
            'faltantes': _faltantes_region([
                (aplicadores, 'sección sin aplicador', 'secciones sin aplicador'),
                (tabuladores, 'tabulador', 'tabuladores'),
                (escuelas_tab, 'escuela sin tabulador', 'escuelas sin tabulador'),
            ]),
        })

    totales = _totales(filas, ['aplicadores', 'tabuladores', 'escuelas_tabulador'])
    totales['aplicadores_cargados'] = sum(f['aplicadores_cargados'] for f in filas)
    if secciones_sge is None:
        totales['aplicadores'] = _indicador(totales['aplicadores']['cargados'], None)
    return {'filas': filas, 'totales': totales}


def detalle_fluidez(region, secciones_sge):
    """Escuelas de la regional con sus secciones cubiertas y su tabulador."""
    escuelas = escuelas_del_operativo(secciones_sge)
    con_aplicador = _secciones_con_aplicador_por_escuela()
    tabulador_de = _tabulador_por_escuela()

    filas = []
    for cueanexo, e in escuelas.items():
        if e['region'] != region:
            continue
        total = secciones_sge.get(cueanexo, 0) if secciones_sge is not None else None
        aplicadores = _indicador(con_aplicador.get(cueanexo, 0), total)
        tiene_tabulador = cueanexo in tabulador_de
        faltantes = _faltan_aplicadores(aplicadores)
        if not tiene_tabulador:
            faltantes.append('tabulador')
        filas.append({
            'cueanexo': cueanexo,
            'escuela': e['escuela'],
            'localidad': e['localidad'],
            'aplicadores': aplicadores,
            'tiene_tabulador': tiene_tabulador,
            'pendiente': bool(faltantes),
            'faltantes': faltantes,
            'peso_pendiente': aplicadores['faltan'] + (0 if tiene_tabulador else 1),
        })
    filas.sort(key=lambda f: f['escuela'])
    return filas


# ---------------------------------------------------------------------------
# APRENDER 2026 (validaciones_2026)
# ---------------------------------------------------------------------------
def _escuelas_aprender():
    # En la base el valor está guardado en minúsculas ('participa'), aunque
    # el TextChoices del modelo esté en mayúsculas.
    return ValEstablecimiento.objects.filter(participa_aprender__iexact='participa')


def _secciones_habilitadas():
    return (
        ValSeccion.objects
        .filter(grado__establecimiento__participa_aprender__iexact='participa')
        .exclude(estado_validacion='DESHABILITADO')
    )


def resumen_aprender():
    escuelas_por_region = dict(
        _escuelas_aprender().values_list('region').annotate(n=Count('pk'))
    )
    secciones_por_region = dict(
        _secciones_habilitadas().values_list('grado__establecimiento__region').annotate(n=Count('pk'))
    )
    secciones_con_aplicador = dict(
        _secciones_habilitadas()
        .filter(aplicadores__isnull=False)
        .values_list('grado__establecimiento__region')
        .annotate(n=Count('pk'))
    )
    veedores = (
        ValVeedor.objects
        .filter(establecimiento__participa_aprender__iexact='participa')
        .values_list('establecimiento__region')
    )
    escuelas_con_veedor = dict(
        veedores.filter(asistente_veedor=False).annotate(n=Count('establecimiento', distinct=True))
    )
    asistentes = dict(veedores.filter(asistente_veedor=True).annotate(n=Count('pk')))

    regiones = set(escuelas_por_region) | set(
        ValEstablecimiento.objects.values_list('region', flat=True).distinct()
    )

    filas = []
    for region in sorted((r for r in regiones if r and r not in REGIONES_OCULTAS), key=orden_region):
        aplicadores = _indicador(secciones_con_aplicador.get(region, 0), secciones_por_region.get(region, 0))
        veedores_ind = _indicador(escuelas_con_veedor.get(region, 0), escuelas_por_region.get(region, 0))
        filas.append({
            'region': region,
            'escuelas': escuelas_por_region.get(region, 0),
            'aplicadores': aplicadores,
            'veedores': veedores_ind,
            'asistentes': asistentes.get(region, 0),
            'estado': _estado_general(aplicadores, veedores_ind),
            'avance': _avance(aplicadores, veedores_ind),
            'faltantes': _faltantes_region([
                (aplicadores, 'sección sin aplicador', 'secciones sin aplicador'),
                (veedores_ind, 'escuela sin veedor', 'escuelas sin veedor'),
            ]),
        })

    totales = _totales(filas, ['aplicadores', 'veedores'])
    totales['escuelas'] = sum(f['escuelas'] for f in filas)
    totales['asistentes'] = sum(f['asistentes'] for f in filas)
    return {'filas': filas, 'totales': totales}


def detalle_aprender(region):
    """Escuelas que participan en la regional, con aplicadores y veedores."""
    escuelas = list(_escuelas_aprender().filter(region=region).order_by('escuela'))

    secciones = dict(
        _secciones_habilitadas()
        .filter(grado__establecimiento__region=region)
        .values_list('grado__establecimiento')
        .annotate(n=Count('pk'))
    )
    con_aplicador = dict(
        _secciones_habilitadas()
        .filter(grado__establecimiento__region=region, aplicadores__isnull=False)
        .values_list('grado__establecimiento')
        .annotate(n=Count('pk'))
    )
    veedores = (
        ValVeedor.objects
        .filter(establecimiento__region=region)
        .values('establecimiento')
        .annotate(
            principal=Count('pk', filter=Q(asistente_veedor=False)),
            asistente=Count('pk', filter=Q(asistente_veedor=True)),
        )
    )
    veedores = {v['establecimiento']: v for v in veedores}

    filas = []
    for est in escuelas:
        cant_secciones = secciones.get(est.cueanexo, 0)
        aplicadores = _indicador(con_aplicador.get(est.cueanexo, 0), cant_secciones)
        v = veedores.get(est.cueanexo, {})
        tiene_veedor = bool(v.get('principal'))
        faltantes = _faltan_aplicadores(aplicadores)
        if not tiene_veedor:
            faltantes.append('veedor')
        filas.append({
            'cueanexo': est.cueanexo,
            'escuela': est.escuela,
            'localidad': est.localidad,
            'aplicadores': aplicadores,
            'tiene_veedor': tiene_veedor,
            'tiene_asistente': bool(v.get('asistente')),
            # El asistente solo se admite con 2 o más secciones habilitadas.
            'admite_asistente': cant_secciones >= 2,
            'pendiente': bool(faltantes),
            'faltantes': faltantes,
            'peso_pendiente': aplicadores['faltan'] + (0 if tiene_veedor else 1),
        })
    return filas
