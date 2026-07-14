import django_tables2 as tables
from apps.sirtee.models.intervenciones import Intervencion


class IntervencionTable(tables.Table):

    escuela = tables.Column(
        accessor="hallazgo.relevamiento.escuela.nom_est",
        verbose_name="Escuela"
    )

    empresa = tables.Column(
        accessor="empresa.nombre",
        verbose_name="Empresa"
    )

    estado = tables.Column(verbose_name="Estado")

    avance = tables.Column(verbose_name="% Avance")

    acciones = tables.TemplateColumn(
        template_code="""
        <a href="/sirtee/intervenciones/{{record.id}}/">Ver</a>
        """,
        orderable=False
    )

    class Meta:
        model = Intervencion
        fields = (
            "id",
            "tipo",
            "estado",
            "avance",
            "fecha_inicio",
            "fecha_estimada_fin",
        )
        attrs = {"class": "table table-striped"}