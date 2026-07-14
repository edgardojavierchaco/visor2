# apps/sirtee/decorators.py

from functools import wraps

from apps.sirtee.permissions import (
    validar_permiso,
    PuedeVerMapa,
    PuedeVerIndicadores,
    PuedeVerRelevamientos,
    PuedeVerHallazgos,
    PuedeVerIntervenciones,
)



def permiso_sirtee(
    permiso
):


    def decorator(view_func):


        @wraps(view_func)
        def wrapper(
            request,
            *args,
            **kwargs
        ):

            validar_permiso(
                permiso,
                request.user
            )


            return view_func(
                request,
                *args,
                **kwargs
            )


        return wrapper


    return decorator





# =====================================================
# ATAJOS
# =====================================================


permiso_mapa = permiso_sirtee(
    PuedeVerMapa
)


permiso_indicadores = permiso_sirtee(
    PuedeVerIndicadores
)


permiso_relevamientos = permiso_sirtee(
    PuedeVerRelevamientos
)


permiso_hallazgos = permiso_sirtee(
    PuedeVerHallazgos
)


permiso_intervenciones = permiso_sirtee(
    PuedeVerIntervenciones
)