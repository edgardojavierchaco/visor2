import csv

from django.http import HttpResponse, StreamingHttpResponse

from .selectors import scoped_activities


class _Echo:
    """Pseudo-buffer para csv.writer + StreamingHttpResponse."""

    def write(self, value):
        return value


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


def _personnel_csv_rows(user, cueanexos):
    """
    Genera el CSV nominal en streaming.

    Importante:
    - hace UNA única consulta de actividades para todos los CUEANEXO visibles;
    - usa select_related para evitar consultas N+1 de catálogos/persona;
    - iterator() mantiene bajo el consumo de memoria;
    - no deduplica registros: exporta cada actividad almacenada.
    """

    pseudo_buffer = _Echo()
    writer = csv.writer(pseudo_buffer)

    # BOM UTF-8 para que Excel abra correctamente tildes y ñ.
    yield "\ufeff"

    yield writer.writerow(
        [
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

    activities = (
        scoped_activities(user, cueanexos)
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
            "cueanexo",
            "persona__apellido",
            "persona__nombre",
            "ceic__descripcion",
            "f_desde",
            "pk",
        )
    )

    for activity in activities.iterator(chunk_size=2000):
        person = activity.persona

        yield writer.writerow(
            [
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
                (
                    activity.fecha_modificacion.isoformat()
                    if activity.fecha_modificacion
                    else ""
                ),
            ]
        )


def export_personnel(user, cueanexos):
    """
    Exportación nominal optimizada.

    La versión anterior ejecutaba institution_activities() dentro de un bucle
    por CUEANEXO. Con miles de unidades eso provocaba miles de consultas SQL y
    la respuesta no comenzaba hasta terminar de construir todo el archivo.

    Esta versión consulta todas las actividades del universo filtrado en una
    única QuerySet y devuelve el CSV progresivamente mediante streaming.
    """

    response = StreamingHttpResponse(
        _personnel_csv_rows(user, cueanexos),
        content_type="text/csv; charset=utf-8",
    )
    response["Content-Disposition"] = (
        'attachment; filename="bnh_seguimiento_personal.csv"'
    )
    response["X-Accel-Buffering"] = "no"
    return response
