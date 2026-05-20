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
    ).only("cueanexo").order_by("cueanexo")