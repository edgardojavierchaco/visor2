from django.shortcuts import render

from .permisos import (
    cef_visualizacion_required,
    get_cefs_visualizacion_usuario,
    resolver_cueanexos_visualizacion_desde_request,
)


@cef_visualizacion_required
def visualizacion_responsables(request):
    cefs_visualizacion = get_cefs_visualizacion_usuario(request.user)
    cueanexos_seleccionados = resolver_cueanexos_visualizacion_desde_request(
        request
    )

    responsables = cefs_visualizacion
    if cueanexos_seleccionados:
        responsables = responsables.filter(cueanexo__in=cueanexos_seleccionados)

    responsables = responsables.order_by(
        "region_loc",
        "localidad",
        "cueanexo",
        "apellido_resp",
        "nombre_resp",
    )

    context = {
        "title": "Responsables CEF",
        "active_menu": "responsables",
        "cefs_visualizacion": cefs_visualizacion,
        "cueanexos_seleccionados": cueanexos_seleccionados,
        "total_cefs_visibles": cefs_visualizacion.count(),
        "total_cefs_seleccionados": len(cueanexos_seleccionados),
        "responsables": responsables,
        "total_responsables": responsables.count(),
    }

    return render(request, "cef/responsables_cef.html", context)
