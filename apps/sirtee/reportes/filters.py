import django_filters

from apps.sirtee.models.intervenciones import Intervencion



class ReporteIntervencionFilter(
    django_filters.FilterSet
):


    desde = django_filters.DateFilter(
        field_name="fecha_inicio",
        lookup_expr="gte"
    )


    hasta = django_filters.DateFilter(
        field_name="fecha_inicio",
        lookup_expr="lte"
    )


    estado = django_filters.CharFilter(
        field_name="estado__codigo",
        lookup_expr="iexact"
    )


    empresa = django_filters.CharFilter(
        field_name="empresa__razon_social",
        lookup_expr="icontains"
    )


    escuela = django_filters.CharFilter(
        field_name=(
            "hallazgo__relevamiento__cueanexo"
        ),
        lookup_expr="icontains"
    )



    class Meta:

        model = Intervencion

        fields = [
            "estado",
            "empresa",
            "escuela",
        ]