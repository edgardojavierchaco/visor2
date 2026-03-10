# apps/consultasge/templatetags/consultas_extras.py
from django import template
import os
from apps.consultasge.utils import estado_sla, progreso_sla, obtener_turno_gestor

register = template.Library()

@register.filter
def estado_sla_filter(consulta):
    """Devuelve el estado del SLA de la consulta (vencido, en término, finalizada)."""
    return estado_sla(consulta)

@register.filter(name='progreso_sla_filter')
def progreso_sla_filter(consulta, user):
    """Devuelve el progreso del SLA para barra de progreso."""
    return progreso_sla(consulta, user)

@register.filter
def turno_gestor(user):
    """Devuelve el primer turno activo que encuentre para mostrar en el perfil/header."""
    return obtener_turno_gestor(user) # Aquí no pasamos región, solo para info general

@register.filter
def split_path(value):
    return os.path.basename(value)

@register.filter
def get_item(dictionary, key):
    """Permite acceder a diccionarios en templates"""
    return dictionary.get(key, 0)