import django_tables2 as tables


from apps.sirtee.models.hallazgos import Hallazgo



class HallazgoTable(
    tables.Table
):


    titulo = tables.Column(
        verbose_name="Título"
    )


    criticidad = tables.Column(
        accessor="criticidad.nombre",
        verbose_name="Criticidad"
    )


    estado = tables.Column(
        accessor="estado.nombre",
        verbose_name="Estado"
    )


    area = tables.Column(
        accessor="area_afectada.nombre",
        verbose_name="Área"
    )


    tipo = tables.Column(
        accessor="tipo_hallazgo.nombre",
        verbose_name="Tipo"
    )



    acciones = tables.TemplateColumn(

        template_name=
        "sirtee/hallazgos/_acciones.html",

        verbose_name=""

    )


    class Meta:

        model = Hallazgo


        fields = [

            "titulo",

            "tipo",

            "area",

            "criticidad",

            "estado",

        ]


        attrs = {

            "class":
            "table table-striped table-hover"

        }