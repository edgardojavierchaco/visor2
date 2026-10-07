"""
Secciones de 2º y 3º grado para la carga de aplicadores de Fluidez Octubre 2026.

Las escuelas son las mismas que se muestran a los tabuladores (CapaUnicaOfertas,
base default) y sus secciones se leen de la vista materializada
public.trayectoria_alumnos_sge (base sge_nacion). Son dos bases distintas, por
eso primero se obtienen los cueanexos y después se pasan como filtro IN.

Solo lectura: nunca se escribe en sge_nacion.
"""
from django.db import connections

from apps.consultasge.models import CapaUnicaOfertas

DB_SGE = 'sge_nacion'

# Valores de anio_grado en trayectoria_alumnos_sge para este operativo.
GRADOS_OPERATIVO = ['2do Año/Grado', '3er Año/Grado']

# La vista trae más de un ciclo lectivo y cada sección tiene un id_seccion
# distinto por ciclo: sin este filtro las secciones aparecen duplicadas.
CICLO_LECTIVO = 2026

# Mismo filtro de oferta que usa asignacion_tabulador. Si cambia allá,
# hay que cambiarlo también acá.
OFERTA_ESCUELAS = 'Común - Primaria de 7 años'

# La vista tiene una fila por alumno: se agrupa por sección. Una sección
# plurigrado (alumnos de 2º y 3º en el mismo grupo) tiene filas de los dos
# grados; `grados` los junta y la sección queda como una sola, con un solo
# aplicador para ambos grados.
SQL_SECCIONES = """
    SELECT id_seccion,
           MIN(id_institucion)                              AS id_institucion,
           MIN(cueanexo)                                    AS cueanexo,
           MIN(escuela)                                     AS escuela,
           MIN(c_grado_nivel_servicio)                      AS c_grado_nivel_servicio,
           array_agg(DISTINCT anio_grado ORDER BY anio_grado) AS grados,
           MIN(nombre_seccion)                              AS nombre_seccion,
           MIN(turno)                                       AS turno,
           MIN(ciclo_lectivo)                               AS ciclo_lectivo,
           MIN(localidad)                                   AS localidad,
           MIN(departamento)                                AS departamento
    FROM public.trayectoria_alumnos_sge
    WHERE cueanexo = ANY(%s)
      AND anio_grado = ANY(%s)
      AND anio_ciclo = %s
      AND id_seccion IS NOT NULL
      {filtro_seccion}
    GROUP BY id_seccion
"""


def cueanexos_region(region):
    """Cueanexos de las escuelas que ven los tabuladores de la región."""
    return sorted({
        str(c).strip()
        for c in CapaUnicaOfertas.objects
        .filter(region_loc=region, oferta__icontains=OFERTA_ESCUELAS)
        .values_list('cueanexo', flat=True)
        if c is not None
    })


def secciones_region(region, id_seccion=None):
    """
    Secciones de 2º y 3º grado de las escuelas de la región, ordenadas por
    escuela, grado y sección. Con `id_seccion` devuelve solo esa sección
    (lista vacía si no es de la región o del grado del operativo).
    """
    cueanexos = cueanexos_region(region)
    if not cueanexos:
        return []

    params = [cueanexos, GRADOS_OPERATIVO, CICLO_LECTIVO]
    filtro_seccion = ''
    if id_seccion is not None:
        filtro_seccion = 'AND id_seccion = %s'
        params.append(id_seccion)

    with connections[DB_SGE].cursor() as cur:
        cur.execute(SQL_SECCIONES.format(filtro_seccion=filtro_seccion), params)
        columnas = [c[0] for c in cur.description]
        secciones = [dict(zip(columnas, fila)) for fila in cur.fetchall()]

    for s in secciones:
        s['cueanexo'] = str(s['cueanexo']).strip()
        grados = list(s['grados'] or [])
        s['plurigrado'] = len(grados) > 1
        # Lo que se guarda en SeccionesAplicadorFluidezOctubre2026.anio_grado
        s['anio_grado'] = ' / '.join(grados)
        # Texto corto de los grados: "2º", "2º y 3º"
        s['grados_corto'] = ' y '.join(g.split(' ')[0].replace('do', 'º').replace('er', 'º') for g in grados)
        if s['plurigrado']:
            grado_txt = f"{s['grados_corto']} grado (plurigrado)"
        else:
            grado_txt = s['anio_grado']
        s['label'] = f"{grado_txt} — Sección {s['nombre_seccion']} — {s['turno'] or 'Sin turno'}"

    secciones.sort(key=lambda s: (s['escuela'] or '', s['grados'][0] if s['grados'] else '', str(s['nombre_seccion'] or '')))
    return secciones
