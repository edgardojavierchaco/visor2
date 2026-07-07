# apps/especial/templatetags/especial_filters.py
from django import template

register = template.Library()

@register.filter
def get_item(obj, key):
    """Accede a un diccionario u objeto por clave/atributo dinámicamente."""
    if isinstance(obj, dict):
        return obj.get(key, "")
    return getattr(obj, key, "")