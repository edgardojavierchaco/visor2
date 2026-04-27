from django import template

register = template.Library()

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