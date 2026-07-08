from django.http import HttpResponse

from apps.sirtee.reportes.excel.intervenciones import (
    IntervencionesExcel
)

from apps.sirtee.reportes.excel.empresas import (
    EmpresasExcel
)

from apps.sirtee.reportes.excel.general import (
    ReporteGeneralExcel
)


def exportar_intervenciones_excel(request):


    reporte = (
        IntervencionesExcel()
        .generar()
    )


    response = HttpResponse(
        content_type=
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


    response[
        "Content-Disposition"
    ] = (
        "attachment;"
        " filename="
        "intervenciones_sirtee.xlsx"
    )


    reporte.save(
        response
    )


    return response





def exportar_empresas_excel(request):


    reporte = (
        EmpresasExcel()
        .generar()
    )


    response = HttpResponse(
        content_type=
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


    response[
        "Content-Disposition"
    ] = (
        "attachment;"
        " filename="
        "empresas_sirtee.xlsx"
    )


    reporte.save(
        response
    )


    return response


def exportar_general_excel(
    request
):


    archivo = (
        ReporteGeneralExcel()
        .generar()
    )


    response = HttpResponse(
        content_type=
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


    response[
        "Content-Disposition"
    ] = (
        "attachment;"
        " filename="
        "reporte_general_sirtee.xlsx"
    )


    archivo.save(
        response
    )


    return response