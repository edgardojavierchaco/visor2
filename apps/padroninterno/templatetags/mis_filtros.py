from django import template

register = template.Library()


# Tag usado por los templates para conservar filtros/paginacion en links.
# Recibe nuevos parametros y devuelve una querystring actualizada.
@register.simple_tag
def query_transform(request, **kwargs):
    """
    Conserva los parámetros GET actuales (como ?page=9) 
    y actualiza/agrega los nuevos que le pasemos.
    """
    updated = request.GET.copy()
    for k, v in kwargs.items():
        # Valor no nulo: se agrega o reemplaza el parametro.
        if v is not None:
            updated[k] = v
        # Valor nulo: se elimina el parametro de la URL.
        else:
            updated.pop(k, 0)
    return updated.urlencode()
