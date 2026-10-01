import json
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

import qrcode
from qrcode.constants import ERROR_CORRECT_M

from django.contrib.staticfiles import finders

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


NAVY = colors.HexColor("#173954")
BLUE = colors.HexColor("#14547E")
PALE_BLUE = colors.HexColor("#EAF2F8")
GRID = colors.HexColor("#BFCED9")
TEXT = colors.HexColor("#20384D")
MUTED = colors.HexColor("#607789")
WHITE = colors.white


def _fecha(value):
    if not value:
        return "—"

    return value.strftime(
        "%d/%m/%Y"
    )


def _texto(
    value,
    default="—",
):
    if value is None:
        return default

    value = str(
        value
    ).strip()

    return value or default


def _html(
    value,
    default="—",
):
    return escape(
        _texto(
            value,
            default,
        )
    )


def _numero(value):

    if value in (
        None,
        "",
    ):
        return "—"

    try:
        dec = Decimal(
            str(value)
        )

    except Exception:
        return str(
            value
        )

    if dec == dec.to_integral():
        return str(
            int(dec)
        )

    return (
        format(
            dec.normalize(),
            "f",
        )
        .replace(
            ".",
            ",",
        )
    )


# ============================================================
# LOGO PROVINCIA
# ============================================================

def _logo_provincia():

    logo_path = finders.find(
        "img/chaco.png"
    )

    if not logo_path:
        return None

    if isinstance(
        logo_path,
        (
            list,
            tuple,
        ),
    ):
        logo_path = (
            logo_path[0]
            if logo_path
            else None
        )

    if not logo_path:
        return None

    path = Path(
        logo_path
    )

    if not path.exists():
        return None

    try:

        iw, ih = ImageReader(
            str(path)
        ).getSize()

        width = 30 * mm

        height = (
            width
            *
            (
                ih
                /
                iw
            )
        )

        if height > 22 * mm:

            height = 22 * mm

            width = (
                height
                *
                (
                    iw
                    /
                    ih
                )
            )

        return Image(
            str(path),
            width=width,
            height=height,
        )

    except Exception:

        return None


# ============================================================
# DATOS DE SERVICIOS
# ============================================================

def _espacios_actividad(
    actividad,
):

    valores = []


    espacio_curricular = getattr(
        actividad,
        "espacio_curricular",
        None,
    )

    if espacio_curricular:

        nombre = (
            getattr(
                espacio_curricular,
                "nombre",
                None,
            )
            or str(
                espacio_curricular
            )
        )

        nombre = str(
            nombre or ""
        ).strip()

        if nombre:
            valores.append(
                nombre
            )


    espacio_historico = getattr(
        actividad,
        "espacios",
        None,
    )

    if espacio_historico:

        nombre = (
            getattr(
                espacio_historico,
                "descrip_titulo",
                None,
            )
            or str(
                espacio_historico
            )
        )

        nombre = str(
            nombre or ""
        ).strip()

        if (
            nombre
            and nombre not in valores
        ):
            valores.append(
                nombre
            )


    return (
        " / ".join(
            valores
        )
        if valores
        else "—"
    )


def _cargo_actividad(
    actividad,
):

    ceic = getattr(
        actividad,
        "ceic",
        None,
    )

    if not ceic:
        return "—"

    return _texto(
        getattr(
            ceic,
            "descripcion",
            None,
        )
        or str(
            ceic
        )
    )


def _situacion_revista(
    actividad,
):

    situacion = getattr(
        actividad,
        "sit_revista",
        None,
    )

    if not situacion:
        return "—"

    return _texto(
        getattr(
            situacion,
            "descrip_sitrev",
            None,
        )
        or str(
            situacion
        )
    )


def _tipo_designacion(
    actividad,
):

    tipo = getattr(
        actividad,
        "t_designacion",
        None,
    )

    if not tipo:
        return "—"

    return _texto(
        getattr(
            tipo,
            "desigfunc_descripcion",
            None,
        )
        or str(
            tipo
        )
    )


def _grado(
    actividad,
):

    obj = getattr(
        actividad,
        "grado_anio",
        None,
    )

    if not obj:
        return "—"

    return _texto(
        getattr(
            obj,
            "nombre_grado_anio",
            None,
        )
        or str(
            obj
        )
    )


def _seccion(
    actividad,
):

    obj = getattr(
        actividad,
        "secciones",
        None,
    )

    if not obj:
        return "—"

    return _texto(
        getattr(
            obj,
            "nombre_seccion",
            None,
        )
        or str(
            obj
        )
    )


# ============================================================
# QR
# ============================================================

def construir_payload_qr(
    *,
    cueanexo,
    nom_est,
    persona,
):

    return {

        "cueanexo":
            str(
                cueanexo
                or ""
            ),

        "nom_est":
            str(
                nom_est
                or ""
            ),

        "cuil":
            str(
                getattr(
                    persona,
                    "cuil",
                    "",
                )
                or ""
            ),

        "nombre":
            str(
                getattr(
                    persona,
                    "nombre",
                    "",
                )
                or ""
            ),

        "apellido":
            str(
                getattr(
                    persona,
                    "apellido",
                    "",
                )
                or ""
            ),
    }


def _qr_image(
    payload,
    size_mm=38,
):

    contenido = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(
            ",",
            ":",
        ),
        sort_keys=True,
    )


    qr = qrcode.QRCode(

        version=None,

        error_correction=
            ERROR_CORRECT_M,

        box_size=8,

        border=2,
    )


    qr.add_data(
        contenido
    )


    qr.make(
        fit=True
    )


    image = qr.make_image(
        fill_color="black",
        back_color="white",
    )


    buffer = BytesIO()


    image.save(
        buffer,
        format="PNG",
    )


    buffer.seek(
        0
    )


    return Image(
        buffer,
        width=size_mm * mm,
        height=size_mm * mm,
    )


# ============================================================
# GENERADOR PDF
# ============================================================

def generar_constancia_servicio_pdf(
    *,
    persona,
    cueanexo,
    nom_est,
    actividades,
    fecha_emision,
):

    actividades = list(
        actividades
    )


    buffer = BytesIO()


    doc = SimpleDocTemplate(

        buffer,

        pagesize=A4,

        rightMargin=
            12 * mm,

        leftMargin=
            12 * mm,

        topMargin=
            10 * mm,

        bottomMargin=
            11 * mm,

        title=
            "Constancia de Servicio BNH",

        author=
            "Base Nacional Homologada (BNH)",
    )


    styles = getSampleStyleSheet()


    # ========================================================
    # ESTILOS
    # ========================================================

    style_header = ParagraphStyle(

        "Header",

        parent=
            styles["Normal"],

        fontName=
            "Helvetica-Bold",

        fontSize=
            9.2,

        leading=
            11.5,

        textColor=
            NAVY,

        alignment=
            TA_LEFT,
    )


    style_header_right = ParagraphStyle(

        "HeaderRight",

        parent=
            styles["Normal"],

        fontName=
            "Helvetica-Bold",

        fontSize=
            10.2,

        leading=
            12.5,

        textColor=
            NAVY,

        alignment=
            TA_LEFT,
    )


    style_title = ParagraphStyle(

        "TitleBNH",

        parent=
            styles["Title"],

        fontName=
            "Helvetica-Bold",

        fontSize=
            18,

        leading=
            22,

        textColor=
            NAVY,

        alignment=
            TA_CENTER,

        spaceAfter=
            0,
    )


    style_body = ParagraphStyle(

        "BodyBNH",

        parent=
            styles["BodyText"],

        fontName=
            "Helvetica",

        fontSize=
            9.2,

        leading=
            13,

        textColor=
            TEXT,
    )


    style_body_small = ParagraphStyle(

        "BodySmallBNH",

        parent=
            style_body,

        fontSize=
            7.5,

        leading=
            9.4,
    )


    style_label = ParagraphStyle(

        "LabelBNH",

        parent=
            style_body,

        fontName=
            "Helvetica-Bold",

        fontSize=
            7.5,

        leading=
            9.2,

        textColor=
            NAVY,
    )


    style_section = ParagraphStyle(

        "SectionBNH",

        parent=
            style_body,

        fontName=
            "Helvetica-Bold",

        fontSize=
            10.5,

        leading=
            12,

        textColor=
            NAVY,
    )


    story = []


    # ========================================================
    # CABECERA
    # ========================================================

    logo = _logo_provincia()


    ministerio = Paragraph(
        (
            "Ministerio de Educación, Cultura, "
            "Ciencia y Tecnología"
            "<br/>"
            "<b>de la Provincia del Chaco</b>"
        ),
        style_header,
    )


    bnh = Paragraph(
        (
            "Base Nacional Homologada"
            "<br/>"
            "(BNH)"
        ),
        style_header_right,
    )


    if logo:

        header = Table(

            [[
                logo,
                ministerio,
                bnh,
            ]],

            colWidths=[
                32 * mm,
                91 * mm,
                58 * mm,
            ],
        )

        bnh_col = 2

    else:

        header = Table(

            [[
                ministerio,
                bnh,
            ]],

            colWidths=[
                123 * mm,
                58 * mm,
            ],
        )

        bnh_col = 1


    header.setStyle(
        TableStyle([

            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "MIDDLE",
            ),

            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                0,
            ),

            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                2 * mm,
            ),

            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                0,
            ),

            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                3 * mm,
            ),

            (
                "LINEBEFORE",
                (bnh_col, 0),
                (bnh_col, 0),
                1.1,
                BLUE,
            ),

            (
                "LEFTPADDING",
                (bnh_col, 0),
                (bnh_col, 0),
                6 * mm,
            ),
        ])
    )


    story.append(
        header
    )


    story.append(
        Spacer(
            1,
            3 * mm,
        )
    )


    # ========================================================
    # TÍTULO
    # ========================================================

    title_box = Table(

        [[
            Paragraph(
                "CONSTANCIA DE SERVICIO",
                style_title,
            )
        ]],

        colWidths=[
            181 * mm
        ],
    )


    title_box.setStyle(
        TableStyle([

            (
                "BACKGROUND",
                (0, 0),
                (-1, -1),
                PALE_BLUE,
            ),

            (
                "BOX",
                (0, 0),
                (-1, -1),
                0.6,
                PALE_BLUE,
            ),

            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                4 * mm,
            ),

            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                4 * mm,
            ),
        ])
    )


    story.append(
        title_box
    )


    story.append(
        Spacer(
            1,
            2.5 * mm,
        )
    )


    # ========================================================
    # FECHA DE EMISIÓN
    # ========================================================

    issue = Table(

        [[
            "",

            Paragraph(
                (
                    "<b>Fecha de emisión:</b> "
                    f"{_html(_fecha(fecha_emision))}"
                ),
                style_body_small,
            ),
        ]],

        colWidths=[
            119 * mm,
            62 * mm,
        ],
    )


    issue.setStyle(
        TableStyle([

            (
                "ALIGN",
                (1, 0),
                (1, 0),
                "RIGHT",
            ),

            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "TOP",
            ),

            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                0,
            ),

            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                0,
            ),

            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                0,
            ),

            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                0,
            ),
        ])
    )


    story.append(
        issue
    )


    story.append(
        Spacer(
            1,
            3.5 * mm,
        )
    )


    # ========================================================
    # INTRODUCCIÓN
    # ========================================================

    intro = (

        f"La Dirección de "
        f"<b>{_html(nom_est, 'la institución')}</b>, "

        f"CUEANEXO: "
        f"<b>{_html(cueanexo)}</b>, "

        "deja constancia de que la persona cuyos datos se "
        "detallan a continuación presta o ha prestado "
        "servicios en esta institución, conforme a los "
        "registros obrantes en la Base Nacional Homologada "
        "(BNH)."
    )


    story.append(
        Paragraph(
            intro,
            style_body,
        )
    )


    story.append(
        Spacer(
            1,
            4 * mm,
        )
    )


    # ========================================================
    # DATOS DEL PERSONAL
    # ========================================================

    section_person = Table(

        [[
            Paragraph(
                "DATOS DEL PERSONAL",
                style_section,
            )
        ]],

        colWidths=[
            181 * mm
        ],
    )


    section_person.setStyle(
        TableStyle([

            (
                "BACKGROUND",
                (0, 0),
                (-1, -1),
                PALE_BLUE,
            ),

            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                2 * mm,
            ),

            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                2 * mm,
            ),

            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                2 * mm,
            ),
        ])
    )


    story.append(
        section_person
    )


    personal_table = Table(

        [

            [
                Paragraph(
                    "Apellido y Nombre",
                    style_label,
                ),

                Paragraph(
                    (
                        f"<b>"
                        f"{_html(getattr(persona, 'apellido', ''))}, "
                        f"{_html(getattr(persona, 'nombre', ''))}"
                        f"</b>"
                    ),
                    style_body,
                ),
            ],

            [
                Paragraph(
                    "CUIL",
                    style_label,
                ),

                Paragraph(
                    (
                        f"<b>"
                        f"{_html(getattr(persona, 'cuil', ''))}"
                        f"</b>"
                    ),
                    style_body,
                ),
            ],
        ],

        colWidths=[
            41 * mm,
            140 * mm,
        ],
    )


    personal_table.setStyle(
        TableStyle([

            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.55,
                GRID,
            ),

            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "MIDDLE",
            ),

            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                2.5 * mm,
            ),

            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                2.5 * mm,
            ),

            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                2 * mm,
            ),

            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                2 * mm,
            ),
        ])
    )


    story.append(
        personal_table
    )


    story.append(
        Spacer(
            1,
            4 * mm,
        )
    )


    # ========================================================
    # DATOS DE LA INSTITUCIÓN
    # ========================================================

    section_inst = Table(

        [[
            Paragraph(
                "DATOS DE LA INSTITUCIÓN",
                style_section,
            )
        ]],

        colWidths=[
            181 * mm
        ],
    )


    section_inst.setStyle(
        TableStyle([

            (
                "BACKGROUND",
                (0, 0),
                (-1, -1),
                PALE_BLUE,
            ),

            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                2 * mm,
            ),

            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                2 * mm,
            ),

            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                2 * mm,
            ),
        ])
    )


    story.append(
        section_inst
    )


    institution_table = Table(

        [

            [
                Paragraph(
                    "CUEANEXO",
                    style_label,
                ),

                Paragraph(
                    f"<b>{_html(cueanexo)}</b>",
                    style_body,
                ),
            ],

            [
                Paragraph(
                    "Nombre",
                    style_label,
                ),

                Paragraph(
                    f"<b>{_html(nom_est)}</b>",
                    style_body,
                ),
            ],
        ],

        colWidths=[
            41 * mm,
            140 * mm,
        ],
    )


    institution_table.setStyle(
        TableStyle([

            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.55,
                GRID,
            ),

            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "MIDDLE",
            ),

            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                2.5 * mm,
            ),

            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                2.5 * mm,
            ),

            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                2 * mm,
            ),

            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                2 * mm,
            ),
        ])
    )


    story.append(
        institution_table
    )


    story.append(
        Spacer(
            1,
            4 * mm,
        )
    )


    # ========================================================
    # SERVICIOS
    # ========================================================

    section_services = Table(

        [[
            Paragraph(
                "SERVICIOS REGISTRADOS EN LA INSTITUCIÓN",
                style_section,
            )
        ]],

        colWidths=[
            181 * mm
        ],
    )


    section_services.setStyle(
        TableStyle([

            (
                "BACKGROUND",
                (0, 0),
                (-1, -1),
                PALE_BLUE,
            ),

            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                2 * mm,
            ),

            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                2 * mm,
            ),

            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                2 * mm,
            ),
        ])
    )


    story.append(
        section_services
    )


    story.append(
        Spacer(
            1,
            1.5 * mm,
        )
    )


    table_data = [[

        Paragraph(
            "N.º",
            style_label,
        ),

        Paragraph(
            "Cargo / Función",
            style_label,
        ),

        Paragraph(
            "Situación de revista",
            style_label,
        ),

        Paragraph(
            "Tipo",
            style_label,
        ),

        Paragraph(
            "Espacio curricular / Asignatura",
            style_label,
        ),

        Paragraph(
            "Grado / Año",
            style_label,
        ),

        Paragraph(
            "Sección",
            style_label,
        ),

        Paragraph(
            "Carga horaria",
            style_label,
        ),

        Paragraph(
            "Fecha inicio",
            style_label,
        ),

        Paragraph(
            "Fecha fin",
            style_label,
        ),
    ]]


    for index, actividad in enumerate(
        actividades,
        start=1,
    ):

        table_data.append([

            Paragraph(
                str(index),
                style_body_small,
            ),

            Paragraph(
                _html(
                    _cargo_actividad(
                        actividad
                    )
                ),
                style_body_small,
            ),

            Paragraph(
                _html(
                    _situacion_revista(
                        actividad
                    )
                ),
                style_body_small,
            ),

            Paragraph(
                _html(
                    _tipo_designacion(
                        actividad
                    )
                ),
                style_body_small,
            ),

            Paragraph(
                _html(
                    _espacios_actividad(
                        actividad
                    )
                ),
                style_body_small,
            ),

            Paragraph(
                _html(
                    _grado(
                        actividad
                    )
                ),
                style_body_small,
            ),

            Paragraph(
                _html(
                    _seccion(
                        actividad
                    )
                ),
                style_body_small,
            ),

            Paragraph(
                _html(
                    _numero(
                        getattr(
                            actividad,
                            "carga_horaria",
                            None,
                        )
                    )
                ),
                style_body_small,
            ),

            Paragraph(
                _html(
                    _fecha(
                        getattr(
                            actividad,
                            "f_desde",
                            None,
                        )
                    )
                ),
                style_body_small,
            ),

            Paragraph(
                _html(
                    _fecha(
                        getattr(
                            actividad,
                            "f_hasta",
                            None,
                        )
                    )
                ),
                style_body_small,
            ),
        ])


    services_table = Table(

        table_data,

        colWidths=[

            6 * mm,

            23 * mm,

            22 * mm,

            18 * mm,

            29 * mm,

            15 * mm,

            11 * mm,

            15 * mm,

            21 * mm,

            21 * mm,
        ],

        repeatRows=1,

        hAlign="LEFT",
    )


    services_table.setStyle(
        TableStyle([

            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor(
                    "#DDEAF4"
                ),
            ),

            (
                "TEXTCOLOR",
                (0, 0),
                (-1, 0),
                NAVY,
            ),

            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.45,
                colors.HexColor(
                    "#9FB4C4"
                ),
            ),

            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "MIDDLE",
            ),

            (
                "ALIGN",
                (0, 0),
                (0, -1),
                "CENTER",
            ),

            (
                "ALIGN",
                (5, 1),
                (9, -1),
                "CENTER",
            ),

            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                1.2 * mm,
            ),

            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                1.2 * mm,
            ),

            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                1.6 * mm,
            ),

            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                1.6 * mm,
            ),
        ])
    )


    story.append(
        services_table
    )


    story.append(
        Spacer(
            1,
            4 * mm,
        )
    )


    # ========================================================
    # OBSERVACIÓN
    # ========================================================

    observation = Table(

        [[

            Paragraph(
                "Observaciones",
                style_label,
            ),

            Paragraph(
                (
                    "La presente constancia tiene carácter "
                    "informativo y detalla únicamente los "
                    "servicios registrados en la Base Nacional "
                    "Homologada (BNH) para la persona y la "
                    "institución indicadas."
                ),
                style_body_small,
            ),
        ]],

        colWidths=[
            33 * mm,
            148 * mm,
        ],
    )


    observation.setStyle(
        TableStyle([

            (
                "BACKGROUND",
                (0, 0),
                (0, 0),
                PALE_BLUE,
            ),

            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "TOP",
            ),

            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                2.5 * mm,
            ),

            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                2.5 * mm,
            ),

            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                2 * mm,
            ),

            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                2 * mm,
            ),
        ])
    )


    story.append(
        observation
    )


    story.append(
        Spacer(
            1,
            4 * mm,
        )
    )


    # ========================================================
    # QR
    # ========================================================

    payload = construir_payload_qr(

        cueanexo=
            cueanexo,

        nom_est=
            nom_est,

        persona=
            persona,
    )


    qr = _qr_image(
        payload
    )


    qr_text = Paragraph(

        (
            "<b>Datos incluidos en el código QR</b>"
            "<br/>"

            f"CUEANEXO: "
            f"{_html(payload['cueanexo'])}"
            "<br/>"

            f"Establecimiento: "
            f"{_html(payload['nom_est'])}"
            "<br/>"

            f"CUIL: "
            f"{_html(payload['cuil'])}"
            "<br/>"

            f"Nombre: "
            f"{_html(payload['nombre'])}"
            "<br/>"

            f"Apellido: "
            f"{_html(payload['apellido'])}"
        ),

        style_body_small,
    )


    qr_block = Table(

        [[
            qr,
            qr_text,
        ]],

        colWidths=[
            48 * mm,
            133 * mm,
        ],
    )


    qr_block.setStyle(
        TableStyle([

            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "MIDDLE",
            ),

            (
                "LINEBEFORE",
                (1, 0),
                (1, 0),
                0.8,
                BLUE,
            ),

            (
                "LEFTPADDING",
                (0, 0),
                (0, 0),
                2 * mm,
            ),

            (
                "RIGHTPADDING",
                (0, 0),
                (0, 0),
                5 * mm,
            ),

            (
                "LEFTPADDING",
                (1, 0),
                (1, 0),
                6 * mm,
            ),

            (
                "RIGHTPADDING",
                (1, 0),
                (1, 0),
                0,
            ),

            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                1 * mm,
            ),

            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                1 * mm,
            ),
        ])
    )


    story.append(
        KeepTogether([
            qr_block
        ])
    )


    # ========================================================
    # SIN PIE INSTITUCIONAL / SIN LEMA
    # ========================================================

    doc.build(
        story
    )


    pdf = buffer.getvalue()


    buffer.close()


    return pdf