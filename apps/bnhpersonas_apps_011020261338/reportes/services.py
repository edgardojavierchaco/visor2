import csv
from datetime import datetime

from django.http import HttpResponse
from django.utils import timezone

from .selectors import ESTADO_LABELS


def _filename(prefix):
    stamp = timezone.localtime().strftime("%Y%m%d_%H%M")
    return f"{prefix}_{stamp}.csv"


def _csv_response(filename):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    # BOM para que Excel abra UTF-8 correctamente.
    response.write("\ufeff")
    return response


def export_regional_summary_csv(summary):
    response = _csv_response(_filename("bnh_estado_carga_por_regional"))
    writer = csv.writer(response, delimiter=";")
    writer.writerow(
        [
            "Regional Educativa",
            "CUEANEXO alcanzados",
            "Con carga",
            "Sin carga",
            "En proceso",
            "Con observaciones",
            "Validados",
            "% con carga",
            "% validados",
            "Personas",
            "Cargos",
            "Docentes",
            "No docentes",
            "Cargos borrador",
            "Cargos observados",
            "Cargos validados",
        ]
    )
    for row in summary:
        writer.writerow(
            [
                row["region"],
                row["instituciones"],
                row["con_carga"],
                row["sin_carga"],
                row["en_proceso"],
                row["observado"],
                row["validado"],
                str(row["porcentaje_con_carga"]).replace(".", ","),
                str(row["porcentaje_validado"]).replace(".", ","),
                row["personas"],
                row["cargos"],
                row["docentes"],
                row["no_docentes"],
                row["borradores"],
                row["observados"],
                row["validados"],
            ]
        )
    return response


def export_cue_detail_csv(rows):
    response = _csv_response(_filename("bnh_estado_carga_detalle_cueanexo"))
    writer = csv.writer(response, delimiter=";")
    writer.writerow(
        [
            "Regional Educativa",
            "CUEANEXO",
            "Institución",
            "Oferta/s",
            "Estado de carga",
            "Personas",
            "Cargos",
            "Docentes",
            "No docentes",
            "Borradores",
            "Observados",
            "Validados",
            "Última actualización",
        ]
    )

    for row in rows:
        updated = row.get("ultima_actualizacion")
        if updated:
            try:
                updated = timezone.localtime(updated).strftime("%d/%m/%Y %H:%M")
            except (ValueError, TypeError):
                updated = str(updated)
        else:
            updated = ""

        writer.writerow(
            [
                row.get("region") or "Sin región informada",
                row.get("cueanexo") or "",
                row.get("nom_est") or "",
                " | ".join(row.get("ofertas") or []),
                ESTADO_LABELS.get(row.get("estado_carga"), row.get("estado_carga") or ""),
                row.get("personas", 0),
                row.get("cargos", 0),
                row.get("docentes", 0),
                row.get("no_docentes", 0),
                row.get("borradores", 0),
                row.get("observados", 0),
                row.get("validados", 0),
                updated,
            ]
        )
    return response
