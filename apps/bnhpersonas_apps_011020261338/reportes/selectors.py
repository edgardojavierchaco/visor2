from collections import defaultdict

from apps.bnhpersonas.monitoring.selectors import enrich_institutions


ESTADOS_CARGA = (
    ("SIN_CARGA", "Sin carga"),
    ("EN_PROCESO", "En proceso"),
    ("OBSERVADO", "Con observaciones"),
    ("VALIDADO", "Validado"),
)

ESTADO_LABELS = dict(ESTADOS_CARGA)


def _texto(value):
    return str(value or "").strip()


def _porcentaje(numerador, denominador):
    if not denominador:
        return 0.0
    return round((numerador / denominador) * 100, 1)


def filter_report_rows(rows, params):
    """Aplica filtros sin ampliar jamás el alcance resuelto por monitoreo."""
    region = _texto(params.get("region"))
    estado = _texto(params.get("estado")).upper()
    q = _texto(params.get("q")).casefold()

    filtered = []
    for row in rows:
        if region and row.get("region") != region:
            continue
        if estado and row.get("estado_carga") != estado:
            continue
        if q:
            haystack = " ".join(
                [
                    _texto(row.get("cueanexo")),
                    _texto(row.get("nom_est")),
                    _texto(row.get("region")),
                    " ".join(row.get("ofertas") or []),
                    " ".join(row.get("acronimos") or []),
                ]
            ).casefold()
            if q not in haystack:
                continue
        filtered.append(row)

    return filtered


def report_rows(user, params):
    """
    Devuelve el detalle por CUEANEXO dentro del alcance autorizado.

    La fuente institucional es CapaUnicaOfertas y las métricas provienen
    del monitoreo BNH existente, de modo que el reporte y el dashboard
    comparten exactamente la misma definición de estado de carga.
    """
    rows = enrich_institutions(user)
    return filter_report_rows(rows, params)


def available_regions(user):
    """Regionales visibles para el usuario según su alcance autorizado."""
    rows = enrich_institutions(user)
    return sorted({row.get("region") or "Sin región informada" for row in rows})


def regional_load_summary(rows):
    """Agrupa el estado de carga por Regional Educativa."""
    grouped = defaultdict(
        lambda: {
            "instituciones": 0,
            "sin_carga": 0,
            "en_proceso": 0,
            "observado": 0,
            "validado": 0,
            "personas": 0,
            "cargos": 0,
            "docentes": 0,
            "no_docentes": 0,
            "borradores": 0,
            "observados": 0,
            "validados": 0,
        }
    )

    for item in rows:
        region = item.get("region") or "Sin región informada"
        data = grouped[region]
        data["instituciones"] += 1
        data["personas"] += item.get("personas", 0) or 0
        data["cargos"] += item.get("cargos", 0) or 0
        data["docentes"] += item.get("docentes", 0) or 0
        data["no_docentes"] += item.get("no_docentes", 0) or 0
        data["borradores"] += item.get("borradores", 0) or 0
        data["observados"] += item.get("observados", 0) or 0
        data["validados"] += item.get("validados", 0) or 0

        estado = item.get("estado_carga")
        if estado == "SIN_CARGA":
            data["sin_carga"] += 1
        elif estado == "OBSERVADO":
            data["observado"] += 1
        elif estado == "VALIDADO":
            data["validado"] += 1
        else:
            data["en_proceso"] += 1

    result = []
    for region, data in grouped.items():
        total = data["instituciones"]
        con_carga = total - data["sin_carga"]
        item = {
            "region": region,
            **data,
            "con_carga": con_carga,
            "porcentaje_con_carga": _porcentaje(con_carga, total),
            "porcentaje_validado": _porcentaje(data["validado"], total),
        }
        result.append(item)

    return sorted(result, key=lambda item: item["region"].casefold())


def general_summary(rows):
    total = len(rows)
    estados = {key: 0 for key, _ in ESTADOS_CARGA}
    personas = 0
    cargos = 0

    for row in rows:
        estado = row.get("estado_carga") or "EN_PROCESO"
        estados[estado] = estados.get(estado, 0) + 1
        personas += row.get("personas", 0) or 0
        cargos += row.get("cargos", 0) or 0

    con_carga = total - estados.get("SIN_CARGA", 0)
    return {
        "instituciones": total,
        "con_carga": con_carga,
        "sin_carga": estados.get("SIN_CARGA", 0),
        "en_proceso": estados.get("EN_PROCESO", 0),
        "observado": estados.get("OBSERVADO", 0),
        "validado": estados.get("VALIDADO", 0),
        "personas": personas,
        "cargos": cargos,
        "porcentaje_con_carga": _porcentaje(con_carga, total),
        "porcentaje_validado": _porcentaje(estados.get("VALIDADO", 0), total),
    }
