from django.shortcuts import render

from .permisos import (
    cef_visualizacion_required,
    get_cefs_visualizacion_usuario,
    resolver_cueanexos_visualizacion_desde_request,
)


def get_contexto_visualizacion(request, title, active_menu):
    cefs_visualizacion = get_cefs_visualizacion_usuario(request.user)
    cueanexos_seleccionados = resolver_cueanexos_visualizacion_desde_request(
        request
    )

    return {
        "title": title,
        "active_menu": active_menu,
        "cefs_visualizacion": cefs_visualizacion,
        "cueanexos_seleccionados": cueanexos_seleccionados,
        "total_cefs_visibles": cefs_visualizacion.count(),
        "total_cefs_seleccionados": len(cueanexos_seleccionados),
    }


@cef_visualizacion_required
def visualizacion_inicio(request):
    context = get_contexto_visualizacion(
        request,
        "Visualizacion CEF",
        "inicio",
    )
    return render(request, "cef/inicio.html", context)
