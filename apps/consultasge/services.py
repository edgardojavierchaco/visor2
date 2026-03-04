from datetime import timedelta
from django.utils import timezone
from .models import Consulta
from .models_padron import CapaUnicaOfertas


def crear_consulta(user, asunto, mensaje, categoria):

    try:
        escuela = CapaUnicaOfertas.objects.get(
            cueanexo=user.username
        )
    except CapaUnicaOfertas.DoesNotExist:
        raise Exception("No se encontró escuela asociada al usuario.")

    sla = categoria.sla_horas if categoria else 48

    consulta = Consulta.objects.create(
        usuario=user,
        cueanexo=user.username,
        escuela=escuela.nom_est,
        region=escuela.region_loc,
        asunto=asunto,
        mensaje=mensaje,
        categoria=categoria,
        estado="abierta",
        fecha_limite=timezone.now() + timedelta(hours=sla)
    )

    return consulta