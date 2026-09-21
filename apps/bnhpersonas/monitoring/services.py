import csv

from django.http import HttpResponse

from .selectors import institution_activities


def csv_response(filename):
    response = HttpResponse(
        content_type="text/csv; charset=utf-8",
    )
    response["Content-Disposition"] = (
        f'attachment; filename="{filename}"'
    )
    response.write("\ufeff")
    return response


def export_institutions(rows):
    response = csv_response("bnh_seguimiento_instituciones.csv")
    writer = csv.writer(response)
    writer.writerow(
        [
            "CUEANEXO",
            "Institución",
            "Regional",
            "Ofertas",
            "Estado de carga",
            "Personas",
            "Cargos",
            "Docentes",
            "No docentes",
            "Pendientes",
            "Observados",
            "Validados",
            "Última actualización",
        ]
    )

    for item in rows:
        writer.writerow(
            [
                item["cueanexo"],
                item["nom_est"],
                item["region"],
                " | ".join(item["ofertas"]),
                item["estado_carga"],
                item["personas"],
                item["cargos"],
                item["docentes"],
                item["no_docentes"],
                item["borradores"],
                item["observados"],
                item["validados"],
                (
                    item["ultima_actualizacion"].isoformat()
                    if item["ultima_actualizacion"]
                    else ""
                ),
            ]
        )
    return response


def export_personnel(user, cueanexos):
    response = csv_response("bnh_seguimiento_personal.csv")
    writer = csv.writer(response)
    writer.writerow(
        [
            "ID Puesto",
            "CUEANEXO",
            "CUIL",
            "DNI",
            "Apellido",
            "Nombre",
            "Tipo de personal",
            "Modalidad cargo",
            "Nivel cargo",
            "CEIC",
            "Descripción CEIC",
            "Situación de revista",
            "Condición de actividad",
            "Tipo de designación",
            "Fecha desde",
            "Fecha hasta",
            "Carga horaria",
            "Estado",
            "Validación",
            "Última modificación",
        ]
    )

    for cue in cueanexos:
        for activity in institution_activities(user, cue).iterator(chunk_size=1000):
            person = activity.persona
            writer.writerow(
                [
                    activity.id_puesto,
                    activity.cueanexo,
                    person.cuil or "",
                    person.dni or "",
                    person.apellido,
                    person.nombre,
                    str(activity.tipo_personal),
                    str(activity.modalidad),
                    str(activity.niveles),
                    activity.ceic_id,
                    str(activity.ceic),
                    str(activity.sit_revista),
                    str(activity.cond_actividad or ""),
                    str(activity.t_designacion),
                    activity.f_desde,
                    activity.f_hasta or "",
                    activity.carga_horaria,
                    activity.estado,
                    activity.validacion,
                    activity.fecha_modificacion.isoformat()
                    if activity.fecha_modificacion
                    else "",
                ]
            )
    return response
