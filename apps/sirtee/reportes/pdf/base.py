from io import BytesIO
from pathlib import Path
from decimal import Decimal

from django.conf import settings

from reportlab.lib import colors
from reportlab.lib.enums import (
    TA_CENTER,
    TA_LEFT,
    TA_RIGHT,
)

from reportlab.lib.pagesizes import (
    A4,
    landscape,
)

from reportlab.lib.styles import (
    ParagraphStyle,
    getSampleStyleSheet,
)

from reportlab.lib.units import cm

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
)


# ==========================================================
# COLORES INSTITUCIONALES
# ==========================================================

COLOR_PRIMARIO = colors.HexColor("#0d6efd")
COLOR_SECUNDARIO = colors.HexColor("#198754")
COLOR_INFO = colors.HexColor("#0dcaf0")
COLOR_WARNING = colors.HexColor("#ffc107")
COLOR_DANGER = colors.HexColor("#dc3545")

COLOR_HEADER = colors.HexColor("#1F4E79")

COLOR_GRIS = colors.HexColor("#F5F5F5")

COLOR_BORDE = colors.HexColor("#CCCCCC")


# ==========================================================
# ESTILOS
# ==========================================================

_styles = getSampleStyleSheet()


STYLE_TITULO = ParagraphStyle(

    "Titulo",

    parent=_styles["Heading1"],

    fontName="Helvetica-Bold",

    fontSize=20,

    leading=24,

    textColor=COLOR_HEADER,

    alignment=TA_CENTER,

    spaceAfter=18,

)


STYLE_SUBTITULO = ParagraphStyle(

    "Subtitulo",

    parent=_styles["Heading2"],

    fontName="Helvetica-Bold",

    fontSize=13,

    leading=16,

    textColor=COLOR_PRIMARIO,

    spaceBefore=12,

    spaceAfter=8,

)


STYLE_NORMAL = ParagraphStyle(

    "Normal",

    parent=_styles["BodyText"],

    fontName="Helvetica",

    fontSize=9,

    leading=13,

)


STYLE_LABEL = ParagraphStyle(

    "Label",

    parent=STYLE_NORMAL,

    fontName="Helvetica-Bold",

)


STYLE_CENTER = ParagraphStyle(

    "Center",

    parent=STYLE_NORMAL,

    alignment=TA_CENTER,

)


STYLE_RIGHT = ParagraphStyle(

    "Right",

    parent=STYLE_NORMAL,

    alignment=TA_RIGHT,

)


STYLE_SMALL = ParagraphStyle(

    "Small",

    parent=STYLE_NORMAL,

    fontSize=8,

)


# ==========================================================
# FORMATEADORES
# ==========================================================

def moneda(valor):

    if valor is None:

        return "$ 0"

    if isinstance(valor, Decimal):

        valor = float(valor)

    return f"$ {valor:,.2f}"


def fecha(valor):

    if not valor:

        return "-"

    return valor.strftime("%d/%m/%Y")


def texto(valor):

    return valor or "-"


# ==========================================================
# CLASE BASE
# ==========================================================

class BasePDF:

    titulo = "SIRTEE"

    subtitulo = ""

    orientacion = "portrait"

    filename = "reporte.pdf"

    def __init__(self):

        self.buffer = BytesIO()

        self.story = []

        self.doc = None


    # ------------------------------------------------------

    def build(self):

        pagesize = A4

        if self.orientacion == "landscape":

            pagesize = landscape(A4)

        self.doc = SimpleDocTemplate(

            self.buffer,

            pagesize=pagesize,

            leftMargin=1.5 * cm,

            rightMargin=1.5 * cm,

            topMargin=2 * cm,

            bottomMargin=2 * cm,

        )

        self.doc.build(

            self.story,

            onFirstPage=self._draw_header_footer,

            onLaterPages=self._draw_header_footer,

        )

        pdf = self.buffer.getvalue()

        self.buffer.close()

        return pdf


    # ------------------------------------------------------

    def _draw_header_footer(

        self,

        canvas,

        document,

    ):

        canvas.saveState()

        width, height = document.pagesize

        logo = (

            Path(settings.BASE_DIR)

            / "static"

            / "img"

            / "logo.png"

        )

        if logo.exists():

            canvas.drawImage(

                str(logo),

                1.5 * cm,

                height - 2.2 * cm,

                width=1.8 * cm,

                height=1.8 * cm,

                preserveAspectRatio=True,

                mask="auto",

            )

        canvas.setFont(

            "Helvetica-Bold",

            16,

        )

        canvas.drawString(

            4 * cm,

            height - 1.3 * cm,

            "SIRTEE",

        )

        canvas.setFont(

            "Helvetica",

            9,

        )

        canvas.drawString(

            4 * cm,

            height - 1.8 * cm,

            "Sistema Integral de Relevamiento Técnico de Establecimientos Educativos",

        )

        canvas.line(

            1.5 * cm,

            height - 2.4 * cm,

            width - 1.5 * cm,

            height - 2.4 * cm,

        )

        canvas.setFont(

            "Helvetica",

            8,

        )

        canvas.drawString(

            1.5 * cm,

            1 * cm,

            "Ministerio de Educación - Provincia del Chaco",

        )

        canvas.drawRightString(

            width - 1.5 * cm,

            1 * cm,

            f"Página {document.page}",

        )

        canvas.restoreState()


    # ------------------------------------------------------

    def add_title(

        self,

        titulo=None,

        subtitulo=None,

    ):

        self.story.append(

            Paragraph(

                titulo or self.titulo,

                STYLE_TITULO,

            )

        )

        if subtitulo:

            self.story.append(

                Paragraph(

                    subtitulo,

                    STYLE_CENTER,

                )

            )

        self.story.append(

            Spacer(

                1,

                0.4 * cm,

            )

        )


    # ------------------------------------------------------

    def add_subtitle(

        self,

        texto,

    ):

        self.story.append(

            Paragraph(

                texto,

                STYLE_SUBTITULO,

            )

        )


    # ------------------------------------------------------

    def add_paragraph(

        self,

        texto,

    ):

        self.story.append(

            Paragraph(

                texto,

                STYLE_NORMAL,

            )

        )

        self.story.append(

            Spacer(

                1,

                0.2 * cm,

            )

        )