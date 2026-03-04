from django import template
from apps.consultasge.utils import estado_sla, progreso_sla

register = template.Library()

@register.filter
def estado_sla_filter(consulta):
    return estado_sla(consulta)

@register.filter
def progreso_sla_filter(consulta, user):
    return progreso_sla(consulta, user)