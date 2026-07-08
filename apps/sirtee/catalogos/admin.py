from django.contrib import admin

from .models import (
    BaseCatalogo, 
    SistemaConstructivo, 
    AreaAfectada, 
    TipoHallazgo,
    Criticidad,
    Riesgo,
    EstadoHallazgo,
    TipoIntervencion,
    EstadoIntervencion,
    Prioridad,
    FuenteFinanciamiento,
    OrganismoResponsable,
)


class BaseCatalogoAdmin(admin.ModelAdmin):

    list_display = (
        "codigo",
        "nombre",
        "orden",
        "activo",
    )

    list_filter = (
        "activo",
    )

    search_fields = (
        "codigo",
        "nombre",
    )

    ordering = (
        "orden",
        "nombre",
    )

admin.site.register(
    SistemaConstructivo,
    BaseCatalogoAdmin,
)

admin.site.register(
    AreaAfectada,
    BaseCatalogoAdmin,
)

admin.site.register(
    TipoHallazgo,
    BaseCatalogoAdmin,
)

admin.site.register(
    Criticidad,
    BaseCatalogoAdmin,
)

admin.site.register(
    Riesgo,
    BaseCatalogoAdmin,
)

admin.site.register(
    EstadoHallazgo,
    BaseCatalogoAdmin,
)

admin.site.register(
    TipoIntervencion,
    BaseCatalogoAdmin,
)

admin.site.register(
    EstadoIntervencion,
    BaseCatalogoAdmin,
)

admin.site.register(
    Prioridad,
    BaseCatalogoAdmin,
)

admin.site.register(
    FuenteFinanciamiento,
    BaseCatalogoAdmin,
)

admin.site.register(
    OrganismoResponsable,
    BaseCatalogoAdmin,
)