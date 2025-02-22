import os
import dotenv
import psycopg2
from django.http import HttpResponse
from django.db.models import Sum
from reportlab.lib.pagesizes import legal, landscape
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from django.contrib.auth.decorators import login_required
from .models import MaterialBibliografico
from django.db import connection
from django.shortcuts import render
from reportlab.lib.units import inch
import tempfile
import qrcode
from io import BytesIO
from datetime import datetime


@login_required
def generar_pdf_material_bibliografico(request):    
    
    usuario =request.user.username
    
    # Establecer la conexión a la base de datos Visualizador
    try:
        connection = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST'),
            user=os.getenv('POSTGRES_USER'),
            password=os.getenv('POSTGRES_PASSWORD'),
            database=os.getenv('DB_NAME1')
        )
        cursor = connection.cursor()
    except psycopg2.Error as e:
        # Manejar el error de conexión
        return render(request, 'error.html', {'mensaje': 'Error al conectar a la base de datos'})

    
    query = """SELECT categoria, jornada, oferta, nom_est, ref_loc, calle, numero, anexo, apellido_resp, nombre_resp, resploc_telefono, resploc_email,
            sup_tecnico, email_suptecnico, tel_suptecnico, cui_loc, cuof_loc
        FROM public.padron_ofertas        
        WHERE cueanexo = %s"""
    
    cursor.execute(query, (usuario,))
    datosbiblio = cursor.fetchall()
    print(datosbiblio)
    
    if datosbiblio:
        nom_est = datosbiblio[0][3]
    else:
        nom_est = "No disponible"
    
    ultimo_registro_mes = MaterialBibliografico.objects.filter(cueanexo=usuario).order_by('-id').first()
    if ultimo_registro_mes:
        mes = ultimo_registro_mes.mes
    else:
        mes = "Mes no disponible"
        
    ultimo_registro_anno = MaterialBibliografico.objects.filter(cueanexo=usuario).order_by('-id').first()
    if ultimo_registro_anno:
        anio = ultimo_registro_anno.anio
    else:
        anio = "Año no disponible"
    
    turnos = MaterialBibliografico.objects.filter(cueanexo=usuario).select_related('turnos_id').values_list('turnos__nom_turno', flat=True).distinct()

    # Convertimos el QuerySet a una lista
    turnos_lista = list(turnos)

    # Preparar la respuesta PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{usuario}-Material Bibliográfico y Especial.pdf"'    
    
    p = canvas.Canvas(response, pagesize=landscape(legal))
    width, height = landscape(legal)

    # Aquí puedes agregar los encabezados antes de la tabla
    p.setFont("Helvetica", 14)
    
    # Agregar encabezados estáticos
    p.drawString(30, height - 40, "ESTADISTICA DE SERVICIOS BIBLIOTECARIOS-MENSUAL-")
    p.drawString(30, height - 55, f"CUE: {usuario} OFICINA: ___________ MES: {mes} AÑO: {anio}")
    p.drawString(30, height - 70, f"BIBLIOTECA Nº Y NOMBRE: {nom_est} MODALIDAD: ________________")
    p.drawString(30, height - 85, "CATEGORÍA: _______ REG.: _______ DOMICILIO: ____________ LOCALIDAD: ________ MAIL: ________")
    p.drawString(30, height - 100, f"TURNO: {', '.join(turnos_lista)}")
    p.drawString(550, height - 360, "DIRECTOR:________________")
        
    # Aquí va tu código para generar la tabla
    service_categories = [
        {"name": "PRESTAMO EN SALA", "cod_servicio": 111},
        {"name": "PRESTAMO EN AULA", "cod_servicio": 112},
        {"name": "PRESTAMO A DOMICILIO", "cod_servicio": 113},
        {"name": "PRESTAMOS A OTRAS INSTITUCIONES", "cod_servicio": 114},
    ]
    material_types = [
        "LIBROS",
        "FOLLETOS",
        "SOPORTES ELECTRÓNICOS",
        "MATERIAL VISUAL",
        "PARTITURAS/GRABACIONES",
        "PUBLICACIONES",
    ]

    data = [
        ["1. MATERIAL BIBLIOGRÁFICO Y ESPECIAL"] + [""] * (len(material_types) + 2),
        ["SERVICIOS", "TURNOS"] + material_types + ["TOTAL"]
    ]

    for cat in service_categories:
        turnos = (
            MaterialBibliografico.objects.filter(servicio__cod_servicio=cat["cod_servicio"])
            .values_list("turnos__nom_turno", flat=True)
            .distinct()
        )

        if not turnos:
            row = [cat["name"]] + ["No hay datos disponibles"]
            data.append(row)
            continue

        row_total = 0
        row = [cat["name"]] + [" "]
        data.append(row)

        for turno in turnos:
            row_turno = [""] + [turno]
            row_turno_total = 0

            for mat_type in material_types:
                if mat_type == "PARTITURAS/GRABACIONES":
                    cantidad_sum = (
                        MaterialBibliografico.objects.filter(
                            servicio__cod_servicio=cat["cod_servicio"],
                            t_material__nom_material__in=["PARTITURAS", "GRABACIONES"],
                            turnos__nom_turno=turno
                        )
                        .aggregate(total=Sum("cantidad"))["total"] or 0
                    )
                else:
                    cantidad_sum = (
                        MaterialBibliografico.objects.filter(
                            servicio__cod_servicio=cat["cod_servicio"],
                            t_material__nom_material=mat_type,
                            turnos__nom_turno=turno
                        )
                        .aggregate(total=Sum("cantidad"))["total"] or 0
                    )
                row_turno.append(cantidad_sum)
                row_turno_total += cantidad_sum

            row_turno.append(row_turno_total)
            data.append(row_turno)
            row_total += row_turno_total

    n_columns = len(data[1])
    overall_totals = ["TOTALES", ""]
    for i in range(2, n_columns):
        column_total = 0
        for row in data[2:]:
            if len(row) > i and isinstance(row[i], (int, float)):
                column_total += row[i]
        overall_totals.append(column_total)

    data.append(overall_totals)

    # Crear la tabla en el PDF
    styles = getSampleStyleSheet()
    header_style = ParagraphStyle(
        name="HeaderStyle",
        parent=styles["Normal"],
        alignment=TA_CENTER, 
        fontSize=12,
    )

    normalStyle = styles["Normal"]
    data_wrapped = []
    for i, row in enumerate(data):
        if i == 0:  
            data_wrapped.append([Paragraph(str(cell), header_style) for cell in row])
        elif i == 1:  
            data_wrapped.append([Paragraph(str(cell), header_style) for cell in row])
        else:  
            data_wrapped.append([Paragraph(str(cell), normalStyle) for cell in row])

    col_widths = [150, 90] + [60,80,110,80,120,120] * len(material_types) + [90]   
    table = Table(data_wrapped, colWidths=col_widths)

    style = TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('ALIGN', (0, 1), (-1, 1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTSIZE', (0, 0), (-1, -1), 14),
        ('SPAN', (0, 0), (-1, 0)),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('BACKGROUND', (0, 1), (-1, 1), colors.whitesmoke),
        ('BOLD', (0, 1), (-1, 1)),
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
        ('BOLD', (0, -1), (-1, -1)),
    ])
    table.setStyle(style)

    table.wrapOn(p, width, height)
    table.drawOn(p, 50, height - 315)

    # Datos para el QR
    cueanexo = usuario
    fecha_generacion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Obtener el total de la columna Totales (última columna)
    total_columna_totales = overall_totals[-1]

    # Formatear los totales para el QR (solo el valor total de la última columna)
    qr_data = f"CUE: {cueanexo}\nMes: {mes}\nAño:{anio}\nFecha de generación: {fecha_generacion}\nTotal de Material Bibliográfico y Especial: {total_columna_totales:,.2f}"

    # Generar el código QR
    qr = qrcode.make(qr_data)

    # Guardar el QR en un archivo temporal
    with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_qr_file:
        qr.save(temp_qr_file, format='PNG')
        qr_file_path = temp_qr_file.name

    # Insertar la imagen del QR en el PDF
    p.drawImage(qr_file_path, width - 890, height - 460, width=100, height=100)

    # Eliminar el archivo temporal después de usarlo
    os.remove(qr_file_path)
    
    p.showPage()
    p.save()
    
    return response
