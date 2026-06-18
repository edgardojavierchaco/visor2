import re
from django.db.models import Func, F, Value
from apps.consultasge.models_padron import CapaUnicaOfertas

def get_ofertas_usuario(user):
    usuario_limpio = re.sub(r'\D', '', user.username)

    return CapaUnicaOfertas.objects.annotate(
        cuit_limpio=Func(
            F('resploc_cuitcuil'),
            Value(r'\D'),   # todo lo que NO sea número
            Value(''),
            Value('g'),
            function='REGEXP_REPLACE'
        )
    ).filter(
        cuit_limpio=usuario_limpio
    ).only("cueanexo").order_by("cueanexo").distinct()


from django.db.models import (
    Func,
    F,
    Value,
    CharField
)

from django.db.models.functions import Cast

from apps.consultasge.models_padron import (
    CapaUnicaOfertas
)

import re


def get_cueanexos_usuario(user):

    usuario_limpio = re.sub(
        r"\D",
        "",
        user.username
    )

    return (

        CapaUnicaOfertas.objects

        .annotate(
            cuit_limpio=Func(
                F("resploc_cuitcuil"),
                Value(r"\D"),
                Value(""),
                Value("g"),
                function="REGEXP_REPLACE"
            ),

            cueanexo_str=Cast(
                "cueanexo",
                output_field=CharField()
            )
        )

        .filter(
            cuit_limpio=usuario_limpio
        )

        .values_list(
            "cueanexo_str",
            flat=True
        )
    )