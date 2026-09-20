from django import template

from apps.bnhpersonas.monitoring.access import can_monitor, resolve_scope

register = template.Library()


@register.simple_tag
def bnh_can_monitor(user):
    return can_monitor(user)


@register.simple_tag
def bnh_monitor_scope(user):
    return resolve_scope(user).label
