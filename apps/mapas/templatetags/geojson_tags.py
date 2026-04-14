from django import template
import json

register = template.Library()

@register.filter
def geojson(value):
    """Convertir un objeto Geometry a GeoJSON."""
    return json.dumps(value.geojson)
