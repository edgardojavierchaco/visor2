from django.urls import path

from apps.sirtee.api.views_padron import (
    buscar_escuelas,
    detalle_escuela,
)


urlpatterns = [

    # búsqueda autocomplete

    path(
        "escuelas/",
        buscar_escuelas,
        name="buscar-escuelas"
    ),


    # detalle por cueanexo

    path(
        "escuelas/<str:cueanexo>/",
        detalle_escuela,
        name="detalle-escuela"
    ),

]