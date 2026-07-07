from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Permite acceder a un diccionario con una key dinámica en el template.
    Ejemplo: {{ mi_diccionario|get_item:variable_key }}
    """
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return getattr(dictionary, str(key), None)

@register.simple_tag
def query_transform(request, **kwargs):
    """
    Conserva los parámetros GET actuales (como ?page=9) 
    y actualiza/agrega los nuevos que le pasemos.
    """
    updated = request.GET.copy()
    for k, v in kwargs.items():
        if v is not None:
            updated[k] = v
        else:
            updated.pop(k, 0)
    return updated.urlencode()