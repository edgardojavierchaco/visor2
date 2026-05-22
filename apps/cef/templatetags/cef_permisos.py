from django import template

from apps.cef.permisos import (
    usuario_puede_entrar_cef_configuracion,
    usuario_puede_entrar_cef_visualizacion,
)


register = template.Library()


@register.simple_tag
def puede_ver_visualizacion_cef(user):
    return usuario_puede_entrar_cef_visualizacion(user)


@register.simple_tag
def puede_ver_configuracion_cef(user):
    return usuario_puede_entrar_cef_configuracion(user)
