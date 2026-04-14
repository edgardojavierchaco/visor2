from django.utils import timezone


def sla_vencido(consulta):

    if consulta.fecha_limite is None:
        return False

    return timezone.now() > consulta.fecha_limite