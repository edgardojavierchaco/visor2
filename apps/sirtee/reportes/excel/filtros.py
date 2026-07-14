from apps.sirtee.filters.intervenciones import (
    IntervencionFilter
)

from apps.sirtee.filters.empresas import (
    EmpresaFilter
)



def aplicar_filtro_intervenciones(
    request,
    queryset
):

    filtro = IntervencionFilter(
        request.GET,
        queryset=queryset
    )

    return filtro.qs



def aplicar_filtro_empresas(
    request,
    queryset
):

    filtro = EmpresaFilter(
        request.GET,
        queryset=queryset
    )

    return filtro.qs