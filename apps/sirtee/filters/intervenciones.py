from django_filters import rest_framework as filters
from django.utils import timezone

from apps.sirtee.models.intervenciones import Intervencion



class IntervencionFilter(filters.FilterSet):


    # =====================================================
    # CATÁLOGOS
    # =====================================================

    estado = filters.CharFilter(
        field_name="estado__codigo",
        lookup_expr="iexact",
    )


    tipo = filters.CharFilter(
        field_name="tipo__codigo",
        lookup_expr="iexact",
    )


    prioridad = filters.CharFilter(
        field_name="prioridad__codigo",
        lookup_expr="iexact",
    )


    organismo = filters.CharFilter(
        field_name="organismo_responsable__codigo",
        lookup_expr="iexact",
    )


    financiamiento = filters.CharFilter(
        field_name="fuente_financiamiento__codigo",
        lookup_expr="iexact",
    )


    # =====================================================
    # EMPRESA
    # =====================================================

    empresa = filters.NumberFilter(
        field_name="empresa__id",
    )


    empresa_nombre = filters.CharFilter(
        field_name="empresa__razon_social",
        lookup_expr="icontains",
    )


    empresa_cuit = filters.CharFilter(
        field_name="empresa__cuit",
        lookup_expr="icontains",
    )



    # =====================================================
    # RESPONSABLE / EJECUTOR
    # =====================================================

    equipo = filters.CharFilter(
        field_name="equipo_ejecutor",
        lookup_expr="icontains",
    )


    responsable = filters.CharFilter(
        field_name="responsable",
        lookup_expr="icontains",
    )



    # =====================================================
    # ESCUELA
    # =====================================================

    escuela = filters.CharFilter(
        field_name=(
            "hallazgo__relevamiento__cueanexo"
        ),
        lookup_expr="icontains",
    )



    # =====================================================
    # FECHAS
    # =====================================================

    fecha_inicio_desde = filters.DateTimeFilter(
        field_name="fecha_inicio",
        lookup_expr="gte",
    )


    fecha_inicio_hasta = filters.DateTimeFilter(
        field_name="fecha_inicio",
        lookup_expr="lte",
    )


    fecha_fin_desde = filters.DateTimeFilter(
        field_name="fecha_fin",
        lookup_expr="gte",
    )


    fecha_fin_hasta = filters.DateTimeFilter(
        field_name="fecha_fin",
        lookup_expr="lte",
    )


    fecha_estimada = filters.DateFilter(
        field_name="fecha_estimada_fin",
    )



    # =====================================================
    # AVANCE
    # =====================================================

    avance_minimo = filters.NumberFilter(
        field_name="porcentaje_avance",
        lookup_expr="gte",
    )


    avance_maximo = filters.NumberFilter(
        field_name="porcentaje_avance",
        lookup_expr="lte",
    )



    # =====================================================
    # COSTOS
    # =====================================================

    costo_estimado_minimo = filters.NumberFilter(
        field_name="costo_estimado",
        lookup_expr="gte",
    )


    costo_estimado_maximo = filters.NumberFilter(
        field_name="costo_estimado",
        lookup_expr="lte",
    )


    costo_real_minimo = filters.NumberFilter(
        field_name="costo_real",
        lookup_expr="gte",
    )


    costo_real_maximo = filters.NumberFilter(
        field_name="costo_real",
        lookup_expr="lte",
    )



    # =====================================================
    # ESTADO TEMPORAL
    # =====================================================

    atrasadas = filters.BooleanFilter(
        method="filter_atrasadas"
    )


    finalizadas = filters.BooleanFilter(
        method="filter_finalizadas"
    )



    class Meta:

        model = Intervencion


        fields = [

            "estado",

            "tipo",

            "prioridad",

            "organismo",

            "financiamiento",

            "empresa",

            "escuela",

        ]



    # =====================================================
    # MÉTODOS
    # =====================================================

    def filter_atrasadas(
        self,
        queryset,
        name,
        value
    ):

        if value:

            return queryset.filter(

                estado__codigo__in=[

                    "PENDIENTE",

                    "PROGRAMADA",

                    "EN_EJECUCION",

                ],

                fecha_estimada_fin__lt=timezone.now().date(),

            )

        return queryset



    def filter_finalizadas(
        self,
        queryset,
        name,
        value
    ):

        if value:

            return queryset.filter(
                estado__codigo="FINALIZADA"
            )


        return queryset