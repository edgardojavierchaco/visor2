from django import template

register = template.Library()

@register.filter
def get_item(obj, key):
    return getattr(obj, f'p{key}', '')

@register.simple_tag
def sum_items(items, examen):
    try:
        return sum(getattr(examen, f'p{i}', 0) or 0 for i in items)
    except Exception:
        return 0

@register.filter
def dict_get(d, key):
    return d.get(key)