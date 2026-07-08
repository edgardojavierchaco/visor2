import django_filters

from apps.sirtee.models.relevamientos import Relevamiento


class RelevamientoFilter(
    django_filters.FilterSet
):


    # ----------------------------------
    # CUEANEXO
    # ----------------------------------

    cueanexo = django_filters.CharFilter(
        field_name="cueanexo",
        lookup_expr="icontains",
        label="CUEANEXO"
    )


    # ----------------------------------
    # ESTADO
    # ----------------------------------

    estado = django_filters.ChoiceFilter(
        field_name="estado",
        choices=Relevamiento._meta.get_field(
            "estado"
        ).choices,
        label="Estado"
    )


    # ----------------------------------
    # TIPO
    # ----------------------------------

    tipo = django_filters.ChoiceFilter(
        field_name="tipo_relevamiento",
        choices=Relevamiento._meta.get_field(
            "tipo_relevamiento"
        ).choices,
        label="Tipo"
    )


    # ----------------------------------
    # FECHAS
    # ----------------------------------

    fecha_desde = django_filters.DateFilter(
        field_name="fecha",
        lookup_expr="gte",
        label="Desde"
    )


    fecha_hasta = django_filters.DateFilter(
        field_name="fecha",
        lookup_expr="lte",
        label="Hasta"
    )


    # ----------------------------------
    # FINALIZADOS
    # ----------------------------------

    finalizado = django_filters.BooleanFilter(
        field_name="finalizado",
        label="Finalizado"
    )


    # ----------------------------------
    # CON HALLAZGOS
    # ----------------------------------

    con_hallazgos = django_filters.BooleanFilter(
        method="filter_con_hallazgos",
        label="Con hallazgos"
    )



    class Meta:

        model = Relevamiento

        fields = [
            "cueanexo",
            "estado",
            "tipo",
            "fecha_desde",
            "fecha_hasta",
            "finalizado",
            "con_hallazgos",
        ]



    def filter_con_hallazgos(
        self,
        queryset,
        name,
        value
    ):

        if value:

            return (
                queryset
                .filter(
                    hallazgos__isnull=False
                )
                .distinct()
            )


        return queryset