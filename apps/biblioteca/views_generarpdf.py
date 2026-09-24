import os
import re
from matplotlib.pylab import qr
import psycopg2
import qrcode

from io import BytesIO
from datetime import date, datetime
from collections import defaultdict
from xml.sax.saxutils import escape

from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, F, Value, Func
from django.views.decorators.http import require_POST

from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame,
    Table, TableStyle, Paragraph,
    PageBreak, Image, Spacer
)
from reportlab.lib.pagesizes import legal, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from requests import get

from .models import (
    GenerarInforme,
    MaterialBibliografico,
    ServicioReferencia,
    ServicioReferenciaVirtual,
    InformePedagogico,
    AsistenciaUsuarios,
    InstitucionesPrestaServicios,
    Aguapey,
    RegistroDestinoFondos,
    BibliotecariosCue,
    ProcesosTecnicos,
    ServicioPrestamo
)

from apps.consultasge.models import CapaUnicaOfertas
from reportlab.platypus import KeepTogether, Spacer
from django.utils.text import slugify
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from django.utils import timezone
from qrcode.constants import ERROR_CORRECT_L

from .mixins import PERIODO_ACTIVO_SESSION_KEY, resolver_periodo_activo


# =========================================================
# TABLE STYLE GLOBAL (TODAS LAS TABLAS)
# =========================================================
TABLE_STYLE_GLOBAL = TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, -1), 8),
    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
])


def build_table(data):
    table = Table(data, repeatRows=1)
    table.setStyle(TABLE_STYLE_GLOBAL)
    return table


def valor_pdf(valor):
    return '—' if valor is None or valor == '' else valor


def build_qr(data_str):
    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_L,
        box_size=4,
        border=2,
    )

    # 🔥 límite defensivo
    data_str = str(data_str)[:1500]

    qr.add_data(data_str)
    qr.make(fit=True)

    qr_img = qr.make_image(fill_color="black", back_color="white")

    buffer = BytesIO()
    qr_img.save(buffer, format="PNG")
    buffer.seek(0)

    return Image(buffer, width=90, height=90)

class ReportEngine:
    def __init__(self, story, styles):
        self.story = story
        self.styles = styles

    def add_section(self, title, table, qr=None, extra_flowables=None):
        block = []

        block.append(Paragraph(title, self.styles["Heading3"]))
        block.append(table)
        block.append(Spacer(1, 6))

        if extra_flowables:
            block.extend(extra_flowables)
            block.append(Spacer(1, 6))

        if qr:
            block.append(qr)

        block.append(Spacer(1, 12))

        # Agrupa todo como bloque lógico
        self.story.append(KeepTogether(block))


# =========================================================
# HEADER / FOOTER
# =========================================================
def header(canvas, doc):
    width, height = landscape(legal)
    canvas.saveState()

    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(30, height - 30, "ESTADÍSTICA DE SERVICIOS BIBLIOTECARIOS - MENSUAL")

    canvas.setFont("Helvetica", 8)
    canvas.drawString(30, height - 45, f"CUE: {doc.cueanexo} | MES: {doc.mes} | AÑO: {doc.anio}")

    canvas.drawString(30, height - 58,
        f"Institución: {doc.nom_est} | Modalidad: {doc.oferta} | Cat: {doc.categoria}"
    )

    canvas.drawString(30, height - 71,
        f"Dir: {doc.calle} {doc.numero} | Loc: {doc.localidad} | Reg: {doc.region_loc}"
    )

    canvas.drawString(30, height - 84,
        f"Resp: {doc.apellido_resp} {doc.nombre_resp} | Tel: {doc.telefono}"
    )
    
    canvas.restoreState()


def footer(canvas, doc):
    width, _ = landscape(legal)
    canvas.saveState()

    canvas.setFont("Helvetica", 8)
    canvas.drawString(30, 20, f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    
    canvas.restoreState()



# =========================================================
# VIEW
# =========================================================
@login_required
@require_POST
def generar_pdf_material_bibliografico(request):
    periodo = resolver_periodo_activo(request)
    if periodo is None:
        return HttpResponse(
            "El período solicitado no está disponible para finalizar.",
            status=409,
        )

    cueanexo_activo = str(periodo.cueanexo)
    cueanexos = cueanexo_activo
    mes = periodo.meses
    anio = periodo.annos

    # =========================================================
    # DB
    # =========================================================
    conn = psycopg2.connect(
        host=os.getenv('POSTGRES_HOST'),
        user=os.getenv('POSTGRES_USER'),
        password=os.getenv('POSTGRES_PASSWORD'),
        database=os.getenv('DB_NAME1')
    )
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT categoria, jornada, oferta, nom_est,
                       calle, numero, apellido_resp, nombre_resp,
                       resploc_telefono, resploc_email,
                       cuof_loc, region_loc, localidad
                FROM public.padron_ofertas
                WHERE cueanexo = %s
            """, (cueanexo_activo,))
            row = cursor.fetchone()
    finally:
        conn.close()
    
    if not row:
        return HttpResponse("No se encontraron datos del padron", status=400)


    (
        categoria, jornada, oferta, nom_est,
        calle, numero,
        apellido_resp, nombre_resp,
        telefono, email,
        cuof_loc, region_loc, localidad
    ) = row
    
    fecha_gen = datetime.now().strftime("%d-%m-%Y_%H-%M")

    nombre_resp_full = f"{apellido_resp} {nombre_resp}"
    nombre_resp_limpio = slugify(nombre_resp_full)

    filename = f"{cueanexo_activo} - {nombre_resp_limpio} - {fecha_gen}.pdf"

    # =========================================================
    # PDF
    # =========================================================
    pdf_buffer = BytesIO()

    doc = BaseDocTemplate(
        pdf_buffer,
        pagesize=landscape(legal),
        leftMargin=30,
        rightMargin=30,
        topMargin=110,
        bottomMargin=40
    )

    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height)

    doc.addPageTemplates([
        PageTemplate(id='main', frames=[frame], onPage=lambda c, d: (header(c, d), footer(c, d)))
    ])

    # metadata
    doc.cueanexo = cueanexo_activo
    doc.mes = mes
    doc.anio = anio
    doc.nom_est = nom_est
    doc.oferta = oferta
    doc.categoria = categoria
    doc.calle = calle
    doc.numero = numero
    doc.localidad = localidad
    doc.region_loc = region_loc
    doc.apellido_resp = apellido_resp
    doc.nombre_resp = nombre_resp
    doc.telefono = telefono
    doc.email = email

    styles = getSampleStyleSheet()
    story = []
    engine = ReportEngine(story, styles)
    
    def canvasmaker(*args, **kwargs):
        c = NumberedCanvas(*args, **kwargs)
        c.cueanexo = cueanexo_activo  # 👈 acá lo inyectás directo
        return c

    # =========================================================
    # 1. MATERIAL BIBLIOGRÁFICO
    # =========================================================
    material = MaterialBibliografico.objects.filter(
        cueanexo=cueanexo_activo, mes=mes, anio=anio
    ).values("servicio__nom_servicio", "turnos__nom_turno", "t_material__nom_material").annotate(total=Sum("cantidad")
    ).order_by("servicio__nom_servicio", "t_material__nom_material", "turnos__nom_turno")

    data = [["SERVICIO", "TIPO MATERIAL","TURNO", "TOTAL"]] + [
        [r["servicio__nom_servicio"], r["t_material__nom_material"],r["turnos__nom_turno"], r["total"] or 0]
        for r in material
    ]
    
    qr_material_data = "\n".join([
        f"{r['servicio__nom_servicio']} | {r['t_material__nom_material']} | {r['turnos__nom_turno']} | {r['total'] or 0}"
        for r in material
    ])

    engine.add_section(
        "1. MATERIAL BIBLIOGRÁFICO Y ESPECIAL",
        build_table(data),
        build_qr(f"MATERIAL BIBLIOGRÁFICO {cueanexos} {mes}/{anio}\n\n")
    )

    # =========================================================
    # 2. SERVICIO DE REFERENCIA
    # =========================================================
    ref = ServicioReferencia.objects.filter(
        cueanexo=cueanexo_activo,
        mes=mes,
        anio=anio
    ).values(
        "servicio__nom_servicio",
        "turnos__nom_turno"
    ).annotate(
        varones=Sum("varones"),
        total=Sum("total")
    ).order_by("servicio__nom_servicio", "turnos__nom_turno")

    data = [["SERVICIO", "TURNO", "VARONES", "TOTAL"]] + [
        [r["servicio__nom_servicio"], r["turnos__nom_turno"], r["varones"], r["total"] or 0]
        for r in ref
    ]
    
    qr_servref_data = "\n".join([
        f"{r['servicio__nom_servicio']} | {r['turnos__nom_turno']} | {r['varones']} | {r['total'] or 0}"
        for r in ref
    ])

    engine.add_section(
        "2. SERVICIO DE REFERENCIA",
        build_table(data),
        build_qr(f"SERVICIO DE REFERENCIA {cueanexos} {mes}/{anio}\n\n{qr_servref_data}")
    )
    

    # =========================================================
    # 3. SERVICIO DE REFERENCIA VIRTUAL
    # =========================================================
    virtual = ServicioReferenciaVirtual.objects.filter(
        cueanexo=cueanexo_activo,
        mes=mes,
        anio=anio
    ).values(
        "servicio__nom_servicio",
        "turnos__nom_turno"
    ).annotate(
        varones=Sum("varones"),
        total=Sum("total")
    ).order_by("servicio__nom_servicio", "turnos__nom_turno")

    data = [["SERVICIO", "TURNO", "VARONES", "TOTAL"]] + [
        [r["servicio__nom_servicio"], r["turnos__nom_turno"], r["varones"], r["total"] or 0]
        for r in virtual
    ]
    
    qr_virtual_data = "\n".join([
        f"{r['servicio__nom_servicio']} | {r['turnos__nom_turno']} | {r['varones']} | {r['total'] or 0}"
        for r in virtual
    ])

    engine.add_section(
        "3. SERVICIO DE REFERENCIA VIRTUAL",
        build_table(data),
        build_qr(f"VIRTUAL {cueanexos} {mes}/{anio}\n\n{qr_virtual_data}")
    )
    
    
    # =========================
    # 4.  SERVICIO DE PRÉSTAMO
    # =========================
    prestamo = ServicioPrestamo.objects.filter(
        cueanexo=cueanexo_activo,
        mes=mes,
        anio=anio
    ).values(
        "servicio__nom_servicio",
        "turnos__nom_turno",
        "instalacion",
        "total"
    ).order_by("servicio__nom_servicio", "turnos__nom_turno", "instalacion")
    
    data = [["SERVICIO", "TURNO", "INSTALACIÓN", "TOTAL"]] + [
        [r["servicio__nom_servicio"], r["turnos__nom_turno"], r["instalacion"], r["total"] or 0]
        for r in prestamo
    ]
    
    qr_prestamo_data = "\n".join([
        f"{r['servicio__nom_servicio']} | {r['turnos__nom_turno']} | {r['instalacion']} | {r['total'] or 0}"
        for r in prestamo
    ])
    
    engine.add_section(
        "4. SERVICIO DE PRÉSTAMO",
        build_table(data),
        build_qr(f"PRÉSTAMO {cueanexos} {mes}/{anio}\n\n{qr_prestamo_data}")
    )
    
    
    # ========================
    # 5.  INFORME PEDAGÓGICO
    # ========================
    ped = InformePedagogico.objects.filter(
        cueanexo=cueanexo_activo,
        mes=mes,
        anio=anio
    ).values(
        "servicio__nom_servicio"
    ).annotate(
        varones=Sum("varones"),
        total=Sum("total")
    ).order_by("servicio__nom_servicio")

    data = [["SERVICIO", "VARONES", "TOTAL"]] + [
        [r["servicio__nom_servicio"], r["varones"], r["total"] or 0]
        for r in ped
    ]
    
    qr_pedagogico_data = "\n".join([
        f"{r['servicio__nom_servicio']} | {r['varones']} | {r['total'] or 0}"
        for r in ped
    ])

    engine.add_section(
        "5. INFORME PEDAGÓGICO DE SERVICIOS",
        build_table(data),
        build_qr(f"PEDAGÓGICO {cueanexos} {mes}/{anio}\n\n{qr_pedagogico_data}")
    )
    

    # ==========================
    # 6. ASISTENCIA DE USUARIOS
    # ==========================
    asi = AsistenciaUsuarios.objects.filter(
        cueanexo=cueanexo_activo,
        mes=mes,
        anio=anio
    ).values(
        "nivel",
        "usuario"
    ).annotate(
        varones=Sum("varones"),
        total=Sum("total")
    ).order_by("nivel", "usuario")

    data = [["NIVEL", "USUARIO", "VARONES", "TOTAL"]] + [
        [r["nivel"], r["usuario"], r["varones"], r["total"] or 0]
        for r in asi
    ]

    qr_asistencia_data = "\n".join([
        f"{r['nivel']} | {r['usuario']} | {r['varones']} | {r['total'] or 0}"
        for r in asi
    ])
    
    engine.add_section(
        "6. ASISTENCIA DE USUARIOS BIBLIOTECAS ESCOLARES",
        build_table(data),
        build_qr(f"ASISTENCIA {cueanexos} {mes}/{anio}\n\n{qr_asistencia_data}")
    )
    

    # ============================================
    # 7. INSTITUCIONES A LAS QUE PRESTA SERVICIOS
    # ============================================
    inst = InstitucionesPrestaServicios.objects.filter(
        cueanexo=cueanexo_activo, mes=mes, anio=anio
    ).values_list('escuela', 'matricula', 'docentes', 'matricdisc', 'etnia')

    data = [["INSTITUCION", "MATRICULA", "DOCENTES", "DISCAPACIDAD", "ETNIA"]] + list(inst)

    qr_material_data = "\n".join([
        f"{r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]}"
        for r in inst
    ])
    
    engine.add_section(
        "7. INSTITUCIONES A LAS QUE PRESTA SERVICIOS",
        build_table(data),
        build_qr(f"INSTITUCIONES {cueanexos} {mes}/{anio}\n\n{qr_material_data}")
    )
    
    
    # =========================================================
    # 8. PROCESOS TÉCNICOS
    # =========================================================
    registros = ProcesosTecnicos.objects.filter(
        cueanexo=cueanexo_activo, mes=mes, anio=anio
    ).values_list('material__nom_material', 'procesos', 'total')

    datos_agrupados = defaultdict(lambda: defaultdict(int))
    procesos_unicos = set()

    for material, proceso, total in registros:
        datos_agrupados[material][proceso] += total or 0
        procesos_unicos.add(proceso)

    procesos_unicos = sorted(procesos_unicos)

    data = [["MATERIAL"] + procesos_unicos + ["SUBTOTAL"]]
    
    qr_material_data = "\n".join([
        f"{material} | " + " | ".join(f"{proceso}: {datos_agrupados[material].get(proceso, 0)}" for proceso in procesos_unicos) + f" | SUBTOTAL: {sum(datos_agrupados[material].get(proceso, 0) for proceso in procesos_unicos)}"
        for material in datos_agrupados
    ])

    for material, procesos in datos_agrupados.items():
        fila = [material]
        subtotal = 0

        for p in procesos_unicos:
            v = procesos.get(p, 0)
            fila.append(v)
            subtotal += v

        fila.append(subtotal)
        data.append(fila)

    engine.add_section(
        "8. SECTOR PROCESOS TÉCNICOS",
        build_table(data),
        build_qr(f"PROCESOS {cueanexos} {mes}/{anio}\n\n{qr_material_data}")
    )   
    

    # ===========
    # 9. AGUAPEY
    # ===========
    aguapey = Aguapey.objects.filter(cueanexo=cueanexo_activo, mes=mes, anio=anio).first()

    data = [["MES", "BASE", "USUARIOS", "OBSERVACIONES"], [
        getattr(aguapey, "total_mes", 0),
        getattr(aguapey, "total_base", 0),
        getattr(aguapey, "total_usuarios", 0),
        getattr(aguapey, "observaciones", ""),
    ]]

    qr_aguapey_data = f"BASE DE DATOS COMO RECURSO DE GESTION | MES: {getattr(aguapey, 'total_mes', 0)} | BASE: {getattr(aguapey, 'total_base', 0)} | USUARIOS: {getattr(aguapey, 'total_usuarios', 0)} | OBS: {getattr(aguapey, 'observaciones', '')}"
    
    engine.add_section(
        "9. BASE DE DATOS COMO RECURSOS DE GESTION",
        build_table(data),
        build_qr(qr_aguapey_data)
    )
    

    # =========================================================
    # 10. REGISTRO DESTINO DE FONDO BIBLIOTECARIO CHAQUEÑO
    # =========================================================
    fondos = RegistroDestinoFondos.objects.filter(cueanexo=cueanexo_activo, mes=mes, anio=anio)

    data = [["DESTINO", "DESCRIPCIÓN", "CANTIDAD"]] + [
        [r.destino.nom_fondo, r.descripcion, r.cantidad] for r in fondos
    ]
    
    qr_fondos_data = "\n".join([
        f"{r.destino.nom_fondo} | {r.descripcion} | {r.cantidad}"
        for r in fondos
    ])

    engine.add_section(
        "10. COMPRAS REALIZADAS CON EL FONDO BIBLIOTECARIO CHAQUEÑO",
        build_table(data),
        build_qr(qr_fondos_data)
    )


    # =========================================================
    # 11. BIBLIOTECARIOS
    # =========================================================
    bib = list(
        BibliotecariosCue.objects.filter(
            cueanexo=cueanexo_activo,
            mes=mes,
            anio=anio,
        )
        .select_related('turno', 'licencia_permiso', 'situacion_laboral')
        .order_by('pk')
    )

    def personal_tiene_valor(valor):
        if valor is None:
            return False
        if isinstance(valor, str):
            return bool(valor.strip())
        return True

    def personal_texto_pdf(valor):
        if not personal_tiene_valor(valor):
            return '—'
        if isinstance(valor, datetime):
            return valor.strftime('%d/%m/%Y %H:%M')
        if isinstance(valor, date):
            return valor.strftime('%d/%m/%Y')
        return str(valor)

    personal_body_style = styles["BodyText"].clone("BibliotecaPersonalBody")
    personal_body_style.fontSize = 7
    personal_body_style.leading = 8.5

    def personal_celda_pdf(valor):
        return Paragraph(
            escape(personal_texto_pdf(valor)),
            personal_body_style,
        )

    data = [[
        "CUIL",
        "APELLIDOS",
        "NOMBRES",
        "CUOF",
        "CUOF ANEXO",
        "LICENCIA",
        "DESDE",
        "HASTA",
        "SITUACIÓN LABORAL",
    ]]

    detalles_pdf = []
    qr_bibliotecarios = []

    for r in bib:
        licencia = (
            r.licencia_permiso.tipo_licencia
            if r.licencia_permiso_id
            else None
        )
        situacion_laboral = (
            r.situacion_laboral.tipo_situacion
            if r.situacion_laboral_id
            else None
        )
        turno = r.turno_texto

        data.append([
            personal_texto_pdf(r.cuil),
            personal_celda_pdf(r.apellidos),
            personal_celda_pdf(r.nombres),
            personal_texto_pdf(r.cuof),
            personal_texto_pdf(r.cuof_anexo),
            personal_celda_pdf(licencia),
            personal_texto_pdf(r.f_desde_lic),
            personal_texto_pdf(r.f_hasta_lic),
            personal_celda_pdf(situacion_laboral),
        ])

        campos_adicionales = [
            ("Observaciones", r.observaciones),
            ("Cargo", r.cargo),
            ("Situación de revista", r.situacion_revista),
            ("Ingreso", r.f_ingreso),
            ("Hasta", r.f_hasta),
            ("Turno", turno),
        ]
        adicionales = [
            (etiqueta, personal_texto_pdf(valor))
            for etiqueta, valor in campos_adicionales
            if personal_tiene_valor(valor)
        ]

        if adicionales:
            detalle_html = "<br/>".join(
                f"<b>{escape(etiqueta)}:</b> {escape(valor)}"
                for etiqueta, valor in adicionales
            )
            detalles_pdf.append([
                personal_texto_pdf(r.cuil),
                Paragraph(detalle_html, personal_body_style),
            ])

        qr_campos = [
            ("CUIL", r.cuil),
            ("Apellidos", r.apellidos),
            ("Nombres", r.nombres),
            ("CUOF", r.cuof),
            ("CUOF Anexo", r.cuof_anexo),
            ("Licencia", licencia),
            ("Desde licencia", r.f_desde_lic),
            ("Hasta licencia", r.f_hasta_lic),
            ("Situación laboral", situacion_laboral),
            *campos_adicionales,
        ]
        qr_bibliotecarios.append(
            " | ".join(
                f"{etiqueta}: {personal_texto_pdf(valor)}"
                for etiqueta, valor in qr_campos
                if personal_tiene_valor(valor)
            )
        )

    tabla_personal = Table(
        data,
        repeatRows=1,
        colWidths=[82, 92, 104, 48, 58, 120, 62, 62, 170],
    )
    tabla_personal.setStyle(TABLE_STYLE_GLOBAL)

    extra_flowables = []
    if detalles_pdf:
        detalle_style = styles["Heading4"].clone("BibliotecaPersonalDetalleTitulo")
        detalle_style.spaceBefore = 4
        detalle_style.spaceAfter = 4

        tabla_detalles = Table(
            [["CUIL", "DATOS ADICIONALES"], *detalles_pdf],
            repeatRows=1,
            colWidths=[90, doc.width - 90],
        )
        tabla_detalles.setStyle(TABLE_STYLE_GLOBAL)

        extra_flowables = [
            Paragraph("Datos adicionales", detalle_style),
            tabla_detalles,
        ]

    qr_bibliotecarios_data = "\n".join(qr_bibliotecarios)

    engine.add_section(
        "11. PERSONAL BIBLIOTECARIO",
        tabla_personal,
        build_qr(qr_bibliotecarios_data),
        extra_flowables=extra_flowables,
    )

    doc.build(story, canvasmaker=canvasmaker)
    
    actualizados = GenerarInforme.objects.filter(
        pk=periodo.pk,
        estado="GENERADO"
    ).update(
        estado="ENVIADO",
        f_envio=timezone.now()
    )

    if actualizados != 1:
        return HttpResponse(
            "El período ya no está disponible para finalizar.",
            status=409,
        )

    if request.session.get(PERIODO_ACTIVO_SESSION_KEY) == periodo.pk:
        request.session.pop(PERIODO_ACTIVO_SESSION_KEY, None)
        request.session.pop("cueanexo_activo", None)

    response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    return response


class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total_pages = len(self._saved_page_states)

        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_footer(total_pages)
            super().showPage()

        super().save()

    def draw_footer(self, total_pages):
        width, height = landscape(legal)

        cue = getattr(self, "cueanexo", "")

        self.setFont("Helvetica", 8)

        self.drawString(
            30,
            20,
            f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        )

        self.drawRightString(
            width - 60,
            20,
            f"CUE: {cue} | Página {self._pageNumber} de {total_pages}"
        )
