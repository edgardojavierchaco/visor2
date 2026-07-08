import django_filters

from apps.sirtee.models.relevamientos import Relevamiento
from apps.sirtee.models.hallazgos import Hallazgo
from apps.sirtee.models.intervenciones import Intervencion


# --------------------------------------
# RELEVAMIENTO FILTER
# --------------------------------------

class RelevamientoFilter(django_filters.FilterSet):

    estado = django_filters.CharFilter(field_name="estado")
    tipo = django_filters.CharFilter(field_name="tipo_relevamiento")
    escuela = django_filters.CharFilter(field_name="escuela__cueanexo")

    class Meta:
        model = Relevamiento
        fields = ["estado", "tipo", "escuela"]


# --------------------------------------
# HALLAZGO FILTER
# --------------------------------------

class HallazgoFilter(django_filters.FilterSet):

    criticidad = django_filters.CharFilter(field_name="criticidad")
    estado = django_filters.CharFilter(field_name="estado")
    categoria = django_filters.CharFilter(field_name="categoria")

    escuela = django_filters.CharFilter(
        field_name="relevamiento__escuela__cueanexo"
    )

    class Meta:
        model = Hallazgo
        fields = ["criticidad", "estado", "categoria", "escuela"]


# --------------------------------------
# INTERVENCIÓN FILTER
# --------------------------------------

class IntervencionFilter(django_filters.FilterSet):

    estado = django_filters.CharFilter(field_name="estado")
    tipo = django_filters.CharFilter(field_name="tipo")

    escuela = django_filters.CharFilter(
        field_name="hallazgo__relevamiento__escuela__cueanexo"
    )

    class Meta:
        model = Intervencion
        fields = ["estado", "tipo", "escuela"]