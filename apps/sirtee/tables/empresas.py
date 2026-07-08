import django_tables2 as tables

from apps.sirtee.models.empresas import Empresa



class EmpresaTable(tables.Table):


    intervenciones = tables.Column(
        empty_values=(),
        verbose_name="Intervenciones"
    )


    acciones = tables.TemplateColumn(

        template_code="""

        <a 
        href="{% url 'sirtee:empresas-detail' record.pk %}"
        class="btn btn-sm btn-primary">

        Ver

        </a>

        <a 
        href="{% url 'sirtee:empresas-update' record.pk %}"
        class="btn btn-sm btn-warning">

        Editar

        </a>

        """,

        orderable=False,
        verbose_name="Acciones"

    )



    class Meta:

        model = Empresa


        fields = (

            "razon_social",

            "nombre_fantasia",

            "cuit",

            "tipo",

            "telefono",

            "responsable",

            "activa",

        )


        attrs = {

            "class": "table table-striped table-hover"

        }



    def render_intervenciones(
        self,
        record
    ):

        return record.intervencion_set.count()