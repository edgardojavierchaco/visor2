import django_tables2 as tables
from apps.sirtee.models.relevamientos import Relevamiento


class RelevamientoTable(tables.Table):

    escuela = tables.Column(accessor="escuela.nom_est", verbose_name="Escuela")
    cueanexo = tables.Column(accessor="escuela.cueanexo", verbose_name="Cueanexo")
    region = tables.Column(accessor="escuela.region_loc", verbose_name="Región")
    departamento = tables.Column(accessor="escuela.departamento", verbose_name="Departamento")

    acciones = tables.TemplateColumn(
        template_code="""
        <a href="/sirtee/relevamientos/{{record.id}}/">Ver</a>
        """,
        orderable=False
    )

    class Meta:
        model = Relevamiento
        fields = (
            "id",
            "escuela",
            "cueanexo",
            "estado",
            "tipo_relevamiento",
            "fecha",
        )
        attrs = {"class": "table table-striped table-hover"}