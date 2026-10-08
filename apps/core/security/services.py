import re

from django.db.models import (
    Func,
    F,
    Value,
)

from apps.consultasge.models_padron import (
    CapaUnicaOfertas,
)

from apps.core.security.padron_access import (
    get_cueanexos_by_cuil,
)


def get_ofertas_usuario(user):
    """
    QuerySet completo de ofertas.

    Se mantiene por compatibilidad con código existente que
    necesita objetos CapaUnicaOfertas.

    NO usar esta función solamente para averiguar CUEANEXOS.
    """

    if not user.is_authenticated:
        return CapaUnicaOfertas.objects.none()

    usuario_limpio = re.sub(
        r"\D",
        "",
        str(user.username),
    )

    return (
        CapaUnicaOfertas.objects
        .annotate(
            cuit_limpio=Func(
                F("resploc_cuitcuil"),
                Value(r"\D"),
                Value(""),
                Value("g"),
                function="REGEXP_REPLACE",
            )
        )
        .filter(
            cuit_limpio=usuario_limpio
        )
        .only("cueanexo")
        .distinct()
        .order_by("cueanexo")
    )


def get_cueanexos_usuario(user):
    """
    Retorna set de CUEANEXOS autorizados.

    Camino optimizado:
        CUIL
        -> responsable
        -> localizacion
        -> oferta_local activa
        -> establecimiento

    Resultado cacheado en Redis.
    """

    if not user.is_authenticated:
        return set()

    usuario_limpio = re.sub(
        r"\D",
        "",
        str(user.username),
    )

    if len(usuario_limpio) != 11:
        return set()

    return set(
        get_cueanexos_by_cuil(
            usuario_limpio
        )
    )