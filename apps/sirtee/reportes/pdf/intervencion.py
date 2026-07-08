from django.utils import timezone

from apps.sirtee.models.intervenciones import Intervencion
from apps.sirtee.reportes.pdf.documento import DocumentoPDF


class ReporteIntervencionPDF(DocumentoPDF):
    """
    Reporte institucional de una intervención.

    Incluye:

    • Ficha técnica
    • Cronograma
    • Costos
    • Responsable
    • Empresa
    • Fotografías
    • Observaciones
    """

    titulo = "Ficha Técnica de Intervención"

    autor = "SIRTEE"

    asunto = "Infraestructura Escolar"

    def __init__(self, intervencion):

        super().__init__()

        if isinstance(intervencion, Intervencion):

            self.intervencion = intervencion

        else:

            self.intervencion = (
                Intervencion.objects
                .select_related(
                    "hallazgo",
                    "hallazgo__relevamiento",
                    "empresa",
                    "tipo",
                    "estado",
                    "prioridad",
                    "organismo_responsable",
                    "fuente_financiamiento",
                )
                .get(pk=intervencion)
            )

    # =====================================================
    # GENERAR PDF
    # =====================================================

    def generar(self):

        self.titulo_principal(
            "FICHA TÉCNICA DE INTERVENCIÓN"
        )

        self.texto(
            f"<b>Fecha de emisión:</b> "
            f"{timezone.now():%d/%m/%Y %H:%M}"
        )

        self.separador()

        self.ficha_tecnica()

        self.separador()

        self.cronograma()

        self.separador()

        self.costos()

        self.separador()

        self.responsables()

        self.separador()

        self.observaciones()

        self.separador()

        self.fotografias()

        self.firma()

        return self.build()

    # =====================================================
    # FICHA TÉCNICA
    # =====================================================

    def ficha_tecnica(self):

        self.subtitulo(
            "Ficha técnica"
        )

        escuela = getattr(
            self.intervencion.hallazgo.relevamiento,
            "cueanexo",
            "-"
        )

        self.agregar_tabla(

            [

                "Campo",
                "Valor",

            ],

            [

                [

                    "Escuela",
                    escuela,

                ],

                [

                    "Hallazgo",
                    self.intervencion.hallazgo.titulo,

                ],

                [

                    "Intervención",
                    self.intervencion.titulo,

                ],

                [

                    "Tipo",
                    self.intervencion.tipo.nombre
                    if self.intervencion.tipo
                    else "-",

                ],

                [

                    "Estado",
                    self.intervencion.estado.nombre
                    if self.intervencion.estado
                    else "-",

                ],

                [

                    "Prioridad",
                    self.intervencion.prioridad.nombre
                    if self.intervencion.prioridad
                    else "-",

                ],

                [

                    "Avance",
                    f"{self.intervencion.porcentaje_avance}%",

                ],

            ],

            widths=[
                5 * 72 / 2.54,
                12 * 72 / 2.54,
            ],

        )

        self.texto(
            "<b>Descripción:</b><br/>"
            f"{self.intervencion.descripcion}"
        )

    # =====================================================
    # CRONOGRAMA
    # =====================================================

    def cronograma(self):

        self.subtitulo(
            "Cronograma"
        )

        self.agregar_tabla(

            [

                "Concepto",
                "Fecha",

            ],

            [

                [

                    "Inicio",

                    self.intervencion.fecha_inicio.strftime("%d/%m/%Y")
                    if self.intervencion.fecha_inicio
                    else "-",

                ],

                [

                    "Finalización",

                    self.intervencion.fecha_fin.strftime("%d/%m/%Y")
                    if self.intervencion.fecha_fin
                    else "-",

                ],

                [

                    "Fecha prevista",

                    self.intervencion.fecha_estimada_fin.strftime("%d/%m/%Y")
                    if self.intervencion.fecha_estimada_fin
                    else "-",

                ],

            ],

        )

    # =====================================================
    # COSTOS
    # =====================================================

    def costos(self):

        self.subtitulo(
            "Información económica"
        )

        estimado = (
            self.intervencion.costo_estimado
            or 0
        )

        real = (
            self.intervencion.costo_real
            or 0
        )

        diferencia = real - estimado

        self.agregar_kpis(

            [

                (

                    "Costo estimado",

                    f"${estimado:,.2f}"

                ),

                (

                    "Costo real",

                    f"${real:,.2f}"

                ),

                (

                    "Diferencia",

                    f"${diferencia:,.2f}"

                ),

            ]

        )

    # =====================================================
    # RESPONSABLES
    # =====================================================

    def responsables(self):

        self.subtitulo(
            "Responsables"
        )

        empresa = "-"

        if self.intervencion.empresa:

            empresa = (
                self.intervencion
                .empresa
                .razon_social
            )

        organismo = "-"

        if self.intervencion.organismo_responsable:

            organismo = (
                self.intervencion
                .organismo_responsable
                .nombre
            )

        financiamiento = "-"

        if self.intervencion.fuente_financiamiento:

            financiamiento = (
                self.intervencion
                .fuente_financiamiento
                .nombre
            )

        self.agregar_tabla(

            [

                "Campo",
                "Valor",

            ],

            [

                [

                    "Responsable",

                    self.intervencion.responsable
                    or "-",

                ],

                [

                    "Empresa",

                    empresa,

                ],

                [

                    "Organismo",

                    organismo,

                ],

                [

                    "Financiamiento",

                    financiamiento,

                ],

            ],

        )

    # =====================================================
    # OBSERVACIONES
    # =====================================================

    def observaciones(self):

        self.subtitulo(
            "Observaciones"
        )

        texto = (
            self.intervencion.observaciones
            or
            "No existen observaciones registradas."
        )

        self.texto(texto)

    # =====================================================
    # FOTOGRAFÍAS
    # =====================================================

    def fotografias(self):

        self.subtitulo(
            "Registro fotográfico"
        )

        fotos = []

        if hasattr(
            self.intervencion,
            "fotografias",
        ):

            fotos = list(
                self.intervencion
                .fotografias
                .all()
            )

        if not fotos:

            self.texto(
                "No existen fotografías asociadas."
            )

            return

        self.texto(
            f"Cantidad de fotografías: {len(fotos)}"
        )

        self.texto(
            "La incorporación automática de imágenes "
            "en el PDF se realizará utilizando "
            "ReportLab Image en la siguiente fase."
        )