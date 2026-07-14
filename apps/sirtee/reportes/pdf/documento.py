from io import BytesIO

from reportlab.lib import colors

from reportlab.lib.enums import (
    TA_CENTER,
    TA_RIGHT,
)

from reportlab.lib.styles import getSampleStyleSheet

from reportlab.lib.units import cm

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from apps.sirtee.reportes.pdf.encabezado import (
    EncabezadoMinisterio,
)


class DocumentoPDF:
    """
    Clase base para todos los PDF institucionales del
    módulo SIRTEE.
    """

    titulo = "Reporte"

    autor = "SIRTEE"

    asunto = ""

    def __init__(self):

        self.buffer = BytesIO()

        self.styles = getSampleStyleSheet()

        self.story = []

        self.doc = SimpleDocTemplate(
            self.buffer,
            rightMargin=1.5 * cm,
            leftMargin=1.5 * cm,
            topMargin=2.3 * cm,
            bottomMargin=2 * cm,
        )

        self.doc.title = self.titulo
        self.doc.author = self.autor
        self.doc.subject = self.asunto

    # ==========================================================
    # Construcción
    # ==========================================================

    def build(self):

        self.doc.build(
            self.story,
            onFirstPage=EncabezadoMinisterio(),
            onLaterPages=EncabezadoMinisterio(),
        )

        pdf = self.buffer.getvalue()

        self.buffer.close()

        return pdf

    # ==========================================================
    # Texto
    # ==========================================================

    def titulo_principal(self, texto):

        estilo = self.styles["Heading1"]

        estilo.alignment = TA_CENTER

        self.story.append(
            Paragraph(texto, estilo)
        )

        self.story.append(
            Spacer(1, 0.5 * cm)
        )

    def subtitulo(self, texto):

        estilo = self.styles["Heading2"]

        self.story.append(
            Paragraph(texto, estilo)
        )

        self.story.append(
            Spacer(1, 0.25 * cm)
        )

    def texto(self, texto):

        self.story.append(
            Paragraph(texto, self.styles["BodyText"])
        )

        self.story.append(
            Spacer(1, 0.25 * cm)
        )

    # ==========================================================
    # KPIs
    # ==========================================================

    def agregar_kpis(self, datos):

        filas = []

        for nombre, valor in datos:

            filas.append([
                Paragraph(f"<b>{nombre}</b>", self.styles["BodyText"]),
                Paragraph(str(valor), self.styles["BodyText"]),
            ])

        tabla = Table(
            filas,
            colWidths=[
                10 * cm,
                5 * cm,
            ],
        )

        tabla.setStyle(

            TableStyle(

                [

                    ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),

                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8F1FB")),

                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),

                    ("TOPPADDING", (0, 0), (-1, -1), 7),

                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

                ]

            )

        )

        self.story.append(tabla)

        self.story.append(
            Spacer(1, 0.5 * cm)
        )

    # ==========================================================
    # Tabla genérica
    # ==========================================================

    def agregar_tabla(
        self,
        encabezados,
        filas,
        widths=None,
    ):

        datos = [encabezados]

        datos.extend(filas)

        tabla = Table(
            datos,
            colWidths=widths,
            repeatRows=1,
        )

        tabla.setStyle(

            TableStyle(

                [

                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0D6EFD")),

                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),

                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),

                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),

                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),

                    ("TOPPADDING", (0, 0), (-1, -1), 6),

                    ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),

                    ("ROWBACKGROUNDS",
                     (0, 1),
                     (-1, -1),
                     [
                         colors.white,
                         colors.HexColor("#F8F9FA"),
                     ]),

                ]

            )

        )

        self.story.append(tabla)

        self.story.append(
            Spacer(1, 0.5 * cm)
        )

    # ==========================================================
    # Línea divisoria
    # ==========================================================

    def separador(self):

        tabla = Table(
            [[""]],
            colWidths=[18 * cm],
            rowHeights=[0.05 * cm],
        )

        tabla.setStyle(

            TableStyle(

                [

                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, -1),
                        colors.HexColor("#D0D0D0"),
                    )

                ]

            )

        )

        self.story.append(tabla)

        self.story.append(
            Spacer(1, 0.4 * cm)
        )

    # ==========================================================
    # Firma
    # ==========================================================

    def firma(self, texto="Sistema SIRTEE"):

        estilo = self.styles["Normal"]

        estilo.alignment = TA_RIGHT

        self.story.append(
            Spacer(1, 0.8 * cm)
        )

        self.story.append(
            Paragraph(
                "<b>%s</b>" % texto,
                estilo,
            )
        )