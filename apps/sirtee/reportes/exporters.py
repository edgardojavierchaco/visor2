import csv



def exportar_intervenciones_csv(
    response,
    queryset
):


    response["Content-Type"] = (
        "text/csv"
    )


    response[
        "Content-Disposition"
    ] = (
        "attachment; filename="
        "\"intervenciones.csv\""
    )



    writer = csv.writer(
        response
    )


    writer.writerow([

        "Título",

        "Escuela",

        "Empresa",

        "Estado",

        "Avance",

        "Costo"

    ])



    for item in queryset:


        writer.writerow([

            item.titulo,

            item.hallazgo.relevamiento.cueanexo,

            item.empresa,

            item.estado.nombre,

            item.porcentaje_avance,

            item.costo_estimado,

        ])



    return response