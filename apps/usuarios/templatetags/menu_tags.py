from django import template

register = template.Library()

@register.simple_tag(takes_context=True)
def is_active(context, url_name):
    request = context['request']
    current = getattr(getattr(request, 'resolver_match', None), 'view_name', '')
    return 'active' if current == url_name else ''