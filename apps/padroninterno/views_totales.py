import logging
from hashlib import sha256

from django.core.cache import cache
from django.http import JsonResponse
from django.db import DatabaseError, connections
from django.shortcuts import render
from django.views.decorators.http import require_GET

from .permisos import (
    padron_interno_admin_o_gestor_required,
    padron_interno_required_json,
)

from .views_fecha import get_contexto_fecha_padron


logger = logging.getLogger(__name__)

# Las vistas actualizadas de Padrón utilizan la conexión default.
PADRON_DB = 'Padron'

# El resumen contiene únicamente cantidades agrupadas; nunca se envían CUE ni
# establecimientos al navegador. La clave incluye la fecha vigente del padrón,
# de modo que un refresh genera automáticamente una versión nueva.
RESUMEN_TOTALES_CACHE_PREFIX = 'padroninterno:totales-resumen:v3'
RESUMEN_TOTALES_CACHE_TIMEOUT = 24 * 60 * 60

# Modalidades que se pueden abrir en la pantalla.
MODALIDADES = {
    'comunes': 1,
    'especiales': 2,
    'adultos': 3,
}

# Datos de presentación para el selector principal. Se mantiene MODALIDADES
# como mapa clave -> id porque también se usa en la lógica existente.
MODALIDADES_PANTALLA = {
    'comunes': {
        'titulo': 'Común',
    },
    'adultos': {
        'titulo': 'Adultos',
    },
    'especiales': {
        'titulo': 'Especial',
    },
}

# Criterios permitidos para el desglose.
# No se usa texto de la URL directamente en SQL. Los criterios cortos se
# muestran completos en un árbol; los geográficos conservan un selector para
# evitar cargar listados demasiado largos.
CRITERIOS_DESGLOSE = {
    'ambito': {
    'titulo': 'Ámbito',
    'tipo': 'arbol',
    'campo': """
        COALESCE(
            NULLIF(BTRIM(vol.cp_of_ambito), ''),
            'SIN AMBITO'
        )
    """,
    'nodos_fijos': (
        ('R-Rural', 'Rural'),
        ('U-Urbano', 'Urbano'),
        ('SIN AMBITO', 'Sin ámbito informado'),
    ),
},
    'sigla': {
        'titulo': 'Sigla',
        'tipo': 'arbol',
        'campo': "COALESCE(BTRIM(vol.cp_acronimo), '')",
    },
        'nivel': {
        'titulo': 'Nivel',
        'tipo': 'arbol',
        'campo': """
            COALESCE(
                NULLIF(BTRIM(vol.cp_of_nivel), ''),
                'SIN NIVEL'
            )
        """,
    },
    'oferta': {
        'titulo': 'Oferta',
        'tipo': 'arbol',
        'campo': "COALESCE(BTRIM(vol.oferta), '')",
    },
    'regional': {
        'titulo': 'Regional',
        'tipo': 'selector',
        'campo': "COALESCE(BTRIM(vl.cp_esvat5), '')",
    },
    'departamento': {
        'titulo': 'Departamento',
        'tipo': 'selector',
        'campo': "COALESCE(BTRIM(vl.departamento_nombre), '')",
    },
    'localidad': {
        'titulo': 'Localidad',
        'tipo': 'selector',
        'campo': "COALESCE(BTRIM(vl.localidad_nombre), '')",
    },
    'sector': {
        'titulo': 'Sector',
        'tipo': 'arbol',
        'campo': "COALESCE(BTRIM(vl.sector), '')",
    },
}

NIVELES = {
    'inicial': {
        'titulo': 'Inicial',
        'valor_db': 'Inicial-Inicial',

        'columnas_principales': [
            ('total', 'Total iniciales'),
            ('comunes', 'Comunes'),
            ('especiales', 'Especiales'),
        ],

        'desglose_comunes': [
            ('jardines_de_infantes', 'Jardines de infantes'),
            ('jardines_maternales', 'Jardines maternales'),
            (
                'domiciliaria_hospitalaria',
                'Domiciliaria-hospitalaria',
            ),
            ('comunes_no_rurales', 'Urbanas'),
            ('comunes_rurales', 'Rurales'),
        ],
                'desglose_especiales': [
            (
                'especiales_jardines_maternales',
                'Jardines maternales',
            ),
            (
                'especiales_domiciliaria_hospitalaria',
                'Domiciliaria-hospitalaria',
            ),
            (
                'especiales_cursos_talleres',
                'Cursos/Talleres',
            ),
            (
                'especiales_integracion',
                'Integración',
            ),
            (
                'especiales_jardines_de_infantes',
                'Jardines de infantes',
            ),
            ('especiales_no_rurales', 'Urbanas'),
            ('especiales_rurales', 'Rurales'),
        ],
    },

    'primaria': {
        'titulo': 'Primaria',
        'valor_db': 'Primaria-Primaria',

        'columnas_principales': [
            ('total', 'Total primarias'),
            ('comunes', 'Comunes'),
            ('adultos', 'Adultos'),
            ('especiales', 'Especiales'),
        ],

        'desglose_comunes': [
            ('comunes_no_rurales', 'Urbanas'),
            ('comunes_rurales', 'Rurales'),
        ],
                'desglose_adultos': [
            ('adultos_epa', 'EPA'),
            ('adultos_epa_anexo', 'EPA Anexo'),
            ('adultos_epgs', 'EPGS'),
            ('adultos_epgcbii', 'EPGCBII'),
            ('adultos_no_rurales', 'Urbanas'),
            ('adultos_rurales', 'Rurales'),
        ],

        'desglose_especiales': [
            (
                'especiales_primaria_7_anios',
                'Primaria de 7 años',
            ),
            (
                'especiales_domiciliaria_hospitalaria',
                'Domiciliaria-hospitalaria',
            ),
            (
                'especiales_integracion',
                'Integración',
            ),
            ('especiales_no_rurales', 'Urbanas'),
            ('especiales_rurales', 'Rurales'),
        ],
    },

    'secundaria': {
    'titulo': 'Secundaria',
    'valor_db': 'Secundaria-Secundaria',

    'columnas_principales': [
        ('total', 'Total secundarias'),
        ('comunes', 'Comunes'),
        ('adultos', 'Adultos'),
    ],

    'desglose_comunes': [
        (
            'secundarias_comunes',
            'Secundarias comunes',
        ),
        ('tecnicas', 'Técnicas'),
        ('agropecuarias', 'Agropecuarias'),
        ('comunes_no_rurales', 'Urbanas'),
        ('comunes_rurales', 'Rurales'),
    ],

    'desglose_adultos': [
        ('adultos_ees', 'EES'),
        ('adultos_epgcbii', 'EPGCBII'),
        ('adultos_epgs', 'EPGS'),
        ('adultos_esja_anexo', 'ESJA Anexo'),
        ('adultos_esja', 'ESJA'),
        ('adultos_pe', 'PE'),
        ('adultos_sin_acronimo', 'Sin acrónimo'),
        ('adultos_no_rurales', 'Urbanas'),
        ('adultos_rurales', 'Rurales'),
    ],
},
}

# Esta configuración corresponde a la nueva pantalla: primero se selecciona
# una modalidad y luego se muestran los niveles que aplican a esa modalidad.
NIVELES_POR_MODALIDAD = {
    'inicial': {
        'titulo': 'Inicial',
        'modalidades': ('comunes', 'especiales'),
    },
    'primaria': {
        'titulo': 'Primaria',
        'modalidades': ('comunes', 'adultos', 'especiales'),
    },
    'secundaria': {
        'titulo': 'Secundaria',
        'modalidades': ('comunes', 'adultos'),
    },
    'artistica': {
        'titulo': 'Artística',
        'modalidades': ('comunes',),
    },
}

ORDEN_NIVELES_POR_MODALIDAD = tuple(NIVELES_POR_MODALIDAD)


# Configuración de la pantalla nueva. Se mantiene la configuración histórica
# de modalidades/niveles de arriba porque todavía la usan funciones antiguas
# del módulo; el resumen nuevo trabaja únicamente con estas estructuras.
GRUPOS_TIPO_OFERTA = (
    {
        'modalidad_id': 1,
        'clave': 'comun',
        'titulo': 'Común',
        'icono': 'fa-school',
    },
    {
        'modalidad_id': 2,
        'clave': 'especial',
        'titulo': 'Especial',
        'icono': 'fa-hands-holding-child',
    },
    {
        'modalidad_id': 3,
        'clave': 'adultos',
        'titulo': 'Adultos',
        'icono': 'fa-user-graduate',
    },
)


# Todos estos criterios se calculan desde una sola base ya filtrada por tipo
# de oferta. La oferta ya se elige en el filtro principal, por eso no se repite
# como desglose. Regional y Departamento conservan sus localidades como ramas.
CRITERIOS_DESGLOSE_OFERTAS = {
    'ambito': {
        'titulo': 'Ámbito',
        'tipo': 'arbol',
        'nodos_fijos': (
            ('R-Rural', 'Rural'),
            ('U-Urbano', 'Urbano'),
            ('SIN AMBITO', 'Sin ámbito informado'),
        ),
    },
    'sector': {
        'titulo': 'Sector',
        'tipo': 'arbol',
    },
    'acronimo': {
        'titulo': 'Acrónimo',
        'tipo': 'arbol',
    },
    'regional': {
        'titulo': 'Regional',
        'tipo': 'selector',
    },
    'departamento': {
        'titulo': 'Departamento',
        'tipo': 'selector',
    },
    'localidad': {
        'titulo': 'Localidad',
        'tipo': 'selector',
    },
}


SQL_TOTALES = """
    WITH base AS (
        SELECT
            BTRIM(vol.cue::text) AS cue,
            vol.c_modalidad1,

            COALESCE(
                BTRIM(vol.cp_of_ambito),
                ''
            ) AS ambito,

            COALESCE(
                BTRIM(vol.cp_acronimo),
                ''
            ) AS acronimo,

            COALESCE(
                BTRIM(vol.oferta),
                ''
            ) AS oferta

        FROM public.vp_oferta_local vol

        INNER JOIN public.vp_establecimientos ve
            ON ve.id_establecimiento =
               vol.id_establecimiento

        WHERE BTRIM(vol.estado_ofertalocal) = 'Activo'
          AND BTRIM(ve.estado) = 'Activo'
          AND BTRIM(vol.cp_of_nivel) = %s
          AND BTRIM(vol.cue::text) <> ''

          AND (
              BTRIM(vol.cp_of_nivel)
                  <> 'Secundaria-Secundaria'

              OR vol.c_modalidad1
                  IS DISTINCT FROM 2
          )
    ),

    artisticas_por_nivel AS (
        SELECT
            COALESCE(
                NULLIF(BTRIM(vol.cp_of_nivel), ''),
                'SIN NIVEL'
            ) AS nivel,

            COUNT(
                DISTINCT BTRIM(vol.cue::text)
            ) AS cantidad

        FROM public.vp_oferta_local vol

        INNER JOIN public.vp_establecimientos ve
            ON ve.id_establecimiento =
               vol.id_establecimiento

        WHERE BTRIM(vol.estado_ofertalocal) = 'Activo'
          AND BTRIM(ve.estado) = 'Activo'
          AND vol.c_modalidad1 = 1
          AND BTRIM(vol.cue::text) <> ''

          AND UPPER(
              COALESCE(
                  BTRIM(vol.cp_acronimo),
                  ''
              )
          ) = 'ARTISTICA-ARTISTICA'

        GROUP BY
            COALESCE(
                NULLIF(BTRIM(vol.cp_of_nivel), ''),
                'SIN NIVEL'
            )
    ),

    total_artisticas AS (
        SELECT
            COALESCE(
                SUM(cantidad),
                0
            ) AS cantidad

        FROM artisticas_por_nivel
    )

    SELECT
        (
            COUNT(DISTINCT cue) FILTER (
                WHERE ambito = 'U-Urbano'
            )
            +
            COUNT(DISTINCT cue) FILTER (
                WHERE ambito = 'R-Rural'
            )
        ) AS total,

        (
            COUNT(DISTINCT cue) FILTER (
                WHERE c_modalidad1 = 1
                  AND ambito = 'U-Urbano'
            )
            +
            COUNT(DISTINCT cue) FILTER (
                WHERE c_modalidad1 = 1
                  AND ambito = 'R-Rural'
            )
        ) AS comunes,

        (
            COUNT(DISTINCT cue) FILTER (
                WHERE c_modalidad1 = 2
                  AND ambito = 'U-Urbano'
            )
            +
            COUNT(DISTINCT cue) FILTER (
                WHERE c_modalidad1 = 2
                  AND ambito = 'R-Rural'
            )
        ) AS especiales,

        (
            COUNT(DISTINCT cue) FILTER (
                WHERE c_modalidad1 = 3
                  AND ambito = 'U-Urbano'
            )
            +
            COUNT(DISTINCT cue) FILTER (
                WHERE c_modalidad1 = 3
                  AND ambito = 'R-Rural'
            )
        ) AS adultos,

        COUNT(DISTINCT cue) FILTER (
            WHERE c_modalidad1 = 1
              AND oferta ILIKE
                  '%%Jardín de infantes%%'
        ) AS jardines_de_infantes,

        COUNT(DISTINCT cue) FILTER (
            WHERE c_modalidad1 = 1
              AND oferta ILIKE
                  '%%Jardín maternal%%'
        ) AS jardines_maternales,

        COUNT(DISTINCT cue) FILTER (
            WHERE c_modalidad1 = 1
              AND oferta ILIKE
                  '%%Domiciliaria-hospitalaria%%'
        ) AS domiciliaria_hospitalaria,

        COUNT(DISTINCT cue) FILTER (
            WHERE c_modalidad1 = 1
              AND UPPER(acronimo) = 'EET-EET'
        ) AS tecnicas,

        COUNT(DISTINCT cue) FILTER (
            WHERE c_modalidad1 = 1
              AND UPPER(acronimo) IN (
                  'EET-A-EET-A',
                  'EFA-EFA'
              )
        ) AS agropecuarias,

        (
    SELECT cantidad
    FROM total_artisticas
) AS artisticas,

        COUNT(DISTINCT cue) FILTER (
            WHERE c_modalidad1 = 1

              AND UPPER(acronimo) NOT IN (
                  'EET-EET',
                  'EET-A-EET-A',
                  'EFA-EFA'
              )

              AND UPPER(acronimo)
                  NOT LIKE 'ARTISTICA%%'

              AND oferta NOT ILIKE
                  '%%ARTÍST%%'

              AND oferta NOT ILIKE
                  '%%ARTIST%%'
        ) AS secundarias_comunes,

        COUNT(DISTINCT cue) FILTER (
            WHERE c_modalidad1 = 1
              AND ambito = 'U-Urbano'
        ) AS comunes_no_rurales,

        COUNT(DISTINCT cue) FILTER (
            WHERE c_modalidad1 = 1
              AND ambito = 'R-Rural'
        ) AS comunes_rurales,

        COUNT(DISTINCT cue) FILTER (
            WHERE c_modalidad1 = 3
              AND UPPER(acronimo) IN (
                  'EES',
                  'EES-EES'
              )
        ) AS adultos_ees,

        COUNT(DISTINCT cue) FILTER (
            WHERE c_modalidad1 = 3
              AND UPPER(acronimo) IN (
                  'EPGCBII',
                  'EPGCBII-EPGCBII'
              )
        ) AS adultos_epgcbii,

        COUNT(DISTINCT cue) FILTER (
            WHERE c_modalidad1 = 3
              AND UPPER(acronimo) IN (
                  'EPGS',
                  'EPGS-EPGS'
              )
        ) AS adultos_epgs,

        COUNT(DISTINCT cue) FILTER (
            WHERE c_modalidad1 = 3
              AND (
                  UPPER(acronimo) = 'ESJA-A'
                  OR UPPER(acronimo)
                      LIKE 'ESJA-A-%%'
                  OR UPPER(acronimo)
                      LIKE 'ESJA%%ANEX%%'
              )
        ) AS adultos_esja_anexo,

        COUNT(DISTINCT cue) FILTER (
            WHERE c_modalidad1 = 3
              AND UPPER(acronimo) IN (
                  'ESJA',
                  'ESJA-ESJA'
              )
        ) AS adultos_esja,

        COUNT(DISTINCT cue) FILTER (
            WHERE c_modalidad1 = 3
              AND UPPER(acronimo) IN (
                  'PE',
                  'PE-PE'
              )
        ) AS adultos_pe,

        COUNT(DISTINCT cue) FILTER (
            WHERE c_modalidad1 = 3
              AND acronimo = ''
        ) AS adultos_sin_acronimo,

        COUNT(DISTINCT cue) FILTER (
            WHERE c_modalidad1 = 3
              AND ambito = 'U-Urbano'
        ) AS adultos_no_rurales,

        COUNT(DISTINCT cue) FILTER (
            WHERE c_modalidad1 = 3
              AND ambito = 'R-Rural'
        ) AS adultos_rurales,

        (
            COUNT(DISTINCT cue) FILTER (
                WHERE c_modalidad1 = 3
                  AND UPPER(acronimo) IN (
                      'EPA',
                      'EPA-EPA'
                  )
                  AND ambito = 'U-Urbano'
            )
            +
            COUNT(DISTINCT cue) FILTER (
                WHERE c_modalidad1 = 3
                  AND UPPER(acronimo) IN (
                      'EPA',
                      'EPA-EPA'
                  )
                  AND ambito = 'R-Rural'
            )
        ) AS adultos_epa,

        (
            COUNT(DISTINCT cue) FILTER (
                WHERE c_modalidad1 = 3
                  AND UPPER(acronimo) IN (
                      'EPA ANEXO',
                      'EPA ANEXO-EPA ANEXO'
                  )
                  AND ambito = 'U-Urbano'
            )
            +
            COUNT(DISTINCT cue) FILTER (
                WHERE c_modalidad1 = 3
                  AND UPPER(acronimo) IN (
                      'EPA ANEXO',
                      'EPA ANEXO-EPA ANEXO'
                  )
                  AND ambito = 'R-Rural'
            )
        ) AS adultos_epa_anexo,

        (
            COUNT(DISTINCT cue) FILTER (
                WHERE c_modalidad1 = 2
                  AND oferta ILIKE
                      'Especial - Primaria de 7 años'
                  AND ambito = 'U-Urbano'
            )
            +
            COUNT(DISTINCT cue) FILTER (
                WHERE c_modalidad1 = 2
                  AND oferta ILIKE
                      'Especial - Primaria de 7 años'
                  AND ambito = 'R-Rural'
            )
        ) AS especiales_primaria_7_anios,

        (
            COUNT(DISTINCT cue) FILTER (
                WHERE c_modalidad1 = 2
                  AND oferta ILIKE
                      '%%Domiciliaria-hospitalaria%%'
                  AND ambito = 'U-Urbano'
            )
            +
            COUNT(DISTINCT cue) FILTER (
                WHERE c_modalidad1 = 2
                  AND oferta ILIKE
                      '%%Domiciliaria-hospitalaria%%'
                  AND ambito = 'R-Rural'
            )
        ) AS especiales_domiciliaria_hospitalaria,

        (
            COUNT(DISTINCT cue) FILTER (
                WHERE c_modalidad1 = 2
                  AND oferta ILIKE
                      'Especial - Integración'
                  AND ambito = 'U-Urbano'
            )
            +
            COUNT(DISTINCT cue) FILTER (
                WHERE c_modalidad1 = 2
                  AND oferta ILIKE
                      'Especial - Integración'
                  AND ambito = 'R-Rural'
            )
        ) AS especiales_integracion,

        (
            COUNT(DISTINCT cue) FILTER (
                WHERE c_modalidad1 = 2
                  AND oferta ILIKE
                      'Especial - Jardín maternal'
                  AND ambito = 'U-Urbano'
            )
            +
            COUNT(DISTINCT cue) FILTER (
                WHERE c_modalidad1 = 2
                  AND oferta ILIKE
                      'Especial - Jardín maternal'
                  AND ambito = 'R-Rural'
            )
        ) AS especiales_jardines_maternales,

        (
            COUNT(DISTINCT cue) FILTER (
                WHERE c_modalidad1 = 2
                  AND oferta ILIKE
                      'Especial - Cursos/Talleres%%'
                  AND ambito = 'U-Urbano'
            )
            +
            COUNT(DISTINCT cue) FILTER (
                WHERE c_modalidad1 = 2
                  AND oferta ILIKE
                      'Especial - Cursos/Talleres%%'
                  AND ambito = 'R-Rural'
            )
        ) AS especiales_cursos_talleres,

        (
            COUNT(DISTINCT cue) FILTER (
                WHERE c_modalidad1 = 2
                  AND oferta ILIKE
                      'Especial - Jardín de infantes'
                  AND ambito = 'U-Urbano'
            )
            +
            COUNT(DISTINCT cue) FILTER (
                WHERE c_modalidad1 = 2
                  AND oferta ILIKE
                      'Especial - Jardín de infantes'
                  AND ambito = 'R-Rural'
            )
        ) AS especiales_jardines_de_infantes,

        COUNT(DISTINCT cue) FILTER (
            WHERE c_modalidad1 = 2
              AND ambito = 'U-Urbano'
        ) AS especiales_no_rurales,

        COUNT(DISTINCT cue) FILTER (
            WHERE c_modalidad1 = 2
              AND ambito = 'R-Rural'
        ) AS especiales_rurales

    FROM base;
"""


# Esta consulta hace una sola lectura de las vistas del padrón y devuelve solo
# grupos con sus cantidades. El CTE base_por_nivel se reutiliza para las tarjetas,
# árboles, selectores y las localidades de cada departamento.
SQL_RESUMEN_TOTALES_COMPLETO = """
    WITH filas AS (
        SELECT
            BTRIM(vol.cue::text) AS cue,
            vol.c_modalidad1 AS modalidad_id,
            COALESCE(BTRIM(vol.cp_of_nivel), '') AS nivel_db,
            UPPER(COALESCE(BTRIM(vol.cp_of_nivel), '')) AS nivel_mayus,
            COALESCE(BTRIM(vol.cp_acronimo), '') AS acronimo,
            UPPER(COALESCE(BTRIM(vol.cp_acronimo), '')) AS acronimo_mayus,
            COALESCE(BTRIM(vol.oferta), '') AS oferta,
            UPPER(COALESCE(BTRIM(vol.oferta), '')) AS oferta_mayus,
            COALESCE(
                NULLIF(BTRIM(vol.cp_of_ambito), ''),
                'SIN AMBITO'
            ) AS ambito,
            COALESCE(BTRIM(vl.cp_esvat5), '') AS regional,
            COALESCE(BTRIM(vl.departamento_nombre), '') AS departamento,
            COALESCE(BTRIM(vl.localidad_nombre), '') AS localidad,
            COALESCE(BTRIM(vl.sector), '') AS sector
        FROM public.vp_oferta_local vol
        INNER JOIN public.vp_establecimientos ve
            ON ve.id_establecimiento = vol.id_establecimiento
        LEFT JOIN public.vp_localizaciones vl
            ON vl.id_localizacion = vol.id_localizacion
        WHERE BTRIM(vol.estado_ofertalocal) = 'Activo'
          AND BTRIM(ve.estado) = 'Activo'
          AND vol.c_modalidad1 IN (1, 2, 3)
          AND BTRIM(vol.cue::text) <> ''
    ),
    base AS (
        SELECT
            filas.*,
            COALESCE(NULLIF(nivel_db, ''), 'SIN NIVEL') AS nivel_mostrable,
            COALESCE(
                NULLIF(localidad, ''),
                'Sin localidad informada'
            ) AS localidad_departamento,
            CASE
                WHEN LENGTH(acronimo) % 2 = 1
                 AND SUBSTRING(
                        acronimo
                        FROM ((LENGTH(acronimo) + 1) / 2)
                        FOR 1
                     ) = '-'
                 AND LEFT(acronimo, ((LENGTH(acronimo) - 1) / 2))
                     = RIGHT(acronimo, ((LENGTH(acronimo) - 1) / 2))
                THEN LEFT(acronimo, ((LENGTH(acronimo) - 1) / 2))
                ELSE acronimo
            END AS sigla_agrupada
        FROM filas
    ),
    base_por_nivel AS (
        SELECT
            base.*,
            clasificacion.nivel,
            CASE
                WHEN clasificacion.nivel = 'artistica'
                THEN nivel_mostrable
                ELSE ''
            END AS clave_unidad
        FROM base
        CROSS JOIN LATERAL (
            SELECT 'inicial'::text AS nivel
            WHERE (
                nivel_mayus LIKE 'INICIAL%'
                OR (
                    modalidad_id = 2
                    AND (
                        oferta_mayus LIKE '%INICIAL%'
                        OR oferta_mayus LIKE '%JARDÍN%'
                        OR oferta_mayus LIKE '%JARDIN%'
                        OR oferta_mayus
                            LIKE '%DOMICILIARIA%HOSPITALARIA%'
                    )
                )
            )

            UNION ALL

            SELECT 'primaria'::text AS nivel
            WHERE (
                nivel_mayus LIKE 'PRIMARIA%'
                OR (
                    modalidad_id = 2
                    AND (
                        oferta_mayus LIKE '%PRIMARIA%'
                        OR oferta_mayus LIKE '%NIVEL PRIMARIO%'
                    )
                )
            )

            UNION ALL

            SELECT 'secundaria'::text AS nivel
            WHERE (
                nivel_mayus LIKE 'SECUNDARIA%'
                AND modalidad_id IS DISTINCT FROM 2
                AND acronimo_mayus <> 'ARTISTICA-ARTISTICA'
            )

            UNION ALL

            SELECT 'artistica'::text AS nivel
            WHERE (
                modalidad_id = 1
                AND acronimo_mayus = 'ARTISTICA-ARTISTICA'
            )
        ) AS clasificacion
    )

    SELECT
        modalidad_id,
        nivel,
        'total'::text AS tipo,
        ''::text AS criterio,
        ''::text AS valor,
        ''::text AS departamento,
        COUNT(DISTINCT (cue, clave_unidad)) AS total
    FROM base_por_nivel
    GROUP BY modalidad_id, nivel

    UNION ALL

    SELECT
        modalidad_id,
        nivel,
        'arbol'::text AS tipo,
        'ambito'::text AS criterio,
        ambito AS valor,
        ''::text AS departamento,
        COUNT(DISTINCT (cue, clave_unidad)) AS total
    FROM base_por_nivel
    GROUP BY modalidad_id, nivel, ambito

    UNION ALL

    SELECT
        modalidad_id,
        nivel,
        'arbol'::text AS tipo,
        'sigla'::text AS criterio,
        sigla_agrupada AS valor,
        ''::text AS departamento,
        COUNT(DISTINCT (cue, clave_unidad)) AS total
    FROM base_por_nivel
    WHERE sigla_agrupada <> ''
    GROUP BY modalidad_id, nivel, sigla_agrupada

    UNION ALL

    SELECT
        modalidad_id,
        nivel,
        'arbol'::text AS tipo,
        'nivel'::text AS criterio,
        nivel_mostrable AS valor,
        ''::text AS departamento,
        COUNT(DISTINCT (cue, clave_unidad)) AS total
    FROM base_por_nivel
    GROUP BY modalidad_id, nivel, nivel_mostrable

    UNION ALL

    SELECT
        modalidad_id,
        nivel,
        'arbol'::text AS tipo,
        'oferta'::text AS criterio,
        oferta AS valor,
        ''::text AS departamento,
        COUNT(DISTINCT (cue, clave_unidad)) AS total
    FROM base_por_nivel
    WHERE oferta <> ''
    GROUP BY modalidad_id, nivel, oferta

    UNION ALL

    SELECT
        modalidad_id,
        nivel,
        'arbol'::text AS tipo,
        'sector'::text AS criterio,
        sector AS valor,
        ''::text AS departamento,
        COUNT(DISTINCT (cue, clave_unidad)) AS total
    FROM base_por_nivel
    WHERE sector <> ''
    GROUP BY modalidad_id, nivel, sector

    UNION ALL

    SELECT
        modalidad_id,
        nivel,
        'selector'::text AS tipo,
        'regional'::text AS criterio,
        regional AS valor,
        ''::text AS departamento,
        COUNT(DISTINCT (cue, clave_unidad)) AS total
    FROM base_por_nivel
    WHERE regional <> ''
    GROUP BY modalidad_id, nivel, regional

    UNION ALL

    SELECT
        modalidad_id,
        nivel,
        'selector'::text AS tipo,
        'departamento'::text AS criterio,
        departamento AS valor,
        ''::text AS departamento,
        COUNT(DISTINCT (cue, clave_unidad)) AS total
    FROM base_por_nivel
    WHERE departamento <> ''
    GROUP BY modalidad_id, nivel, departamento

    UNION ALL

    SELECT
        modalidad_id,
        nivel,
        'selector'::text AS tipo,
        'localidad'::text AS criterio,
        localidad AS valor,
        ''::text AS departamento,
        COUNT(DISTINCT (cue, clave_unidad)) AS total
    FROM base_por_nivel
    WHERE localidad <> ''
    GROUP BY modalidad_id, nivel, localidad

    UNION ALL

    SELECT
        modalidad_id,
        nivel,
        'localidades_departamento'::text AS tipo,
        'departamento'::text AS criterio,
        localidad_departamento AS valor,
        departamento,
        COUNT(DISTINCT (cue, clave_unidad)) AS total
    FROM base_por_nivel
    WHERE departamento <> ''
    GROUP BY modalidad_id, nivel, departamento, localidad_departamento;
"""


def _crear_nivel_resumen(modalidad, nivel):
    """Crea la estructura vacía que el navegador reutiliza sin consultar SQL."""
    criterios = {}

    for clave, configuracion in CRITERIOS_DESGLOSE.items():
        if configuracion['tipo'] == 'arbol':
            criterios[clave] = {
                'tipo': 'arbol',
                'titulo': configuracion['titulo'],
                'nodos': [],
            }
        else:
            criterios[clave] = {
                'tipo': 'selector',
                'titulo': configuracion['titulo'],
                'opciones': [],
                '_localidades_por_departamento': {},
            }

    return {
        'titulo': NIVELES_POR_MODALIDAD[nivel]['titulo'],
        'aplica': nivel_aplica_a_modalidad(nivel, modalidad),
        'total': 0,
        'criterios': criterios,
    }


def construir_resumen_totales_completo():
    """Agrupa todos los datos necesarios para la pantalla en una sola consulta."""
    resumen = {
        'modalidades': {
            modalidad: {
                'titulo': MODALIDADES_PANTALLA[modalidad]['titulo'],
                'niveles': {
                    nivel: _crear_nivel_resumen(modalidad, nivel)
                    for nivel in ORDEN_NIVELES_POR_MODALIDAD
                },
            }
            for modalidad in MODALIDADES
        },
    }
    modalidades_por_id = {
        identificador: modalidad
        for modalidad, identificador in MODALIDADES.items()
    }

    with connections[PADRON_DB].cursor() as cursor:
        cursor.execute(SQL_RESUMEN_TOTALES_COMPLETO)
        nombres_columnas = [
            columna[0]
            for columna in cursor.description
        ]
        filas = [
            dict(zip(nombres_columnas, fila))
            for fila in cursor.fetchall()
        ]

    for fila in filas:
        modalidad = modalidades_por_id.get(fila['modalidad_id'])
        nivel = fila['nivel']

        if modalidad is None or nivel not in NIVELES_POR_MODALIDAD:
            continue

        nivel_datos = resumen['modalidades'][modalidad]['niveles'][nivel]
        tipo = fila['tipo']
        criterio = fila['criterio']
        valor = str(fila['valor'] or '')
        total = int(fila['total'] or 0)

        if tipo == 'total':
            nivel_datos['total'] = total
            continue

        if criterio not in nivel_datos['criterios']:
            continue

        criterio_datos = nivel_datos['criterios'][criterio]

        if tipo == 'arbol':
            criterio_datos['nodos'].append({
                'valor': valor,
                'titulo': formatear_valor_desglose(criterio, valor),
                'total': total,
            })
            continue

        if tipo == 'selector':
            criterio_datos['opciones'].append({
                'valor': valor,
                'titulo': valor,
                'total': total,
            })
            continue

        if tipo == 'localidades_departamento':
            departamento = str(fila['departamento'] or '')
            localidades = criterio_datos[
                '_localidades_por_departamento'
            ].setdefault(departamento, [])
            localidades.append({
                'titulo': valor,
                'total': total,
            })

    for modalidad_datos in resumen['modalidades'].values():
        for nivel_datos in modalidad_datos['niveles'].values():
            for criterio, criterio_datos in nivel_datos['criterios'].items():
                nodos_fijos = CRITERIOS_DESGLOSE[criterio].get('nodos_fijos')

                if nodos_fijos:
                    nodos_por_valor = {
                        nodo['valor']: nodo
                        for nodo in criterio_datos['nodos']
                    }
                    criterio_datos['nodos'] = [
                        {
                            'valor': valor,
                            'titulo': titulo,
                            'total': int(
                                nodos_por_valor.get(
                                    valor,
                                    {},
                                ).get('total', 0)
                            ),
                        }
                        for valor, titulo in nodos_fijos
                    ]
                    continue

                if criterio_datos['tipo'] == 'arbol':
                    criterio_datos['nodos'].sort(
                        key=lambda nodo: (
                            nodo['titulo'].casefold(),
                            nodo['valor'].casefold(),
                        )
                    )
                    continue

                criterio_datos['opciones'].sort(
                    key=lambda opcion: opcion['titulo'].casefold()
                )

                localidades_por_departamento = criterio_datos.pop(
                    '_localidades_por_departamento',
                    {},
                )
                for opcion in criterio_datos['opciones']:
                    localidades = localidades_por_departamento.get(
                        opcion['valor'],
                        [],
                    )
                    localidades.sort(
                        key=lambda nodo: nodo['titulo'].casefold()
                    )
                    opcion['localidades'] = localidades

    return resumen


def _clave_cache_resumen_totales(version_padron):
    """Genera una clave corta y segura a partir de la versión del padrón."""
    version = str(version_padron or 'sin-fecha')
    version_hash = sha256(version.encode('utf-8')).hexdigest()[:16]
    return f'{RESUMEN_TOTALES_CACHE_PREFIX}:{version_hash}'


def obtener_resumen_totales_cacheado(version_padron):
    """Devuelve el resumen ya calculado o lo genera solo en el primer acceso."""
    clave_cache = _clave_cache_resumen_totales(version_padron)
    resumen = cache.get(clave_cache)

    if resumen is not None:
        return resumen

    resumen = construir_resumen_totales_completo()
    cache.set(clave_cache, resumen, RESUMEN_TOTALES_CACHE_TIMEOUT)
    return resumen


# ---------------------------------------------------------------------------
# Resumen por Tipo de oferta (pantalla nueva)
# ---------------------------------------------------------------------------
#
# Esta sección no reemplaza las funciones históricas que siguen debajo. La
# pantalla nueva llama explícitamente a las funciones ``*_por_ofertas`` para
# poder conservar el resto de este módulo sin cambiar su comportamiento.

RESUMEN_TOTALES_OFERTAS_CACHE_PREFIX = (
    'padroninterno:totales-resumen-ofertas:v2'
)
TIPOS_OFERTA_CACHE_PREFIX = 'padroninterno:tipos-oferta:v1'
TIPOS_OFERTA_CACHE_TIMEOUT = RESUMEN_TOTALES_CACHE_TIMEOUT


def _clave_cache_tipos_oferta(version_padron):
    """Genera una clave del catálogo vinculada a la versión del padrón."""
    version = str(version_padron or 'sin-fecha')
    version_hash = sha256(version.encode('utf-8')).hexdigest()[:16]
    return f'{TIPOS_OFERTA_CACHE_PREFIX}:{version_hash}'


SQL_TIPOS_OFERTA = """
    SELECT
        vol.c_modalidad1 AS modalidad_id,
        BTRIM(vol.oferta) AS oferta
    FROM public.vp_oferta_local vol
    INNER JOIN public.vp_establecimientos ve
        ON ve.id_establecimiento = vol.id_establecimiento
    WHERE BTRIM(vol.estado_ofertalocal) = 'Activo'
      AND BTRIM(ve.estado) = 'Activo'
      AND vol.c_modalidad1 IN (1, 2, 3)
      AND BTRIM(vol.cue::text) <> ''
      AND BTRIM(vol.oferta) <> ''
    GROUP BY vol.c_modalidad1, BTRIM(vol.oferta)
    ORDER BY
        CASE vol.c_modalidad1
            WHEN 1 THEN 1
            WHEN 2 THEN 2
            WHEN 3 THEN 3
            ELSE 4
        END,
        LOWER(BTRIM(vol.oferta));
"""


# La consulta devuelve solamente valores agrupados. ``{filtro_ofertas}`` se
# construye con parámetros validados contra SQL_TIPOS_OFERTA; nunca se inserta
# texto proveniente directamente de la URL.
SQL_RESUMEN_TOTALES_POR_OFERTAS = """
    WITH filas AS (
        SELECT
            BTRIM(vol.cue::text) AS cue,
            COALESCE(BTRIM(vol.cue_anexo_oferta::text), '')
                AS cue_anexo_oferta,
            COALESCE(BTRIM(vol.oferta), '') AS oferta,
            UPPER(COALESCE(BTRIM(vol.cp_acronimo), '')) AS acronimo,
            COALESCE(
                NULLIF(BTRIM(vol.cp_of_ambito), ''),
                'SIN AMBITO'
            ) AS ambito,
            COALESCE(
                NULLIF(BTRIM(vl.sector), ''),
                'SIN SECTOR'
            ) AS sector,
            COALESCE(
                NULLIF(BTRIM(vl.cp_esvat5), ''),
                'Sin regional informada'
            ) AS regional,
            COALESCE(
                NULLIF(BTRIM(vl.departamento_nombre), ''),
                'Sin departamento informado'
            ) AS departamento,
            COALESCE(
                NULLIF(BTRIM(vl.localidad_nombre), ''),
                'Sin localidad informada'
            ) AS localidad
        FROM public.vp_oferta_local vol
        INNER JOIN public.vp_establecimientos ve
            ON ve.id_establecimiento = vol.id_establecimiento
        LEFT JOIN public.vp_localizaciones vl
            ON vl.id_localizacion = vol.id_localizacion
        WHERE BTRIM(vol.estado_ofertalocal) = 'Activo'
          AND BTRIM(ve.estado) = 'Activo'
          AND vol.c_modalidad1 IN (1, 2, 3)
          AND BTRIM(vol.cue::text) <> ''
          AND BTRIM(vol.oferta) <> ''
          {filtro_ofertas}
    ),
    acronimos_normalizados AS (
        SELECT
            filas.*,
            CASE
                WHEN MOD(LENGTH(acronimo), 2) = 1
                 AND SUBSTRING(
                        acronimo
                        FROM ((LENGTH(acronimo) + 1) / 2)
                        FOR 1
                     ) = '-'
                 AND LEFT(acronimo, ((LENGTH(acronimo) - 1) / 2))
                     = RIGHT(acronimo, ((LENGTH(acronimo) - 1) / 2))
                THEN LEFT(acronimo, ((LENGTH(acronimo) - 1) / 2))
                ELSE acronimo
            END AS acronimo_agrupado
        FROM filas
    ),
    base AS (
        SELECT
            acronimos_normalizados.*,
            COALESCE(
                NULLIF(acronimo_agrupado, ''),
                'SIN ACRONIMO'
            ) AS acronimo_mostrable
        FROM acronimos_normalizados
    )

    SELECT
        'total'::text AS tipo,
        'cue'::text AS criterio,
        ''::text AS valor,
        ''::text AS departamento,
        COUNT(DISTINCT cue) AS total
    FROM base

    UNION ALL

    SELECT
        'total'::text AS tipo,
        'anexo'::text AS criterio,
        ''::text AS valor,
        ''::text AS departamento,
        COUNT(DISTINCT NULLIF(cue_anexo_oferta, '')) AS total
    FROM base

    UNION ALL

    SELECT
        'arbol'::text AS tipo,
        'ambito'::text AS criterio,
        ambito AS valor,
        ''::text AS departamento,
        COUNT(DISTINCT cue) AS total
    FROM base
    GROUP BY ambito

    UNION ALL

    SELECT
        'arbol'::text AS tipo,
        'sector'::text AS criterio,
        sector AS valor,
        ''::text AS departamento,
        COUNT(DISTINCT cue) AS total
    FROM base
    GROUP BY sector

    UNION ALL

    SELECT
        'arbol'::text AS tipo,
        'acronimo'::text AS criterio,
        acronimo_mostrable AS valor,
        ''::text AS departamento,
        COUNT(DISTINCT cue) AS total
    FROM base
    GROUP BY acronimo_mostrable

    UNION ALL

    SELECT
        'selector'::text AS tipo,
        'regional'::text AS criterio,
        regional AS valor,
        ''::text AS departamento,
        COUNT(DISTINCT cue) AS total
    FROM base
    GROUP BY regional

    UNION ALL

    SELECT
        'selector'::text AS tipo,
        'departamento'::text AS criterio,
        departamento AS valor,
        ''::text AS departamento,
        COUNT(DISTINCT cue) AS total
    FROM base
    GROUP BY departamento

    UNION ALL

    SELECT
        'selector'::text AS tipo,
        'localidad'::text AS criterio,
        localidad AS valor,
        ''::text AS departamento,
        COUNT(DISTINCT cue) AS total
    FROM base
    GROUP BY localidad

    UNION ALL

    SELECT
        'localidades_departamento'::text AS tipo,
        'departamento'::text AS criterio,
        localidad AS valor,
        departamento,
        COUNT(DISTINCT cue) AS total
    FROM base
    GROUP BY departamento, localidad

    UNION ALL

    SELECT
        'localidades_regional'::text AS tipo,
        'regional'::text AS criterio,
        localidad AS valor,
        regional AS departamento,
        COUNT(DISTINCT cue) AS total
    FROM base
    GROUP BY regional, localidad;
"""


def _crear_grupos_tipo_oferta_vacios():
    """Crea los grupos del filtro sin compartir listas entre requests."""
    return [
        {
            **grupo,
            'opciones': [],
        }
        for grupo in GRUPOS_TIPO_OFERTA
    ]


def _token_tipo_oferta(modalidad_id, oferta):
    """Identificador estable de una combinación válida de oferta/modalidad."""
    return f'{modalidad_id}:{oferta}'


def obtener_grupos_tipo_oferta(version_padron=None):
    """Carga el catálogo del filtro, cacheado por versión del padrón."""
    grupos = _crear_grupos_tipo_oferta_vacios()
    grupos_por_id = {
        grupo['modalidad_id']: grupo
        for grupo in grupos
    }

    clave_cache = _clave_cache_tipos_oferta(version_padron)
    filas = cache.get(clave_cache)

    if filas is None:
        with connections[PADRON_DB].cursor() as cursor:
            cursor.execute(SQL_TIPOS_OFERTA)
            filas = tuple(cursor.fetchall())

        cache.set(
            clave_cache,
            filas,
            TIPOS_OFERTA_CACHE_TIMEOUT,
        )

    for modalidad_id, oferta in filas:
        modalidad_id = int(modalidad_id)
        oferta = str(oferta or '').strip()
        grupo = grupos_por_id.get(modalidad_id)

        if grupo is None or not oferta:
            continue

        grupo['opciones'].append({
            'token': _token_tipo_oferta(modalidad_id, oferta),
            'titulo': oferta,
            'modalidad_id': modalidad_id,
            'seleccionada': False,
        })

    return grupos


def obtener_ofertas_seleccionadas(request, grupos_ofertas):
    """Valida los tokens recibidos antes de usarlos en la consulta."""
    catalogo = {
        opcion['token']: opcion
        for grupo in grupos_ofertas
        for opcion in grupo['opciones']
    }
    seleccionadas = []
    tokens_vistos = set()

    for token in request.GET.getlist('oferta'):
        token = str(token or '').strip()

        if not token or token in tokens_vistos or token not in catalogo:
            continue

        opcion = catalogo[token]
        tokens_vistos.add(token)
        seleccionadas.append({
            'token': token,
            'modalidad_id': opcion['modalidad_id'],
            'oferta': opcion['titulo'],
        })

    return sorted(
        seleccionadas,
        key=lambda item: (
            item['modalidad_id'],
            item['oferta'].casefold(),
        ),
    )


def marcar_ofertas_seleccionadas(grupos_ofertas, seleccionadas):
    """Marca los checkboxes correspondientes a la selección actual."""
    tokens = {
        seleccionada['token']
        for seleccionada in seleccionadas
    }

    for grupo in grupos_ofertas:
        for opcion in grupo['opciones']:
            opcion['seleccionada'] = opcion['token'] in tokens


def _sql_filtro_tipo_oferta(seleccionadas):
    """Genera el fragmento parametrizado para una o varias ofertas."""
    if not seleccionadas:
        return '', []

    condiciones = []
    parametros = []

    for seleccionada in seleccionadas:
        condiciones.append(
            '('
            'vol.c_modalidad1 = %s '
            'AND BTRIM(vol.oferta) = %s'
            ')'
        )
        parametros.extend([
            seleccionada['modalidad_id'],
            seleccionada['oferta'],
        ])

    return 'AND (' + ' OR '.join(condiciones) + ')', parametros


def _formatear_valor_desglose_ofertas(criterio, valor):
    """Da nombres de presentación a los valores técnicos de esta pantalla."""
    valor = str(valor or '').strip()

    if criterio == 'ambito':
        return {
            'R-Rural': 'Rural',
            'U-Urbano': 'Urbano',
            'SIN AMBITO': 'Sin ámbito informado',
        }.get(valor, valor)

    if criterio == 'acronimo':
        return {
            'SIN ACRONIMO': 'Sin acrónimo informado',
            'ARTISTICA': 'Artística',
            'HOSPITALARIA': 'Hospitalaria',
        }.get(valor, valor)

    if criterio == 'sector' and valor == 'SIN SECTOR':
        return 'Sin sector informado'

    return valor


def _crear_resumen_totales_ofertas_vacio():
    """Crea la estructura que espera totales_escuelas.html."""
    criterios = {}

    for clave, configuracion in CRITERIOS_DESGLOSE_OFERTAS.items():
        if configuracion['tipo'] == 'arbol':
            criterios[clave] = {
                'tipo': 'arbol',
                'titulo': configuracion['titulo'],
                'nodos': [],
            }
            continue

        criterios[clave] = {
            'tipo': 'selector',
            'titulo': configuracion['titulo'],
            'opciones': [],
            '_localidades_por_departamento': {},
            '_localidades_por_regional': {},
        }

    return {
        'totales': {
            'cue': 0,
            'anexo': 0,
            'sectores': 0,
            'acronimos': 0,
        },
        'criterios': criterios,
    }


def construir_resumen_totales_por_ofertas(ofertas_seleccionadas):
    """Calcula tarjetas, árboles y selectores desde la base filtrada."""
    filtro_ofertas, parametros = _sql_filtro_tipo_oferta(
        ofertas_seleccionadas
    )
    sql = SQL_RESUMEN_TOTALES_POR_OFERTAS.replace(
        '{filtro_ofertas}',
        filtro_ofertas,
    )
    resumen = _crear_resumen_totales_ofertas_vacio()

    with connections[PADRON_DB].cursor() as cursor:
        cursor.execute(sql, parametros)
        nombres_columnas = [
            columna[0]
            for columna in cursor.description
        ]
        filas = [
            dict(zip(nombres_columnas, fila))
            for fila in cursor.fetchall()
        ]

    for fila in filas:
        tipo = str(fila['tipo'] or '')
        criterio = str(fila['criterio'] or '')
        valor = str(fila['valor'] or '')
        total = int(fila['total'] or 0)

        if tipo == 'total':
            if criterio in resumen['totales']:
                resumen['totales'][criterio] = total
            continue

        criterio_datos = resumen['criterios'].get(criterio)

        if criterio_datos is None:
            continue

        if tipo == 'arbol':
            criterio_datos['nodos'].append({
                'valor': valor,
                'titulo': _formatear_valor_desglose_ofertas(
                    criterio,
                    valor,
                ),
                'total': total,
            })
            continue

        if tipo == 'selector':
            criterio_datos['opciones'].append({
                'valor': valor,
                'titulo': valor,
                'total': total,
            })
            continue

        if tipo == 'localidades_departamento':
            departamento = str(fila['departamento'] or '')
            criterio_datos['_localidades_por_departamento'].setdefault(
                departamento,
                [],
            ).append({
                'titulo': valor,
                'total': total,
            })

        if tipo == 'localidades_regional':
            regional = str(fila['departamento'] or '')
            criterio_datos['_localidades_por_regional'].setdefault(
                regional,
                [],
            ).append({
                'titulo': valor,
                'total': total,
            })

    for criterio, criterio_datos in resumen['criterios'].items():
        if criterio_datos['tipo'] == 'arbol':
            nodos_fijos = CRITERIOS_DESGLOSE_OFERTAS[criterio].get(
                'nodos_fijos'
            )

            if nodos_fijos:
                nodos_por_valor = {
                    nodo['valor']: nodo
                    for nodo in criterio_datos['nodos']
                }
                valores_fijos = {
                    valor
                    for valor, _titulo in nodos_fijos
                }
                nodos_extra = [
                    nodo
                    for nodo in criterio_datos['nodos']
                    if nodo['valor'] not in valores_fijos
                ]
                nodos_extra.sort(
                    key=lambda nodo: nodo['titulo'].casefold()
                )
                criterio_datos['nodos'] = [
                    {
                        'valor': valor,
                        'titulo': titulo,
                        'total': int(
                            nodos_por_valor.get(valor, {}).get(
                                'total',
                                0,
                            )
                        ),
                    }
                    for valor, titulo in nodos_fijos
                ] + nodos_extra
            else:
                criterio_datos['nodos'].sort(
                    key=lambda nodo: nodo['titulo'].casefold()
                )
            continue

        criterio_datos['opciones'].sort(
            key=lambda opcion: opcion['titulo'].casefold()
        )
        localidades_por_departamento = criterio_datos.pop(
            '_localidades_por_departamento',
            {},
        )
        localidades_por_regional = criterio_datos.pop(
            '_localidades_por_regional',
            {},
        )

        if criterio == 'departamento':
            for opcion in criterio_datos['opciones']:
                localidades = localidades_por_departamento.get(
                    opcion['valor'],
                    [],
                )
                localidades.sort(
                    key=lambda nodo: nodo['titulo'].casefold()
                )
                opcion['localidades'] = localidades

        if criterio == 'regional':
            for opcion in criterio_datos['opciones']:
                localidades = localidades_por_regional.get(
                    opcion['valor'],
                    [],
                )
                localidades.sort(
                    key=lambda nodo: nodo['titulo'].casefold()
                )
                opcion['localidades'] = localidades

    resumen['totales']['sectores'] = len(
        resumen['criterios']['sector']['nodos']
    )
    resumen['totales']['acronimos'] = len(
        resumen['criterios']['acronimo']['nodos']
    )

    return resumen


def _clave_cache_resumen_por_ofertas(
    version_padron,
    ofertas_seleccionadas,
):
    """Incluye versión y selección para no mezclar resultados en caché."""
    version = str(version_padron or 'sin-fecha')
    seleccion = '|'.join(
        seleccionada['token']
        for seleccionada in ofertas_seleccionadas
    ) or 'todas'
    contenido = f'{version}|{seleccion}'
    version_hash = sha256(contenido.encode('utf-8')).hexdigest()[:20]
    return f'{RESUMEN_TOTALES_OFERTAS_CACHE_PREFIX}:{version_hash}'


def obtener_resumen_totales_por_ofertas_cacheado(
    version_padron,
    ofertas_seleccionadas,
):
    """Devuelve el resumen de la selección o lo calcula una única vez."""
    clave_cache = _clave_cache_resumen_por_ofertas(
        version_padron,
        ofertas_seleccionadas,
    )
    resumen = cache.get(clave_cache)

    if resumen is not None:
        return resumen

    resumen = construir_resumen_totales_por_ofertas(
        ofertas_seleccionadas
    )
    cache.set(clave_cache, resumen, RESUMEN_TOTALES_CACHE_TIMEOUT)
    return resumen


def descripcion_filtro_ofertas(ofertas_seleccionadas):
    """Devuelve una descripción corta de la selección mostrada."""
    if not ofertas_seleccionadas:
        return 'Todas las ofertas activas'

    nombres = [
        seleccionada['oferta']
        for seleccionada in ofertas_seleccionadas
    ]

    if len(nombres) <= 2:
        return ' · '.join(nombres)

    return ' · '.join(nombres[:2]) + f' y {len(nombres) - 2} más'


def _obtener_resumen_por_ofertas_para_request(request):
    """Resuelve catálogo, selección validada y resumen de un GET."""
    contexto_fecha = get_contexto_fecha_padron(request)
    grupos_ofertas = obtener_grupos_tipo_oferta(
        contexto_fecha['padron_fecha_version']
    )
    ofertas_seleccionadas = obtener_ofertas_seleccionadas(
        request,
        grupos_ofertas,
    )
    resumen = obtener_resumen_totales_por_ofertas_cacheado(
        contexto_fecha['padron_fecha_version'],
        ofertas_seleccionadas,
    )
    return (
        contexto_fecha,
        grupos_ofertas,
        ofertas_seleccionadas,
        resumen,
    )


def obtener_detalle_nivel(
    nivel,
    categoria,
    busqueda='',
    pagina=1,
):
    """
    Obtiene una fila por CUE para el nivel y la categoría
    seleccionados.

    Tanto el nivel como la categoría se validan previamente
    mediante listas cerradas.
    """
    valor_nivel = NIVELES[nivel]['valor_db']

    condicion_categoria = (
        CATEGORIAS_DETALLE[nivel][categoria]
    )

    cantidad_por_pagina = 10
    offset = (pagina - 1) * cantidad_por_pagina
    patron_busqueda = f'%{busqueda}%'

    sql = f"""
        WITH base_nivel AS (
            SELECT
                vol.id_establecimiento,

                BTRIM(
                    vol.cue::text
                ) AS cue,

                COALESCE(
                    NULLIF(BTRIM(ve.nombre), ''),
                    'Sin información'
                ) AS nombre,

                vol.c_modalidad1,

                COALESCE(
                    NULLIF(
                        BTRIM(vol.cp_of_ambito),
                        ''
                    ),
                    'Sin información'
                ) AS ambito,

                COALESCE(
                    NULLIF(
                        BTRIM(vol.cp_acronimo),
                        ''
                    ),
                    'Sin información'
                ) AS acronimo,

                COALESCE(
                    NULLIF(
                        BTRIM(vol.oferta),
                        ''
                    ),
                    'Sin información'
                ) AS oferta,

                CASE vol.c_modalidad1
                    WHEN 1 THEN 'Común'
                    WHEN 2 THEN 'Especial'
                    WHEN 3 THEN 'Adultos'
                    ELSE 'Sin información'
                END AS modalidad

            FROM public.vp_oferta_local vol

            INNER JOIN public.vp_establecimientos ve
                ON (
                    ve.id_establecimiento
                    = vol.id_establecimiento
                )

            WHERE BTRIM(vol.estado_ofertalocal) = 'Activo'
              AND BTRIM(ve.estado) = 'Activo'
              AND BTRIM(vol.cp_of_nivel) = %s
              AND BTRIM(vol.cue::text) <> ''

              AND (
                  BTRIM(vol.cp_of_nivel)
                      <> 'Secundaria-Secundaria'

                  OR vol.c_modalidad1
                      IS DISTINCT FROM 2
              )
        ),

        cues_categoria AS (
            SELECT DISTINCT cue

            FROM base_nivel

            WHERE {condicion_categoria}
        ),

        detalle_por_cue AS (
            SELECT
                base.cue,

                MIN(
                    base.id_establecimiento
                ) AS id_establecimiento,

                MIN(base.nombre) AS nombre,

                STRING_AGG(
                    DISTINCT base.modalidad,
                    ', ' ORDER BY base.modalidad
                ) AS modalidades,

                STRING_AGG(
                    DISTINCT base.ambito,
                    ', ' ORDER BY base.ambito
                ) AS ambitos,

                STRING_AGG(
                    DISTINCT base.acronimo,
                    ', ' ORDER BY base.acronimo
                ) AS acronimos,

                STRING_AGG(
                    DISTINCT base.oferta,
                    ', ' ORDER BY base.oferta
                ) AS ofertas

            FROM base_nivel base

            INNER JOIN cues_categoria categoria
                ON categoria.cue = base.cue

            GROUP BY base.cue
        )

        SELECT
            id_establecimiento,
            cue,
            nombre,
            modalidades,
            ambitos,
            acronimos,
            ofertas,
            COUNT(*) OVER () AS total_filtrado

        FROM detalle_por_cue

        WHERE (
            %s = ''
            OR cue ILIKE %s
            OR nombre ILIKE %s
        )

        ORDER BY cue

        LIMIT %s
        OFFSET %s;
    """

    parametros = [
        valor_nivel,
        busqueda,
        patron_busqueda,
        patron_busqueda,
        cantidad_por_pagina,
        offset,
    ]

    with connections[PADRON_DB].cursor() as cursor:
        cursor.execute(sql, parametros)

        nombres_columnas = [
            columna[0]
            for columna in cursor.description
        ]

        filas = [
            dict(zip(nombres_columnas, fila))
            for fila in cursor.fetchall()
        ]

    total = (
        int(filas[0]['total_filtrado'])
        if filas
        else 0
    )

    for fila in filas:
        fila.pop('total_filtrado', None)

    total_paginas = (
        (total + cantidad_por_pagina - 1)
        // cantidad_por_pagina
    )

    return {
        'resultados': filas,
        'total': total,
        'pagina': pagina,
        'total_paginas': total_paginas,
        'cantidad_por_pagina': cantidad_por_pagina,
    }

def obtener_totales(valor_nivel):
    """
    Ejecuta la consulta para un nivel y convierte
    la única fila obtenida en un diccionario.
    """
    with connections[PADRON_DB].cursor() as cursor:
        cursor.execute(
            SQL_TOTALES,
            [valor_nivel]
        )

        fila = cursor.fetchone()

        if fila is None:
            return {}

        nombres_columnas = [
            columna[0]
            for columna in cursor.description
        ]

        return dict(
            zip(nombres_columnas, fila)
        )


def nivel_aplica_a_modalidad(nivel, modalidad):
    """Indica si un nivel debe mostrarse para la modalidad elegida."""
    return modalidad in NIVELES_POR_MODALIDAD[nivel]['modalidades']


def condicion_nivel_por_modalidad_sql(nivel, alias='vol'):
    """Devuelve la condición fija que identifica cada tarjeta principal."""
    campo_nivel = (
        f"UPPER(COALESCE(BTRIM({alias}.cp_of_nivel), ''))"
    )
    campo_oferta = (
        f"UPPER(COALESCE(BTRIM({alias}.oferta), ''))"
    )
    campo_acronimo = (
        f"UPPER(COALESCE(BTRIM({alias}.cp_acronimo), ''))"
    )
    campo_modalidad = f'{alias}.c_modalidad1'

    if nivel == 'inicial':
        # En Especial no alcanza con Inicial-Inicial: también hay ofertas
        # activas de inicial identificadas por la oferta (Jardín, maternal,
        # domiciliaria-hospitalaria, etc.).
        return f"""
            (
                {campo_nivel} LIKE 'INICIAL%%'
                OR (
                    {campo_modalidad} = 2
                    AND (
                        {campo_oferta} LIKE '%%INICIAL%%'
                        OR {campo_oferta} LIKE '%%JARDÍN%%'
                        OR {campo_oferta} LIKE '%%JARDIN%%'
                        OR {campo_oferta} LIKE '%%MATERNAL%%'
                        OR {campo_oferta}
                            LIKE '%%DOMICILIARIA%%HOSPITALARIA%%'
                    )
                )
            )
        """

    if nivel == 'primaria':
        return f"""
            (
                {campo_nivel} LIKE 'PRIMARIA%%'
                OR (
                    {campo_modalidad} = 2
                    AND (
                        {campo_oferta} LIKE '%%PRIMARIA%%'
                        OR {campo_oferta} LIKE '%%NIVEL PRIMARIO%%'
                    )
                )
            )
        """

    if nivel == 'secundaria':
        return f"""
            (
                {campo_nivel} LIKE 'SECUNDARIA%%'
                AND {campo_modalidad} IS DISTINCT FROM 2
                AND {campo_acronimo} <> 'ARTISTICA-ARTISTICA'
            )
        """

    if nivel == 'artistica':
        return f"""
            (
                {campo_modalidad} = 1
                AND {campo_acronimo} = 'ARTISTICA-ARTISTICA'
            )
        """

    raise ValueError('Nivel no válido.')

def expresion_conteo_por_modalidad(nivel, alias='vol'):
    cue = f"BTRIM({alias}.cue::text)"

    if nivel == 'artistica':
        nivel_artistica = (
            f"COALESCE(NULLIF(BTRIM({alias}.cp_of_nivel), ''), 'SIN NIVEL')"
        )
        return f"({cue}, {nivel_artistica})"

    return cue

def expresion_conteo_por_modalidad(nivel, alias='vol'):
    cue = f"BTRIM({alias}.cue::text)"

    if nivel == 'artistica':
        nivel_artistica = (
            f"COALESCE(NULLIF(BTRIM({alias}.cp_of_nivel), ''), 'SIN NIVEL')"
        )
        return f"({cue}, {nivel_artistica})"

    return cue

def obtener_totales_por_modalidad(modalidad):
    """Obtiene Inicial, Primaria, Secundaria y Artística en una consulta."""
    condiciones = {
        nivel: condicion_nivel_por_modalidad_sql(nivel, 'base')
        for nivel in ORDEN_NIVELES_POR_MODALIDAD
    }

    unidad_artistica = expresion_conteo_por_modalidad(
        'artistica',
        'base',
    )

    sql = f"""
        WITH base AS (
            SELECT
                BTRIM(vol.cue::text) AS cue,
                vol.c_modalidad1,
                COALESCE(BTRIM(vol.cp_of_nivel), '') AS cp_of_nivel,
                COALESCE(BTRIM(vol.cp_acronimo), '') AS cp_acronimo,
                COALESCE(BTRIM(vol.oferta), '') AS oferta
            FROM public.vp_oferta_local vol
            INNER JOIN public.vp_establecimientos ve
                ON ve.id_establecimiento = vol.id_establecimiento
            WHERE BTRIM(vol.estado_ofertalocal) = 'Activo'
              AND BTRIM(ve.estado) = 'Activo'
              AND vol.c_modalidad1 = %s
              AND BTRIM(vol.cue::text) <> ''
        )
        SELECT
            COUNT(DISTINCT cue) FILTER (
                WHERE {condiciones['inicial']}
            ) AS inicial,
            COUNT(DISTINCT cue) FILTER (
                WHERE {condiciones['primaria']}
            ) AS primaria,
            COUNT(DISTINCT cue) FILTER (
                WHERE {condiciones['secundaria']}
            ) AS secundaria,
            COUNT(DISTINCT {unidad_artistica}) FILTER (
                WHERE {condiciones['artistica']}
            ) AS artistica
        FROM base;
    """

    with connections[PADRON_DB].cursor() as cursor:
        cursor.execute(sql, [MODALIDADES[modalidad]])
        fila = cursor.fetchone()
        nombres_columnas = [
            columna[0]
            for columna in cursor.description
        ]

    return {
        nombre: int(valor or 0)
        for nombre, valor in zip(nombres_columnas, fila or ())
    }


def obtener_total_nivel_por_modalidad(nivel, modalidad):
    """Cuenta CUE únicos de una tarjeta y su modalidad."""
    condicion_nivel = condicion_nivel_por_modalidad_sql(nivel)
    unidad_conteo = expresion_conteo_por_modalidad(nivel)

    sql = f"""
        SELECT COUNT(DISTINCT {unidad_conteo}) AS total
        FROM public.vp_oferta_local vol
        INNER JOIN public.vp_establecimientos ve
            ON ve.id_establecimiento = vol.id_establecimiento
        WHERE BTRIM(vol.estado_ofertalocal) = 'Activo'
          AND BTRIM(ve.estado) = 'Activo'
          AND vol.c_modalidad1 = %s
          AND BTRIM(vol.cue::text) <> ''
          AND {condicion_nivel};
    """

    with connections[PADRON_DB].cursor() as cursor:
        cursor.execute(sql, [MODALIDADES[modalidad]])
        return int(cursor.fetchone()[0] or 0)


def obtener_nodos_desglose_por_modalidad(nivel, modalidad, criterio):
    """Devuelve el árbol del nivel elegido con la misma condición del total."""
    configuracion = CRITERIOS_DESGLOSE[criterio]
    campo = configuracion['campo']
    campo_agrupado = campo_agrupado_desglose(criterio)
    condicion_nivel = condicion_nivel_por_modalidad_sql(nivel)
    unidad_conteo = expresion_conteo_por_modalidad(nivel)

    sql = f"""
        SELECT
            {campo_agrupado} AS valor,
            COUNT(DISTINCT {unidad_conteo}) AS total
        FROM public.vp_oferta_local vol
        INNER JOIN public.vp_establecimientos ve
            ON ve.id_establecimiento = vol.id_establecimiento
        LEFT JOIN public.vp_localizaciones vl
            ON vl.id_localizacion = vol.id_localizacion
        WHERE BTRIM(vol.estado_ofertalocal) = 'Activo'
          AND BTRIM(ve.estado) = 'Activo'
          AND vol.c_modalidad1 = %s
          AND BTRIM(vol.cue::text) <> ''
          AND {campo} <> ''
          AND {condicion_nivel}
        GROUP BY {campo_agrupado}
        ORDER BY LOWER({campo_agrupado});
    """

    with connections[PADRON_DB].cursor() as cursor:
        cursor.execute(sql, [MODALIDADES[modalidad]])
        filas = cursor.fetchall()

    totales_por_valor = {
        valor: int(total or 0)
        for valor, total in filas
    }
    nodos_fijos = configuracion.get('nodos_fijos')

    if nodos_fijos:
        return [
            {
                'valor': valor,
                'titulo': titulo,
                'total': totales_por_valor.get(valor, 0),
            }
            for valor, titulo in nodos_fijos
        ]

    return [
        {
            'valor': valor,
            'titulo': formatear_valor_desglose(criterio, valor),
            'total': total,
        }
        for valor, total in filas
    ]


def obtener_opciones_desglose_por_modalidad(nivel, modalidad, criterio):
    """Devuelve las opciones de los selectores geográficos."""
    campo = CRITERIOS_DESGLOSE[criterio]['campo']
    condicion_nivel = condicion_nivel_por_modalidad_sql(nivel)

    sql = f"""
        SELECT DISTINCT {campo} AS valor
        FROM public.vp_oferta_local vol
        INNER JOIN public.vp_establecimientos ve
            ON ve.id_establecimiento = vol.id_establecimiento
        LEFT JOIN public.vp_localizaciones vl
            ON vl.id_localizacion = vol.id_localizacion
        WHERE BTRIM(vol.estado_ofertalocal) = 'Activo'
          AND BTRIM(ve.estado) = 'Activo'
          AND vol.c_modalidad1 = %s
          AND BTRIM(vol.cue::text) <> ''
          AND {campo} <> ''
          AND {condicion_nivel}
        ORDER BY valor;
    """

    with connections[PADRON_DB].cursor() as cursor:
        cursor.execute(sql, [MODALIDADES[modalidad]])
        return [fila[0] for fila in cursor.fetchall()]


def obtener_total_desglose_por_modalidad(
    nivel,
    modalidad,
    criterio,
    valor,
):
    """Cuenta CUE únicos para una opción geográfica elegida."""
    campo = CRITERIOS_DESGLOSE[criterio]['campo']
    condicion_nivel = condicion_nivel_por_modalidad_sql(nivel)
    unidad_conteo = expresion_conteo_por_modalidad(nivel)

    sql = f"""
        SELECT COUNT(DISTINCT {unidad_conteo}) AS total
        FROM public.vp_oferta_local vol
        INNER JOIN public.vp_establecimientos ve
            ON ve.id_establecimiento = vol.id_establecimiento
        LEFT JOIN public.vp_localizaciones vl
            ON vl.id_localizacion = vol.id_localizacion
        WHERE BTRIM(vol.estado_ofertalocal) = 'Activo'
          AND BTRIM(ve.estado) = 'Activo'
          AND vol.c_modalidad1 = %s
          AND BTRIM(vol.cue::text) <> ''
          AND {campo} = %s
          AND {condicion_nivel};
    """

    with connections[PADRON_DB].cursor() as cursor:
        cursor.execute(
            sql,
            [MODALIDADES[modalidad], valor],
        )
        return int(cursor.fetchone()[0] or 0)

def obtener_localidades_departamento_por_modalidad(
    nivel,
    modalidad,
    departamento,
):
    """Devuelve las localidades de un departamento y sus CUE activos."""
    campo_departamento = CRITERIOS_DESGLOSE['departamento']['campo']
    campo_localidad = """
        COALESCE(
            NULLIF(BTRIM(vl.localidad_nombre), ''),
            'Sin localidad informada'
        )
    """
    condicion_nivel = condicion_nivel_por_modalidad_sql(nivel)
    unidad_conteo = expresion_conteo_por_modalidad(nivel)

    sql = f"""
        SELECT
            {campo_localidad} AS localidad,
            COUNT(DISTINCT {unidad_conteo}) AS total
        FROM public.vp_oferta_local vol
        INNER JOIN public.vp_establecimientos ve
            ON ve.id_establecimiento = vol.id_establecimiento
        LEFT JOIN public.vp_localizaciones vl
            ON vl.id_localizacion = vol.id_localizacion
        WHERE BTRIM(vol.estado_ofertalocal) = 'Activo'
          AND BTRIM(ve.estado) = 'Activo'
          AND vol.c_modalidad1 = %s
          AND BTRIM(vol.cue::text) <> ''
          AND {campo_departamento} = %s
          AND {condicion_nivel}
        GROUP BY {campo_localidad}
        ORDER BY LOWER({campo_localidad});
    """

    with connections[PADRON_DB].cursor() as cursor:
        cursor.execute(
            sql,
            [MODALIDADES[modalidad], departamento],
        )
        filas = cursor.fetchall()

    return [
        {
            'titulo': localidad,
            'total': int(total or 0),
        }
        for localidad, total in filas
    ]

def formatear_valor_desglose(criterio, valor):
    """Prepara los nombres de los nodos para que sean más legibles."""
    valor = str(valor or '').strip()

    if criterio == 'ambito':
        nombres_ambito = {
            'R-Rural': 'Rural',
            'U-Urbano': 'Urbano',
        }
        return nombres_ambito.get(valor, valor)

    return valor


def campo_agrupado_desglose(criterio):
    """Normaliza la sigla repetida antes de agrupar el árbol."""
    campo = CRITERIOS_DESGLOSE[criterio]['campo']

    if criterio != 'sigla':
        return campo

    # Ejemplos que quedan en una sola rama: EES-EES -> EES y
    # EET-A-EET-A -> EET-A. El valor original continúa usándose fuera del
    # agrupamiento, por lo que no se modifica ningún dato de la base.
    mitad = f"((LENGTH({campo}) - 1) / 2)"
    return f"""
        CASE
            WHEN LENGTH({campo}) %% 2 = 1
             AND SUBSTRING(
                    {campo}
                    FROM ((LENGTH({campo}) + 1) / 2)
                    FOR 1
                 ) = '-'
             AND LEFT({campo}, {mitad})
                 = RIGHT({campo}, {mitad})
            THEN LEFT({campo}, {mitad})
            ELSE {campo}
        END
    """


def obtener_total_modalidad(valor_nivel, modalidad):
    """Cuenta el total de la modalidad con la misma regla de la pantalla."""
    sql = """
        SELECT
            (
                COUNT(DISTINCT BTRIM(vol.cue::text)) FILTER (
                    WHERE COALESCE(BTRIM(vol.cp_of_ambito), '')
                        = 'U-Urbano'
                )
                + COUNT(DISTINCT BTRIM(vol.cue::text)) FILTER (
                    WHERE COALESCE(BTRIM(vol.cp_of_ambito), '')
                        = 'R-Rural'
                )
            ) AS total
        FROM public.vp_oferta_local vol
        INNER JOIN public.vp_establecimientos ve
            ON ve.id_establecimiento = vol.id_establecimiento
        WHERE BTRIM(vol.estado_ofertalocal) = 'Activo'
          AND BTRIM(ve.estado) = 'Activo'
          AND BTRIM(vol.cp_of_nivel) = %s
          AND vol.c_modalidad1 = %s
          AND BTRIM(vol.cue::text) <> ''
          AND (
              BTRIM(vol.cp_of_nivel) <> 'Secundaria-Secundaria'
              OR vol.c_modalidad1 IS DISTINCT FROM 2
          );
    """

    with connections[PADRON_DB].cursor() as cursor:
        cursor.execute(sql, [valor_nivel, MODALIDADES[modalidad]])
        return int(cursor.fetchone()[0] or 0)


def obtener_nodos_desglose(valor_nivel, modalidad, criterio):
    """Devuelve todos los nodos y sus cantidades para un árbol."""
    configuracion = CRITERIOS_DESGLOSE[criterio]
    campo = configuracion['campo']
    campo_agrupado = campo_agrupado_desglose(criterio)

    sql = f"""
        SELECT
            {campo_agrupado} AS valor,
            COUNT(DISTINCT BTRIM(vol.cue::text)) AS total
        FROM public.vp_oferta_local vol
        INNER JOIN public.vp_establecimientos ve
            ON ve.id_establecimiento = vol.id_establecimiento
        LEFT JOIN public.vp_localizaciones vl
            ON vl.id_localizacion = vol.id_localizacion
        WHERE BTRIM(vol.estado_ofertalocal) = 'Activo'
          AND BTRIM(ve.estado) = 'Activo'
          AND BTRIM(vol.cp_of_nivel) = %s
          AND vol.c_modalidad1 = %s
          AND BTRIM(vol.cue::text) <> ''
          AND {campo} <> ''
          AND (
              BTRIM(vol.cp_of_nivel) <> 'Secundaria-Secundaria'
              OR vol.c_modalidad1 IS DISTINCT FROM 2
          )
        GROUP BY {campo_agrupado}
        ORDER BY LOWER({campo_agrupado});
    """

    with connections[PADRON_DB].cursor() as cursor:
        cursor.execute(sql, [valor_nivel, MODALIDADES[modalidad]])
        filas = cursor.fetchall()

    totales_por_valor = {
        valor: int(total or 0)
        for valor, total in filas
    }
    nodos_fijos = configuracion.get('nodos_fijos')

    if nodos_fijos:
        return [
            {
                'valor': valor,
                'titulo': titulo,
                'total': totales_por_valor.get(valor, 0),
            }
            for valor, titulo in nodos_fijos
        ]

    return [
        {
            'valor': valor,
            'titulo': formatear_valor_desglose(criterio, valor),
            'total': total,
        }
        for valor, total in filas
    ]


def obtener_opciones_desglose(valor_nivel, modalidad, criterio):
    """Devuelve valores disponibles de un selector dentro de una modalidad."""
    campo = CRITERIOS_DESGLOSE[criterio]['campo']

    sql = f"""
        SELECT DISTINCT {campo} AS valor
        FROM public.vp_oferta_local vol
        INNER JOIN public.vp_establecimientos ve
            ON ve.id_establecimiento = vol.id_establecimiento
        LEFT JOIN public.vp_localizaciones vl
            ON vl.id_localizacion = vol.id_localizacion
        WHERE BTRIM(vol.estado_ofertalocal) = 'Activo'
          AND BTRIM(ve.estado) = 'Activo'
          AND BTRIM(vol.cp_of_nivel) = %s
          AND vol.c_modalidad1 = %s
          AND BTRIM(vol.cue::text) <> ''
          AND {campo} <> ''
          AND (
              BTRIM(vol.cp_of_nivel) <> 'Secundaria-Secundaria'
              OR vol.c_modalidad1 IS DISTINCT FROM 2
          )
        ORDER BY valor;
    """

    with connections[PADRON_DB].cursor() as cursor:
        cursor.execute(sql, [valor_nivel, MODALIDADES[modalidad]])
        return [fila[0] for fila in cursor.fetchall()]


def obtener_total_desglose(valor_nivel, modalidad, criterio, valor):
    """Cuenta CUE distintos para una única opción elegida por el usuario."""
    campo = CRITERIOS_DESGLOSE[criterio]['campo']

    sql = f"""
        SELECT COUNT(DISTINCT BTRIM(vol.cue::text))
        FROM public.vp_oferta_local vol
        INNER JOIN public.vp_establecimientos ve
            ON ve.id_establecimiento = vol.id_establecimiento
        LEFT JOIN public.vp_localizaciones vl
            ON vl.id_localizacion = vol.id_localizacion
        WHERE BTRIM(vol.estado_ofertalocal) = 'Activo'
          AND BTRIM(ve.estado) = 'Activo'
          AND BTRIM(vol.cp_of_nivel) = %s
          AND vol.c_modalidad1 = %s
          AND BTRIM(vol.cue::text) <> ''
          AND {campo} = %s
          AND (
              BTRIM(vol.cp_of_nivel) <> 'Secundaria-Secundaria'
              OR vol.c_modalidad1 IS DISTINCT FROM 2
          );
    """

    with connections[PADRON_DB].cursor() as cursor:
        cursor.execute(
            sql,
            [valor_nivel, MODALIDADES[modalidad], valor],
        )
        return int(cursor.fetchone()[0] or 0)


@padron_interno_admin_o_gestor_required
@require_GET
def detalle_totales_json(request):
    """Devuelve un desglose construido con el filtro de ofertas actual."""
    criterio = request.GET.get('criterio', '').strip().lower()
    valor = request.GET.get('valor', '').strip()
    detalle = request.GET.get('detalle', '').strip().lower()

    if criterio not in CRITERIOS_DESGLOSE_OFERTAS:
        return JsonResponse({'error': 'Criterio no válido.'}, status=400)

    try:
        (
            _contexto_fecha,
            _grupos_ofertas,
            _ofertas_seleccionadas,
            resumen,
        ) = _obtener_resumen_por_ofertas_para_request(request)
    except DatabaseError:
        logger.exception('Error al consultar el resumen de totales por oferta')
        return JsonResponse(
            {'error': 'No fue posible consultar el desglose.'},
            status=500,
        )

    criterio_datos = resumen['criterios'][criterio]

    if detalle:
        if (
            detalle != 'localidades'
            or criterio not in {'regional', 'departamento'}
            or not valor
        ):
            return JsonResponse(
                {'error': 'Detalle de localidades no válido.'},
                status=400,
            )

        opcion_geografica = next(
            (
                opcion
                for opcion in criterio_datos['opciones']
                if opcion['valor'] == valor
            ),
            None,
        )
        return JsonResponse({
            'tipo': 'localidades',
            'titulo': 'Localidades de ' + valor,
            'nodos': (
                opcion_geografica.get('localidades', [])
                if opcion_geografica
                else []
            ),
        })

    if criterio_datos['tipo'] == 'arbol':
        return JsonResponse({
            'tipo': 'arbol',
            'titulo': criterio_datos['titulo'],
            'total': resumen['totales']['cue'],
            'nodos': criterio_datos['nodos'],
        })

    opcion_seleccionada = next(
        (
            opcion
            for opcion in criterio_datos['opciones']
            if opcion['valor'] == valor
        ),
        None,
    )

    return JsonResponse({
        'tipo': 'selector',
        'titulo': criterio_datos['titulo'],
        'opciones': [] if valor else criterio_datos['opciones'],
        'valor_seleccionado': valor,
        'total': (
            opcion_seleccionada['total']
            if opcion_seleccionada
            else None
        ),
    })

def construir_columnas(definiciones, totales):
    """Combina los títulos configurados con sus cantidades."""
    return [
        {
            'clave': clave,
            'titulo': titulo,
            'valor': totales.get(clave, 0),
        }
        for clave, titulo in definiciones
    ]


def construir_columnas_niveles(modalidad, totales):
    """Prepara las cuatro tarjetas de la pantalla por modalidad."""
    columnas = []

    for clave in ORDEN_NIVELES_POR_MODALIDAD:
        nivel = NIVELES_POR_MODALIDAD[clave]
        aplica = nivel_aplica_a_modalidad(clave, modalidad)
        columnas.append({
            'clave': clave,
            'titulo': nivel['titulo'],
            'valor': int(totales.get(clave, 0)) if aplica else None,
            'aplica': aplica,
        })

    return columnas


@padron_interno_admin_o_gestor_required
@require_GET
def totales_escuelas_view(request):
    """Muestra los totales de establecimientos activos por tipo de oferta."""
    mensaje_error = None
    contexto_fecha = get_contexto_fecha_padron(request)
    grupos_ofertas = _crear_grupos_tipo_oferta_vacios()
    ofertas_seleccionadas = []
    resumen_totales = _crear_resumen_totales_ofertas_vacio()

    try:
        grupos_ofertas = obtener_grupos_tipo_oferta(
            contexto_fecha['padron_fecha_version']
        )
        ofertas_seleccionadas = obtener_ofertas_seleccionadas(
            request,
            grupos_ofertas,
        )
        marcar_ofertas_seleccionadas(
            grupos_ofertas,
            ofertas_seleccionadas,
        )
        resumen_totales = obtener_resumen_totales_por_ofertas_cacheado(
            contexto_fecha['padron_fecha_version'],
            ofertas_seleccionadas,
        )
    except DatabaseError:
        logger.exception('Error al construir el resumen de totales')
        mensaje_error = (
            'No fue posible consultar los totales. '
            'Intentá nuevamente más tarde.'
        )

    context = {
        'grupos_ofertas': grupos_ofertas,
        'ofertas_seleccionadas': ofertas_seleccionadas,
        'hay_filtro_ofertas': bool(ofertas_seleccionadas),
        'cantidad_ofertas_seleccionadas': len(ofertas_seleccionadas),
        'descripcion_filtro_ofertas': descripcion_filtro_ofertas(
            ofertas_seleccionadas
        ),
        'mensaje_error': mensaje_error,
        'sin_datos': (
            mensaje_error is None
            and resumen_totales['totales']['cue'] == 0
        ),
        'resumen_totales': resumen_totales,
    }

    context.update(contexto_fecha)

    return render(
        request,
        'padroninterno/totales_escuelas.html',
        context,
    )