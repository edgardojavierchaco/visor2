from django.shortcuts import render

from .models_integracion import get_datos_establecimiento_cef
from .permisos import (
    cef_director_required,
    cef_visualizacion_required,
    get_cefs_cargables_usuario,
    get_cefs_visualizacion_usuario,
    get_cueanexos_cargables_usuario,
    resolver_cef_cueanexo_activo,
    resolver_cueanexos_visualizacion_desde_request,
)


@cef_visualizacion_required
def visualizacion_establecimientos(request):
    cefs_visualizacion = get_cefs_visualizacion_usuario(request.user)
    cueanexos_seleccionados = resolver_cueanexos_visualizacion_desde_request(
        request
    )

    establecimientos = cefs_visualizacion
    if cueanexos_seleccionados:
        establecimientos = establecimientos.filter(
            cueanexo__in=cueanexos_seleccionados
        )

    establecimientos = establecimientos.order_by(
        "region_loc",
        "localidad",
        "cueanexo",
    )

    context = {
        "title": "Establecimientos CEF",
        "active_menu": "establecimientos",
        "cefs_visualizacion": cefs_visualizacion,
        "cueanexos_seleccionados": cueanexos_seleccionados,
        "total_cefs_visibles": cefs_visualizacion.count(),
        "total_cefs_seleccionados": len(cueanexos_seleccionados),
        "establecimientos": establecimientos,
        "total_establecimientos": establecimientos.count(),
    }

    return render(request, "cef/establecimientos_cef.html", context)


@cef_director_required
def establecimiento_director(request):
    cueanexo_activo = resolver_cef_cueanexo_activo(request)
    cefs_cargables = get_cefs_cargables_usuario(request.user)
    cueanexos_cargables = get_cueanexos_cargables_usuario(request.user)

    datos_establecimiento = None
    if cueanexo_activo:
        datos_establecimiento = get_datos_establecimiento_cef(cueanexo_activo)

    context = {
        "title": "Datos del establecimiento CEF",
        "active_menu": "establecimiento",
        "cef_cueanexo_activo": cueanexo_activo,
        "cefs_cargables": cefs_cargables,
        "cueanexos_cargables": cueanexos_cargables,
        "datos_establecimiento": datos_establecimiento,
    }

    return render(request, "cef/establecimiento_director_cef.html", context)
