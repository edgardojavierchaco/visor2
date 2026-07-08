import django_filters

from apps.sirtee.models.empresas import Empresa



class EmpresaFilter(
    django_filters.FilterSet
):


    razon_social = django_filters.CharFilter(
        lookup_expr="icontains",
        label="Razón social"
    )


    cuit = django_filters.CharFilter(
        lookup_expr="icontains",
        label="CUIT"
    )


    localidad = django_filters.CharFilter(
        lookup_expr="icontains",
        label="Localidad"
    )


    tipo = django_filters.CharFilter(
        lookup_expr="iexact"
    )


    activa = django_filters.BooleanFilter()



    class Meta:

        model = Empresa


        fields = [

            "razon_social",

            "cuit",

            "localidad",

            "tipo",

            "activa",

        ]