from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(str(key), "0.00")  # Convertimos la clave a string y devolvemos "0.00" si no existe

