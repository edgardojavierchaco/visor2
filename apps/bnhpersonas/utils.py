import re
from django.db.models import Func, F, Value
from apps.consultasge.models_padron import CapaUnicaOfertas

def get_cueanexos_usuario(user):
    usuario_limpio = re.sub(r'\D', '', user.username)

    return CapaUnicaOfertas.objects.annotate(
        cuit_limpio=Func(
            F('resploc_cuitcuil'),
            Value('-'),
            Value(''),
            function='REPLACE'
        )
    ).filter(
        cuit_limpio=usuario_limpio
    ).values_list('cueanexo', flat=True)