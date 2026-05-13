from django.db.models import CharField, Value
from django.db.models.functions import Cast, Replace

from apps.consultasge.models_padron import CapaUnicaOfertas


def get_cueanexos_usuario(user):

    return (
        CapaUnicaOfertas.objects
        .annotate(
            cuil_limpio=Replace(
                Replace(
                    'resploc_cuitcuil',
                    Value('-'),
                    Value('')
                ),
                Value(' '),
                Value('')
            ),
            cueanexo_str=Cast(
                'cueanexo',
                output_field=CharField()
            )
        )
        .filter(
            cuil_limpio=user.username
        )
        .values_list(
            'cueanexo_str',
            flat=True
        )
    )