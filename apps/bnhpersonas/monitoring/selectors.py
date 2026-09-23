from collections import defaultdict
from datetime import date, timedelta

from django.conf import settings
from django.db import connection
from django.db.models import Count, Max, Q, Sum
from django.utils import timezone

from apps.consultasge.models_padron import CapaUnicaOfertas

from ..models import EventoAuditoria, RegistroActividades
from .access import allowed_cueanexos, scoped_offers


VALIDACION_BORRADOR = "BORRADOR"
VALIDACION_VALIDADO = "VALIDADO"
VALIDACION_OBSERVADO = "OBSERVADO"


# ============================================================
# UTILIDADES
# ============================================================

def normalize_cue(value):
    value = str(value or "").strip()

    return (
        value.zfill(9)
        if value.isdigit()
        else value
    )


def _numero(value, default=0):

    if value is None:
        return default

    return value


def _porcentaje(
    numerador,
    denominador,
):

    numerador = _numero(
        numerador,
        0,
    )

    denominador = _numero(
        denominador,
        0,
    )

    if not denominador:
        return None

    return round(
        float(numerador)
        /
        float(denominador)
        * 100,
        2,
    )


def _estado_cobertura(
    bnh,
    ra,
):

    bnh = _numero(
        bnh,
        0,
    )

    ra = _numero(
        ra,
        0,
    )

    if ra == 0 and bnh == 0:
        return "SIN UNIVERSO"

    if ra == 0 and bnh > 0:
        return "SIN BASE RA"

    if bnh == 0:
        return "SIN CARGA"

    if bnh < ra:
        return "INCOMPLETO"

    if bnh == ra:
        return "COMPLETO"

    return "EXCEDE RA"


# ============================================================
# CATÁLOGO DE INSTITUCIONES
# ============================================================

def institution_catalog(user):

    """
    Consolida CapaUnicaOfertas por CUEANEXO.

    Un establecimiento puede tener más de una oferta.
    """

    rows = (
        scoped_offers(user)
        .order_by(
            "cueanexo",
            "oferta",
        )
        .values(
            "cueanexo",
            "nom_est",
            "region_loc",
            "oferta",
            "acronimo",
        )
    )

    institutions = {}

    for row in rows.iterator(
        chunk_size=2000
    ):

        cue = normalize_cue(
            row["cueanexo"]
        )

        if not cue:
            continue

        item = institutions.setdefault(
            cue,
            {
                "cueanexo": cue,
                "nom_est":
                    row.get("nom_est")
                    or "",
                "region":
                    row.get("region_loc")
                    or "",
                "ofertas":
                    set(),
                "acronimos":
                    set(),
            },
        )

        if (
            not item["nom_est"]
            and row.get("nom_est")
        ):
            item["nom_est"] = (
                row["nom_est"]
            )

        if (
            not item["region"]
            and row.get("region_loc")
        ):
            item["region"] = (
                row["region_loc"]
            )

        if row.get("oferta"):

            item["ofertas"].add(
                str(
                    row["oferta"]
                )
            )

        if row.get("acronimo"):

            item["acronimos"].add(
                str(
                    row["acronimo"]
                )
            )

    result = []

    for item in institutions.values():

        item["ofertas"] = sorted(
            item["ofertas"]
        )

        item["acronimos"] = sorted(
            item["acronimos"]
        )

        result.append(
            item
        )

    return sorted(
        result,
        key=lambda value: (
            value["region"],
            value["nom_est"],
            value["cueanexo"],
        ),
    )


# ============================================================
# ACTIVIDADES DEL ÁMBITO AUTORIZADO
# ============================================================

def scoped_activities(
    user,
    cueanexos=None,
):

    cues = (
        tuple(cueanexos)
        if cueanexos is not None
        else allowed_cueanexos(user)
    )

    if not cues:
        return (
            RegistroActividades.objects.none()
        )

    return (
        RegistroActividades.objects
        .filter(
            cueanexo__in=cues,
            eliminado=False,
            persona__archivada=False,
        )
    )


# ============================================================
# MÉTRICAS BNH OPERATIVAS
# ============================================================

def activity_metrics_by_cue(
    user,
    cueanexos,
):

    cues = tuple(
        cueanexos
    )

    if not cues:
        return {}

    rows = (
        scoped_activities(
            user,
            cues,
        )
        .values(
            "cueanexo"
        )
        .annotate(

            personas=Count(
                "persona_id",
                distinct=True,
            ),

            cargos=Count(
                "id"
            ),

            docentes=Count(
                "id",
                filter=Q(
                    tipo_personal_id=1
                ),
            ),

            no_docentes=Count(
                "id",
                filter=Q(
                    tipo_personal_id=2
                ),
            ),

            borradores=Count(
                "id",
                filter=Q(
                    validacion=
                    VALIDACION_BORRADOR
                ),
            ),

            validados=Count(
                "id",
                filter=Q(
                    validacion=
                    VALIDACION_VALIDADO
                ),
            ),

            observados=Count(
                "id",
                filter=Q(
                    validacion=
                    VALIDACION_OBSERVADO
                ),
            ),

            ultima_actualizacion=Max(
                "fecha_modificacion"
            ),
        )
    )

    return {

        normalize_cue(
            row["cueanexo"]
        ): row

        for row in rows
    }


# ============================================================
# COBERTURA RA vs BNH POR CUEANEXO
# ============================================================

def cobertura_por_cue(
    cueanexos,
):

    """
    Devuelve la comparación RA 2026 vs BNH vivo
    para los CUEANEXO recibidos.

    La seguridad no se resuelve acá:
    cueanexos debe provenir del ámbito ya autorizado.
    """

    cues = sorted({
        normalize_cue(
            value
        )
        for value
        in cueanexos
        if value
    })

    if not cues:
        return {}

    sql = """

        SELECT

            cueanexo,

            total_cargos_ra,
            total_cargos_bnh,
            diferencia_cargos,
            porcentaje_cargos,
            estado_cargos,

            total_horas_ra,
            total_horas_bnh,
            diferencia_horas,
            porcentaje_horas,
            estado_horas

        FROM
            bnh.v_cobertura_bnh_ra_2026

        WHERE
            cueanexo = ANY(
                %s::text[]
            )

    """

    with connection.cursor() as cursor:

        cursor.execute(
            sql,
            [cues],
        )

        columns = [
            column[0]
            for column
            in cursor.description
        ]

        result = {}

        for values in cursor.fetchall():

            row = dict(
                zip(
                    columns,
                    values,
                )
            )

            cue = normalize_cue(
                row["cueanexo"]
            )

            if (
                row[
                    "porcentaje_cargos"
                ]
                is not None
            ):
                row[
                    "porcentaje_cargos"
                ] = float(
                    row[
                        "porcentaje_cargos"
                    ]
                )

            if (
                row[
                    "porcentaje_horas"
                ]
                is not None
            ):
                row[
                    "porcentaje_horas"
                ] = float(
                    row[
                        "porcentaje_horas"
                    ]
                )

            # El valor real puede superar 100.
            # La barra visual no.

            row[
                "progreso_cargos"
            ] = min(
                max(
                    row[
                        "porcentaje_cargos"
                    ]
                    or 0,
                    0,
                ),
                100,
            )

            row[
                "progreso_horas"
            ] = min(
                max(
                    row[
                        "porcentaje_horas"
                    ]
                    or 0,
                    0,
                ),
                100,
            )

            result[
                cue
            ] = row

    return result



# ============================================================
# COMPARATIVA REUNIDAS POF vs BNH POR CEIC
# ============================================================

def pof_bnh_breakdown(
    cueanexo,
    anio_objetivo=2026,
):
    """
    Compara, por CEIC, cargos y horas cátedra de Reunidas POF
    contra BNH para un CUEANEXO.

    Reglas POF:
    - Usa datos AFECTADOS.
    - Prioriza el año objetivo (2026).
    - Si no existe, usa el último año disponible para el CUEANEXO.

    Reglas BNH:
    - Actividades no eliminadas.
    - Personas no archivadas.
    - Estado ACTIVO.
    - Tipo de designación 1 = CARGO.
    - Tipo de designación 3 = HORAS CÁTEDRAS.
    - Vigentes en el año objetivo.

    La seguridad del CUEANEXO se resuelve en la vista mediante
    assert_cue_access().
    """

    from apps.reunidas_pof.models import CargoPof

    cue = normalize_cue(cueanexo)

    if not cue:
        return {
            "cueanexo": "",
            "anio_objetivo": int(anio_objetivo),
            "anio_pof": None,
            "anio_bnh": int(anio_objetivo),
            "pof_disponible": False,
            "usa_anio_anterior": False,
            "mensaje_pof": "No se pudo determinar el CUEANEXO.",
            "resumen": {
                "cargos_pof": 0,
                "cargos_bnh": 0,
                "diferencia_cargos": 0,
                "horas_pof": 0,
                "horas_bnh": 0,
                "diferencia_horas": 0,
            },
            "cargos": [],
            "horas": [],
        }

    anio_objetivo = int(anio_objetivo)

    # --------------------------------------------------------
    # Base POF disponible para la institución
    # --------------------------------------------------------

    pof_base = CargoPof.objects.filter(
        localizacion__cueanexo=cue,
        localizacion__reunida__isnull=False,
        estado_pof=CargoPof.EstadoPof.AFECTADO,
    )

    # Primero se busca el año objetivo o el último anterior.
    anio_pof = (
        pof_base
        .filter(
            localizacion__reunida__anio__lte=anio_objetivo,
        )
        .order_by(
            "-localizacion__reunida__anio",
        )
        .values_list(
            "localizacion__reunida__anio",
            flat=True,
        )
        .first()
    )

    # Si no hubiera ningún año <= al objetivo, se usa el último
    # existente para el CUEANEXO, cualquiera sea su año.
    if anio_pof is None:
        anio_pof = (
            pof_base
            .order_by(
                "-localizacion__reunida__anio",
            )
            .values_list(
                "localizacion__reunida__anio",
                flat=True,
            )
            .first()
        )

    pof_disponible = anio_pof is not None
    usa_anio_anterior = (
        pof_disponible
        and int(anio_pof) != anio_objetivo
    )

    if not pof_disponible:
        mensaje_pof = (
            f"No se encontraron datos POF disponibles para esta unidad de servicio. "
            f"POF {anio_objetivo} estará disponible para comparar cuando el "
            f"Departamento POF actualice los datos."
        )
    elif usa_anio_anterior:
        mensaje_pof = (
            f"POF {anio_objetivo} aún no se encuentra disponible para esta unidad "
            f"de servicio. La comparación se realiza con la última POF disponible, "
            f"correspondiente al año {int(anio_pof)}. POF {anio_objetivo} estará "
            f"disponible para comparar cuando el Departamento POF actualice los datos."
        )
    else:
        mensaje_pof = None

    # --------------------------------------------------------
    # POF por CEIC
    # --------------------------------------------------------

    pof = {}

    if pof_disponible:
        pof_rows = (
            pof_base
            .filter(
                localizacion__reunida__anio=int(anio_pof),
            )
            .values(
                "ceic",
            )
            .annotate(
                descripcion=Max("cargo"),
                cargos_pof=Sum(
                    "cantidad",
                    filter=Q(
                        unidad_cantidad=CargoPof.UnidadCantidad.CARGO,
                    ),
                ),
                horas_pof=Sum(
                    "cantidad",
                    filter=Q(
                        unidad_cantidad=CargoPof.UnidadCantidad.HORA_CATEDRA,
                    ),
                ),
            )
            .order_by(
                "ceic",
            )
        )

        for row in pof_rows:
            ceic = row.get("ceic")

            if ceic is None:
                continue

            pof[int(ceic)] = {
                "descripcion": row.get("descripcion") or "",
                "cargos": float(row.get("cargos_pof") or 0),
                "horas": float(row.get("horas_pof") or 0),
            }

    # --------------------------------------------------------
    # BNH por CEIC
    # --------------------------------------------------------

    fecha_desde = date(
        anio_objetivo,
        1,
        1,
    )

    fecha_hasta = date(
        anio_objetivo,
        12,
        31,
    )

    bnh_rows = (
        RegistroActividades.objects
        .filter(
            cueanexo=cue,
            eliminado=False,
            persona__archivada=False,
            estado="ACTIVO",
            t_designacion_id__in=(1, 3),
            f_desde__lte=fecha_hasta,
        )
        .filter(
            Q(f_hasta__isnull=True)
            |
            Q(f_hasta__gte=fecha_desde)
        )
        .values(
            "ceic_id",
            "ceic__descripcion",
        )
        .annotate(
            cargos_bnh=Count(
                "id",
                filter=Q(
                    t_designacion_id=1,
                ),
            ),
            horas_bnh=Sum(
                "carga_horaria",
                filter=Q(
                    t_designacion_id=3,
                ),
            ),
        )
        .order_by(
            "ceic_id",
        )
    )

    bnh = {}

    for row in bnh_rows:
        ceic = row.get("ceic_id")

        if ceic is None:
            continue

        bnh[int(ceic)] = {
            "descripcion": row.get("ceic__descripcion") or "",
            "cargos": float(row.get("cargos_bnh") or 0),
            "horas": float(row.get("horas_bnh") or 0),
        }

    # --------------------------------------------------------
    # Estados y orden
    # --------------------------------------------------------

    def _estado(valor_pof, valor_bnh):
        diferencia = valor_pof - valor_bnh

        if diferencia == 0:
            return "COINCIDE"

        if valor_pof > 0 and valor_bnh == 0:
            return "SIN_BNH"

        if valor_pof == 0 and valor_bnh > 0:
            return "SOLO_BNH"

        if diferencia > 0:
            return "FALTA_BNH"

        return "EXCEDE_BNH"

    prioridad_estado = {
        "SIN_BNH": 0,
        "FALTA_BNH": 1,
        "EXCEDE_BNH": 2,
        "SOLO_BNH": 3,
        "COINCIDE": 4,
    }

    cargos = []
    horas = []

    ceics = sorted(
        set(pof.keys())
        |
        set(bnh.keys())
    )

    for ceic in ceics:
        dato_pof = pof.get(ceic, {})
        dato_bnh = bnh.get(ceic, {})

        descripcion = (
            dato_pof.get("descripcion")
            or dato_bnh.get("descripcion")
            or ""
        )

        cargos_pof = float(
            dato_pof.get("cargos", 0)
        )
        cargos_bnh = float(
            dato_bnh.get("cargos", 0)
        )

        if cargos_pof or cargos_bnh:
            cargos.append({
                "ceic": ceic,
                "descripcion": descripcion,
                "pof": cargos_pof,
                "bnh": cargos_bnh,
                "diferencia": cargos_pof - cargos_bnh,
                "estado": _estado(
                    cargos_pof,
                    cargos_bnh,
                ),
            })

        horas_pof = float(
            dato_pof.get("horas", 0)
        )
        horas_bnh = float(
            dato_bnh.get("horas", 0)
        )

        if horas_pof or horas_bnh:
            horas.append({
                "ceic": ceic,
                "descripcion": descripcion,
                "pof": horas_pof,
                "bnh": horas_bnh,
                "diferencia": horas_pof - horas_bnh,
                "estado": _estado(
                    horas_pof,
                    horas_bnh,
                ),
            })

    cargos.sort(
        key=lambda row: (
            prioridad_estado.get(
                row["estado"],
                99,
            ),
            -abs(row["diferencia"]),
            row["ceic"],
        )
    )

    horas.sort(
        key=lambda row: (
            prioridad_estado.get(
                row["estado"],
                99,
            ),
            -abs(row["diferencia"]),
            row["ceic"],
        )
    )

    # --------------------------------------------------------
    # Totales
    # --------------------------------------------------------

    total_cargos_pof = sum(
        row["pof"]
        for row in cargos
    )
    total_cargos_bnh = sum(
        row["bnh"]
        for row in cargos
    )
    total_horas_pof = sum(
        row["pof"]
        for row in horas
    )
    total_horas_bnh = sum(
        row["bnh"]
        for row in horas
    )

    return {
        "cueanexo": cue,
        "anio_objetivo": anio_objetivo,
        "anio_pof": (
            int(anio_pof)
            if anio_pof is not None
            else None
        ),
        "anio_bnh": anio_objetivo,
        "pof_disponible": pof_disponible,
        "usa_anio_anterior": usa_anio_anterior,
        "mensaje_pof": mensaje_pof,
        "resumen": {
            "cargos_pof": total_cargos_pof,
            "cargos_bnh": total_cargos_bnh,
            "diferencia_cargos": (
                total_cargos_pof
                - total_cargos_bnh
            ),
            "horas_pof": total_horas_pof,
            "horas_bnh": total_horas_bnh,
            "diferencia_horas": (
                total_horas_pof
                - total_horas_bnh
            ),
        },
        "cargos": cargos,
        "horas": horas,
    }


# ============================================================
# ESTADO OPERATIVO BNH
# ============================================================

def derive_status(
    metrics,
):

    cargos = (
        metrics.get(
            "cargos",
            0,
        )
        or 0
    )

    if cargos == 0:
        return "SIN_CARGA"

    if (
        metrics.get(
            "observados",
            0,
        )
        or 0
    ) > 0:
        return "OBSERVADO"

    if (
        metrics.get(
            "borradores",
            0,
        )
        or 0
    ) > 0:
        return "EN_PROCESO"

    if (
        metrics.get(
            "validados",
            0,
        )
        or 0
    ) == cargos:
        return "VALIDADO"

    return "EN_PROCESO"


# ============================================================
# INSTITUCIONES ENRIQUECIDAS
# ============================================================

def enrich_institutions(
    user,
):

    """
    Consolida para cada CUEANEXO:

    - datos institucionales
    - métricas operativas BNH
    - cobertura RA vs BNH
    """

    institutions = (
        institution_catalog(
            user
        )
    )

    cues = [
        item["cueanexo"]
        for item
        in institutions
    ]

    # --------------------------------------------------------
    # Indicadores operativos BNH
    # --------------------------------------------------------

    metrics = (
        activity_metrics_by_cue(
            user,
            cues,
        )
    )

    # --------------------------------------------------------
    # Comparativa RA 2026 vs BNH vivo
    # --------------------------------------------------------

    coverage = (
        cobertura_por_cue(
            cues
        )
    )

    # --------------------------------------------------------
    # Control de actualización
    # --------------------------------------------------------

    stale_days = int(
        getattr(
            settings,
            "BNH_MONITOR_STALE_DAYS",
            30,
        )
    )

    stale_limit = (
        timezone.now()
        -
        timedelta(
            days=stale_days
        )
    )

    # --------------------------------------------------------
    # Integración
    # --------------------------------------------------------

    for item in institutions:

        cue = (
            item["cueanexo"]
        )

        data = metrics.get(
            cue,
            {},
        )

        ra = coverage.get(
            cue,
            {},
        )

        item.update(
            {

                # =================================================
                # BNH OPERATIVO
                # =================================================

                "personas":
                    data.get(
                        "personas",
                        0,
                    )
                    or 0,

                "cargos":
                    data.get(
                        "cargos",
                        0,
                    )
                    or 0,

                "docentes":
                    data.get(
                        "docentes",
                        0,
                    )
                    or 0,

                "no_docentes":
                    data.get(
                        "no_docentes",
                        0,
                    )
                    or 0,

                "borradores":
                    data.get(
                        "borradores",
                        0,
                    )
                    or 0,

                "validados":
                    data.get(
                        "validados",
                        0,
                    )
                    or 0,

                "observados":
                    data.get(
                        "observados",
                        0,
                    )
                    or 0,

                "ultima_actualizacion":
                    data.get(
                        "ultima_actualizacion"
                    ),


                # =================================================
                # RA vs BNH - CARGOS
                # =================================================

                "total_cargos_ra":
                    ra.get(
                        "total_cargos_ra",
                        0,
                    )
                    or 0,

                "total_cargos_bnh":
                    ra.get(
                        "total_cargos_bnh",
                        0,
                    )
                    or 0,

                "diferencia_cargos":
                    ra.get(
                        "diferencia_cargos",
                        0,
                    )
                    or 0,

                "porcentaje_cargos":
                    ra.get(
                        "porcentaje_cargos"
                    ),

                "progreso_cargos":
                    ra.get(
                        "progreso_cargos",
                        0,
                    )
                    or 0,

                "estado_cargos":
                    ra.get(
                        "estado_cargos",
                        "SIN UNIVERSO",
                    ),


                # =================================================
                # RA vs BNH - HORAS CÁTEDRA
                # =================================================

                "total_horas_ra":
                    ra.get(
                        "total_horas_ra",
                        0,
                    )
                    or 0,

                "total_horas_bnh":
                    ra.get(
                        "total_horas_bnh",
                        0,
                    )
                    or 0,

                "diferencia_horas":
                    ra.get(
                        "diferencia_horas",
                        0,
                    )
                    or 0,

                "porcentaje_horas":
                    ra.get(
                        "porcentaje_horas"
                    ),

                "progreso_horas":
                    ra.get(
                        "progreso_horas",
                        0,
                    )
                    or 0,

                "estado_horas":
                    ra.get(
                        "estado_horas",
                        "SIN UNIVERSO",
                    ),
            }
        )

        # --------------------------------------------------------
        # Estado BNH de carga
        # --------------------------------------------------------

        item[
            "estado_carga"
        ] = derive_status(
            item
        )

        # --------------------------------------------------------
        # Desactualización
        # --------------------------------------------------------

        item[
            "desactualizada"
        ] = bool(
            item[
                "ultima_actualizacion"
            ]
            and
            item[
                "ultima_actualizacion"
            ] < stale_limit
        )

    return institutions


# ============================================================
# FILTROS
# ============================================================

def apply_institution_filters(
    items,
    params,
):

    q = (
        params.get(
            "q"
        )
        or ""
    ).strip().casefold()

    region = (
        params.get(
            "region"
        )
        or ""
    ).strip()

    estado = (
        params.get(
            "estado"
        )
        or ""
    ).strip().upper()

    result = []

    for item in items:

        if (
            region
            and
            item["region"] != region
        ):
            continue

        if (
            estado
            and
            item[
                "estado_carga"
            ] != estado
        ):
            continue

        if q:

            haystack = " ".join(
                [
                    item[
                        "cueanexo"
                    ],
                    item[
                        "nom_est"
                    ],
                    item[
                        "region"
                    ],
                    " ".join(
                        item[
                            "ofertas"
                        ]
                    ),
                    " ".join(
                        item[
                            "acronimos"
                        ]
                    ),
                ]
            ).casefold()

            if q not in haystack:
                continue

        result.append(
            item
        )

    return result


# ============================================================
# KPI OPERATIVOS GENERALES
# ============================================================

def jurisdiction_kpis(
    user,
    institution_rows,
):

    cues = [
        item[
            "cueanexo"
        ]
        for item
        in institution_rows
    ]

    total = len(
        cues
    )

    con_carga = sum(
        1
        for item
        in institution_rows
        if item["cargos"] > 0
    )

    sin_carga = (
        total
        -
        con_carga
    )

    qs = scoped_activities(
        user,
        cues,
    )

    aggregate = qs.aggregate(

        personas_unicas=Count(
            "persona_id",
            distinct=True,
        ),

        cargos=Count(
            "id"
        ),

        cargos_docentes=Count(
            "id",
            filter=Q(
                tipo_personal_id=1
            ),
        ),

        cargos_no_docentes=Count(
            "id",
            filter=Q(
                tipo_personal_id=2
            ),
        ),

        borradores=Count(
            "id",
            filter=Q(
                validacion=
                VALIDACION_BORRADOR
            ),
        ),

        validados=Count(
            "id",
            filter=Q(
                validacion=
                VALIDACION_VALIDADO
            ),
        ),

        observados=Count(
            "id",
            filter=Q(
                validacion=
                VALIDACION_OBSERVADO
            ),
        ),

        ultima_actualizacion=Max(
            "fecha_modificacion"
        ),
    )

    aggregate.update(
        {

            "instituciones":
                total,

            "instituciones_con_carga":
                con_carga,

            "instituciones_sin_carga":
                sin_carga,

            # Este indicador mide INICIO DE CARGA
            # y NO cobertura respecto al RA.

            "cobertura":
                round(
                    (
                        con_carga
                        /
                        total
                        * 100
                    ),
                    1,
                )
                if total
                else 0,

            "cobertura_institucional":
                round(
                    (
                        con_carga
                        /
                        total
                        * 100
                    ),
                    1,
                )
                if total
                else 0,

            "instituciones_desactualizadas":
                sum(
                    1
                    for item
                    in institution_rows
                    if (
                        item[
                            "cargos"
                        ]
                        and
                        item[
                            "desactualizada"
                        ]
                    )
                ),
        }
    )

    return aggregate


# ============================================================
# COBERTURA GENERAL RA vs BNH
# ============================================================

def coverage_summary(
    institution_rows,
):

    """
    Calcula cobertura ponderada:

        SUM(BNH) / SUM(RA) * 100

    NO promedia porcentajes por escuela.
    """

    total_cargos_ra = sum(
        (
            item.get(
                "total_cargos_ra",
                0,
            )
            or 0
        )
        for item
        in institution_rows
    )

    total_cargos_bnh = sum(
        (
            item.get(
                "total_cargos_bnh",
                0,
            )
            or 0
        )
        for item
        in institution_rows
    )

    total_horas_ra = sum(
        (
            item.get(
                "total_horas_ra",
                0,
            )
            or 0
        )
        for item
        in institution_rows
    )

    total_horas_bnh = sum(
        (
            item.get(
                "total_horas_bnh",
                0,
            )
            or 0
        )
        for item
        in institution_rows
    )

    porcentaje_cargos = (
        _porcentaje(
            total_cargos_bnh,
            total_cargos_ra,
        )
    )

    porcentaje_horas = (
        _porcentaje(
            total_horas_bnh,
            total_horas_ra,
        )
    )

    return {

        # =====================================================
        # CARGOS
        # =====================================================

        "total_cargos_ra":
            total_cargos_ra,

        "total_cargos_bnh":
            total_cargos_bnh,

        "diferencia_cargos":
            (
                total_cargos_ra
                -
                total_cargos_bnh
            ),

        "porcentaje_cargos":
            porcentaje_cargos,

        "progreso_cargos":
            min(
                max(
                    porcentaje_cargos
                    or 0,
                    0,
                ),
                100,
            ),

        "estado_cargos":
            _estado_cobertura(
                total_cargos_bnh,
                total_cargos_ra,
            ),

        # =====================================================
        # HORAS
        # =====================================================

        "total_horas_ra":
            total_horas_ra,

        "total_horas_bnh":
            total_horas_bnh,

        "diferencia_horas":
            (
                total_horas_ra
                -
                total_horas_bnh
            ),

        "porcentaje_horas":
            porcentaje_horas,

        "progreso_horas":
            min(
                max(
                    porcentaje_horas
                    or 0,
                    0,
                ),
                100,
            ),

        "estado_horas":
            _estado_cobertura(
                total_horas_bnh,
                total_horas_ra,
            ),

        # =====================================================
        # CONTROL CUE - CARGOS
        # =====================================================

        "cue_sin_carga_cargos":
            sum(
                1
                for item
                in institution_rows
                if (
                    (
                        item.get(
                            "total_cargos_ra",
                            0,
                        )
                        or 0
                    ) > 0
                    and
                    (
                        item.get(
                            "total_cargos_bnh",
                            0,
                        )
                        or 0
                    ) == 0
                )
            ),

        "cue_completos_cargos":
            sum(
                1
                for item
                in institution_rows
                if (
                    (
                        item.get(
                            "total_cargos_ra",
                            0,
                        )
                        or 0
                    ) > 0
                    and
                    (
                        item.get(
                            "total_cargos_bnh",
                            0,
                        )
                        or 0
                    )
                    ==
                    (
                        item.get(
                            "total_cargos_ra",
                            0,
                        )
                        or 0
                    )
                )
            ),

        "cue_excedidos_cargos":
            sum(
                1
                for item
                in institution_rows
                if (
                    (
                        item.get(
                            "total_cargos_ra",
                            0,
                        )
                        or 0
                    ) > 0
                    and
                    (
                        item.get(
                            "total_cargos_bnh",
                            0,
                        )
                        or 0
                    )
                    >
                    (
                        item.get(
                            "total_cargos_ra",
                            0,
                        )
                        or 0
                    )
                )
            ),

        # =====================================================
        # CONTROL CUE - HORAS
        # =====================================================

        "cue_sin_carga_horas":
            sum(
                1
                for item
                in institution_rows
                if (
                    (
                        item.get(
                            "total_horas_ra",
                            0,
                        )
                        or 0
                    ) > 0
                    and
                    (
                        item.get(
                            "total_horas_bnh",
                            0,
                        )
                        or 0
                    ) == 0
                )
            ),

        "cue_completos_horas":
            sum(
                1
                for item
                in institution_rows
                if (
                    (
                        item.get(
                            "total_horas_ra",
                            0,
                        )
                        or 0
                    ) > 0
                    and
                    (
                        item.get(
                            "total_horas_bnh",
                            0,
                        )
                        or 0
                    )
                    ==
                    (
                        item.get(
                            "total_horas_ra",
                            0,
                        )
                        or 0
                    )
                )
            ),

        "cue_excedidos_horas":
            sum(
                1
                for item
                in institution_rows
                if (
                    (
                        item.get(
                            "total_horas_ra",
                            0,
                        )
                        or 0
                    ) > 0
                    and
                    (
                        item.get(
                            "total_horas_bnh",
                            0,
                        )
                        or 0
                    )
                    >
                    (
                        item.get(
                            "total_horas_ra",
                            0,
                        )
                        or 0
                    )
                )
            ),
    }


# ============================================================
# RESUMEN REGIONAL
# ============================================================

def regional_summary(
    institution_rows,
):

    grouped = defaultdict(
        lambda: {

            # Operativo
            "instituciones": 0,
            "con_carga": 0,
            "sin_carga": 0,
            "cargos": 0,
            "observados": 0,
            "borradores": 0,

            # RA vs BNH
            "total_cargos_ra": 0,
            "total_cargos_bnh": 0,

            "total_horas_ra": 0,
            "total_horas_bnh": 0,
        }
    )

    for item in institution_rows:

        region = (
            item["region"]
            or
            "Sin región informada"
        )

        row = grouped[
            region
        ]

        # ----------------------------------------------------
        # Operativo
        # ----------------------------------------------------

        row[
            "instituciones"
        ] += 1

        row[
            "cargos"
        ] += (
            item[
                "cargos"
            ]
        )

        row[
            "observados"
        ] += (
            item[
                "observados"
            ]
        )

        row[
            "borradores"
        ] += (
            item[
                "borradores"
            ]
        )

        if item[
            "cargos"
        ]:

            row[
                "con_carga"
            ] += 1

        else:

            row[
                "sin_carga"
            ] += 1

        # ----------------------------------------------------
        # RA vs BNH
        # ----------------------------------------------------

        row[
            "total_cargos_ra"
        ] += (
            item.get(
                "total_cargos_ra",
                0,
            )
            or 0
        )

        row[
            "total_cargos_bnh"
        ] += (
            item.get(
                "total_cargos_bnh",
                0,
            )
            or 0
        )

        row[
            "total_horas_ra"
        ] += (
            item.get(
                "total_horas_ra",
                0,
            )
            or 0
        )

        row[
            "total_horas_bnh"
        ] += (
            item.get(
                "total_horas_bnh",
                0,
            )
            or 0
        )

    result = []

    for (
        region,
        row,
    ) in grouped.items():

        row[
            "region"
        ] = region

        # ----------------------------------------------------
        # Cobertura institucional
        # ----------------------------------------------------

        row[
            "cobertura"
        ] = (
            round(
                row[
                    "con_carga"
                ]
                /
                row[
                    "instituciones"
                ]
                * 100,
                1,
            )
            if row[
                "instituciones"
            ]
            else 0
        )

        # ----------------------------------------------------
        # Cargos RA
        # ----------------------------------------------------

        row[
            "diferencia_cargos"
        ] = (
            row[
                "total_cargos_ra"
            ]
            -
            row[
                "total_cargos_bnh"
            ]
        )

        row[
            "porcentaje_cargos"
        ] = _porcentaje(
            row[
                "total_cargos_bnh"
            ],
            row[
                "total_cargos_ra"
            ],
        )

        row[
            "progreso_cargos"
        ] = min(
            max(
                row[
                    "porcentaje_cargos"
                ]
                or 0,
                0,
            ),
            100,
        )

        row[
            "estado_cargos"
        ] = _estado_cobertura(
            row[
                "total_cargos_bnh"
            ],
            row[
                "total_cargos_ra"
            ],
        )

        # ----------------------------------------------------
        # Horas RA
        # ----------------------------------------------------

        row[
            "diferencia_horas"
        ] = (
            row[
                "total_horas_ra"
            ]
            -
            row[
                "total_horas_bnh"
            ]
        )

        row[
            "porcentaje_horas"
        ] = _porcentaje(
            row[
                "total_horas_bnh"
            ],
            row[
                "total_horas_ra"
            ],
        )

        row[
            "progreso_horas"
        ] = min(
            max(
                row[
                    "porcentaje_horas"
                ]
                or 0,
                0,
            ),
            100,
        )

        row[
            "estado_horas"
        ] = _estado_cobertura(
            row[
                "total_horas_bnh"
            ],
            row[
                "total_horas_ra"
            ],
        )

        result.append(
            row
        )

    return sorted(
        result,
        key=lambda value:
            value[
                "region"
            ],
    )


# ============================================================
# COBERTURA DE UNA INSTITUCIÓN
# ============================================================

def institution_coverage(
    user,
    cueanexo,
):

    cue = normalize_cue(
        cueanexo
    )

    permitidos = {
        normalize_cue(
            value
        )
        for value
        in allowed_cueanexos(
            user
        )
    }

    if cue not in permitidos:

        return {

            "cueanexo":
                cue,

            "total_cargos_ra":
                0,

            "total_cargos_bnh":
                0,

            "diferencia_cargos":
                0,

            "porcentaje_cargos":
                None,

            "progreso_cargos":
                0,

            "estado_cargos":
                "SIN UNIVERSO",

            "total_horas_ra":
                0,

            "total_horas_bnh":
                0,

            "diferencia_horas":
                0,

            "porcentaje_horas":
                None,

            "progreso_horas":
                0,

            "estado_horas":
                "SIN UNIVERSO",
        }

    data = (
        cobertura_por_cue(
            [cue]
        ).get(
            cue
        )
    )

    if data:
        return data

    return {

        "cueanexo":
            cue,

        "total_cargos_ra":
            0,

        "total_cargos_bnh":
            0,

        "diferencia_cargos":
            0,

        "porcentaje_cargos":
            None,

        "progreso_cargos":
            0,

        "estado_cargos":
            "SIN UNIVERSO",

        "total_horas_ra":
            0,

        "total_horas_bnh":
            0,

        "diferencia_horas":
            0,

        "porcentaje_horas":
            None,

        "progreso_horas":
            0,

        "estado_horas":
            "SIN UNIVERSO",
    }


# ============================================================
# AUDITORÍA
# ============================================================

def recent_audit(
    user,
    cueanexos,
    limit=20,
):

    cues = tuple(
        cueanexos
    )

    if not cues:
        return (
            EventoAuditoria.objects.none()
        )

    return (
        EventoAuditoria.objects
        .filter(
            cueanexo__in=cues
        )
        .select_related(
            "usuario"
        )
        .order_by(
            "-fecha",
            "-pk",
        )[:limit]
    )


# ============================================================
# OFERTAS DE UNA INSTITUCIÓN
# ============================================================

def institution_offers(
    user,
    cueanexo,
):

    return list(
        scoped_offers(
            user
        )
        .filter(
            cueanexo=cueanexo
        )
        .order_by(
            "oferta"
        )
        .values(
            "cueanexo",
            "nom_est",
            "region_loc",
            "oferta",
            "acronimo",
        )
    )


# ============================================================
# ACTIVIDADES DE UNA INSTITUCIÓN
# ============================================================

def institution_activities(
    user,
    cueanexo,
):

    return (
        scoped_activities(
            user,
            [cueanexo],
        )
        .select_related(
            "persona",
            "tipo_personal",
            "modalidad",
            "niveles",
            "ceic",
            "sit_revista",
            "cond_actividad",
            "t_designacion",
        )
        .order_by(
            "persona__apellido",
            "persona__nombre",
            "ceic__descripcion",
            "f_desde",
            "pk",
        )
    )


# ============================================================
# AUDITORÍA INSTITUCIONAL
# ============================================================

def institution_audit(
    cueanexo,
    limit=50,
):

    return (
        EventoAuditoria.objects
        .filter(
            cueanexo=cueanexo
        )
        .select_related(
            "usuario"
        )
        .order_by(
            "-fecha",
            "-pk",
        )[:limit]
    )