from django import template

register = template.Library()

@register.filter(name='checkbox')
def checkbox(value):
    if value:
        return '<input type="checkbox" checked disabled>'
    else:
        return '<input type="checkbox" disabled>'

@register.filter(name='add_class')
def add_class(field, css_class):
    return field.as_widget(attrs={"class": css_class})

@register.filter
def widget_class(field):
    return field.field.widget.__class__.__name__