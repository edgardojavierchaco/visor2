import re

from django.db.models import (
    Func,
    F,
    Value
)

from apps.consultasge.models_padron import (
    CapaUnicaOfertas
)


def get_ofertas_usuario(user):
    """
    Queryset de ofertas autorizadas
    para usuario autenticado.

    Fuente oficial ministerial:
    CapaUnicaOfertas
    """

    if not user.is_authenticated:
        return (
            CapaUnicaOfertas.objects.none()
        )

    usuario_limpio = re.sub(
        r'\D',
        '',
        str(user.username)
    )

    return (
        CapaUnicaOfertas.objects
        .annotate(
            cuit_limpio=Func(
                F('resploc_cuitcuil'),
                Value(r'\D'),
                Value(''),
                Value('g'),
                function='REGEXP_REPLACE'
            )
        )
        .filter(
            cuit_limpio=usuario_limpio
        )
        .only('cueanexo')
        .distinct()
        .order_by('cueanexo')
    )


def get_cueanexos_usuario(user):
    """
    Retorna set de cueanexos
    autorizados.
    """

    return {
        str(c).strip()
        for c in get_ofertas_usuario(user)
        .values_list(
            'cueanexo',
            flat=True
        )
        if c
    }