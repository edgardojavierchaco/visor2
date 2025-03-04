import email
import os
import dotenv
import psycopg2
from django.http import HttpResponse
from django.db.models import Sum
from reportlab.lib.pagesizes import legal, landscape, portrait
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle, Paragraph,SimpleDocTemplate
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from django.contrib.auth.decorators import login_required

from apps import usuarios
from .models import GenerarInforme, InstitucionesPrestaServicios, MaterialBibliografico, ProcesosTecnicos, ServicioReferencia, ServicioReferenciaVirtual, ServicioPrestamo, InformePedagogico
from .models import AsistenciaUsuarios, Aguapey, PlanillasAnexas
from django.db import connection
from django.shortcuts import render
from reportlab.lib.units import inch, mm
import tempfile
import qrcode
from io import BytesIO
from datetime import datetime
from collections import defaultdict
from django.contrib import messages
from apps.usuarios.models import UsuariosVisualizador


@login_required
def modal_generar_pdf_cuemesanio_uno(request):
    cueanexo=request.user.username
    print(cueanexo)
    return render(request, 'biblioteca/consulta_cue_mes_anio_uno.html', {'cueanexo': cueanexo})

@login_required
def generar_pdf_cuemesanio_uno(request):    
    # Obtener los datos del formulario
    cueanexo =request.POST.get('cueanexo')
    mes = request.POST.get('mes')
    anio = request.POST.get('anio')
    
    print(cueanexo, mes, anio)
    
    # Establecer la conexión a la base de datos padron
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
            sup_tecnico, email_suptecnico, tel_suptecnico, cui_loc, cuof_loc, region_loc, localidad
        FROM public.padron_ofertas        
        WHERE cueanexo = %s """
    
    cursor.execute(query, (cueanexo,))
    datosbiblio = cursor.fetchall()
    print(datosbiblio)
    
    if datosbiblio:
        categoria = datosbiblio[0][0]
        jornada = datosbiblio[0][1]
        oferta = datosbiblio[0][2]
        nom_est = datosbiblio[0][3]
        calle= datosbiblio[0][5]
        numero = datosbiblio[0][6]
        apellido_resp = datosbiblio[0][8]
        nombre_resp = datosbiblio[0][9]
        resploc_telefono = datosbiblio[0][10]
        resploc_email = datosbiblio[0][11]
        cuof_loc= datosbiblio[0][16]
        region_loc = datosbiblio[0][17]
        localidad = datosbiblio[0][18]
    else:
        nom_est = "No disponible"    
       

        
####################################################
#             MATERIAL BIBLIOGRAFICO               #
####################################################
   

    # Verificar si el mes y año existen en la base de datos
    ultimo_registro_mes = GenerarInforme.objects.filter(cueanexo=cueanexo, meses=mes, annos=anio).exists()
    
    if not ultimo_registro_mes:
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="sin_registros_{cueanexo}_{mes}_{anio}.pdf"'
        
        p = canvas.Canvas(response, pagesize=portrait(legal))
        p.setFont("Helvetica-Bold", 12)
        p.drawString(100, 500, f"No existen registros para el CUE: {cueanexo}, Mes: {mes}, Año: {anio}")
        
        p.showPage()
        p.save()
        
        return response
    

    # Obtener los datos desde el modelo MaterialBibliografico    
    turnos = MaterialBibliografico.objects.filter(cueanexo=cueanexo).select_related('turnos_id').values_list('turnos__nom_turno', flat=True).distinct()
      
    # Convertimos el QuerySet a una lista
    turnos_lista = list(turnos)
    
    # Preparar la respuesta PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{cueanexo}-Material Bibliográfico y Especial.pdf"'    
    
    p = canvas.Canvas(response, pagesize=landscape(legal))
    p.setTitle('Planilla')
    width, height = landscape(legal)

    # Aquí puedes agregar los encabezados antes de la tabla
    p.setFont("Helvetica", 14)
    
    # Agregar encabezados estáticos
    p.setFont("Helvetica-Bold", 14)
    p.drawString(30, height - 40, "ESTADISTICA DE SERVICIOS BIBLIOTECARIOS-MENSUAL-")  
    p.setFont("Helvetica", 14)  
    p.drawString(30, height - 55, f"CUE: {cueanexo} OFICINA: {cuof_loc} MES: {mes} AÑO: {anio}")
    p.setFont("Helvetica-Bold", 14)
    p.drawString(30, height - 70, f"BIBLIOTECA: {nom_est} MODALIDAD: {oferta}")
    p.setFont("Helvetica", 14)
    p.drawString(30, height - 85, f"CATEGORÍA: {categoria} REG.: {region_loc} DOMICILIO: {calle} {numero} LOCALIDAD: {localidad} MAIL: {resploc_email}")
    p.setFont("Helvetica-Bold", 14)
    p.drawString(30, height - 100, f"TURNO: {', '.join(turnos_lista)}")
    p.drawString(550, height - 560, f"RESPONSABLE: {apellido_resp} {nombre_resp} - TEL: {resploc_telefono}")
        
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
            MaterialBibliografico.objects.filter(servicio__cod_servicio=cat["cod_servicio"],
                                                 cueanexo=cueanexo, mes=mes, anio=anio)
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
                            turnos__nom_turno=turno, cueanexo=cueanexo, mes=mes, anio=anio
                        )
                        .aggregate(total=Sum("cantidad"))["total"] or 0
                    )
                else:
                    cantidad_sum = (
                        MaterialBibliografico.objects.filter(
                            servicio__cod_servicio=cat["cod_servicio"],
                            t_material__nom_material=mat_type,
                            turnos__nom_turno=turno, cueanexo=cueanexo, mes=mes, anio=anio
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
    cueanexo = cueanexo
    fecha_generacion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Obtener el total de la columna Totales (última columna)
    total_columna_totales = overall_totals[-1]
    
    
    # Formatear los totales para el QR (solo el valor total de la última columna)
    qr_data = f"CUE: {cueanexo}\nMes: {mes}\nAño:{anio}\nFecha de generación: {fecha_generacion}\nTotal de Material Bibliográfico y Especial: {total_columna_totales:,.2f}\nResponsable: {apellido_resp} {nombre_resp}"

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
    
    # salto de página       
    p.showPage()
    
##########################################################
#                 SERVICIOS DE REFERENCIA                #
##########################################################

    p.setFont("Helvetica", 14)    

    # Agregar encabezados estáticos
    p.setFont("Helvetica-Bold", 14)
    p.drawString(30, height - 40, "ESTADISTICA DE SERVICIOS BIBLIOTECARIOS-MENSUAL-")  
    p.setFont("Helvetica", 14)  
    p.drawString(30, height - 55, f"CUE: {cueanexo} OFICINA: {cuof_loc} MES: {mes} AÑO: {anio}")
    p.setFont("Helvetica-Bold", 14)
    p.drawString(30, height - 70, f"BIBLIOTECA: {nom_est} MODALIDAD: {oferta}")
    p.setFont("Helvetica", 14)
    p.drawString(30, height - 85, f"CATEGORÍA: {categoria} REG.: {region_loc} DOMICILIO: {calle} {numero} LOCALIDAD: {localidad} MAIL: {resploc_email}")
    p.setFont("Helvetica-Bold", 14)
    p.drawString(30, height - 100, f"TURNO: {', '.join(turnos_lista)}")
    p.drawString(550, height - 560, f"RESPONSABLE: {apellido_resp} {nombre_resp} - TEL: {resploc_telefono}")
    
    
    # Código para tabla Servicio Referencia
    service_categories = [
    {"name": "CONSULTA EN EL LUGAR", "cod_servicio": 211},
    {"name": "INFORMACIÓN AL CIUDADANO", "cod_servicio": 212},        
    ]

    data = [
        ["2. SERVICIO DE REFERENCIA", "", "TOTAL"],
        ["SERVICIOS", "TURNOS", "V", "T"],
    ]

    total_v_general = 0
    total_t_general = 0
        
    
    turnos_sref = ServicioReferencia.objects.filter(cueanexo=cueanexo).select_related('turnos_id').values_list('turnos__nom_turno', flat=True).distinct()
   

    for cat in service_categories:
        turnos_data = (
            ServicioReferencia.objects.filter(servicio__cod_servicio=cat["cod_servicio"],
                    cueanexo=cueanexo, mes=mes, anio=anio)
            .values("turnos__nom_turno")  
            .annotate(total_v=Sum("varones"), total_t=Sum("total"))
        )

        if not turnos_data:
            row = [cat["name"], "No hay datos disponibles", "", ""]
            data.append(row)
            continue

        row = [cat["name"], "", "", ""]
        data.append(row)

        for turno in turnos_data:
            turno_nombre = turno["turnos__nom_turno"]
            total_v = turno["total_v"] or 0
            total_t = turno["total_t"] or 0

            data.append(["", turno_nombre, total_v, total_t])

            total_v_general += total_v
            total_t_general += total_t

    # Agregar total general sin subtotales
    data.append(["TOTAL GENERAL", "", total_v_general, total_t_general])
    

#########################################################
#           SERVICIO DE REFERNCIA VIRTUAL               #
#########################################################
    
    # Tabla Servicios Referencia Virtual
    service_categories_virtual = [
        {"name": "PUBLICACIONES EN REDES", "cod_servicio": 311},
        {"name": "INFORMACION AL CIUDADANO", "cod_servicio": 312},
    ]

    data_virtual = [
        ["3. SERVICIO DE REFERENCIA VIRTUAL", "", "TOTAL"],
        ["SERVICIOS", "TURNOS", "V", "T"],
    ]

    total_v_general1 = 0
    total_t_general1 = 0
    
    for cat in service_categories_virtual:
        turnos_data = (
            ServicioReferenciaVirtual.objects.filter(
                servicio__cod_servicio=cat["cod_servicio"],
                cueanexo=cueanexo, mes=mes, anio=anio
            )
            .values("turnos__nom_turno")
            .annotate(total_v1=Sum("varones"), total_t1=Sum("total"))
        )

        if not turnos_data:
            data_virtual.append([cat["name"], "No hay datos disponibles", "", ""])
            continue

        data_virtual.append([cat["name"], "", "", ""])

        for turno in turnos_data:
            turno_nombre = turno["turnos__nom_turno"]
            total_v1 = turno.get("total_v1", 0)  # Evitar errores si no existe
            total_t1 = turno.get("total_t1", 0)

            data_virtual.append(["", turno_nombre, total_v1, total_t1])

            total_v_general1 += total_v1
            total_t_general1 += total_t1

    # Agregar total general
    data_virtual.append(["TOTALES:", "", total_v_general1, total_t_general1])

    # Estilos para la tabla en el PDF
    styles = getSampleStyleSheet()
    header_style = ParagraphStyle(
        name="HeaderStyle",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        fontSize=12,
    )

    normalStyle = styles["Normal"]
    data_wrapped_virtual = []
    for i, row in enumerate(data_virtual):
        if i == 0 or i == 1:  # Encabezados
            data_wrapped_virtual.append([Paragraph(str(cell), header_style) for cell in row])
        else:  # Datos normales
            data_wrapped_virtual.append([Paragraph(str(cell), normalStyle) for cell in row])

    # Definir anchos de columna
    col_widths_virtual = [190, 150, 40, 40]

    # Crear la tabla de servicios virtuales
    table2 = Table(data_wrapped_virtual, colWidths=col_widths_virtual)

    # Aplicar estilos
    common_style = TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('ALIGN', (0, 1), (-1, 1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('SPAN', (0, 0), (-1, 0)),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('BACKGROUND', (0, 1), (-1, 1), colors.whitesmoke),
        ('BOLD', (0, 1), (-1, 1)),
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
        ('BOLD', (0, -1), (-1, -1)),
    ])
    # Crear las dos tablas
    col_widths = [190, 150, 40, 40]  # Ajustar según sea necesario
    col_widths_virtual = [190, 150, 40, 40]  # Ajustar según sea necesario

    table1 = Table(data, colWidths=col_widths)
    table2 = Table(data_virtual, colWidths=col_widths_virtual)

    # Estilos generales para ambas tablas
    common_style = TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('ALIGN', (0, 1), (-1, 1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('SPAN', (0, 0), (-1, 0)),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('BACKGROUND', (0, 1), (-1, 1), colors.whitesmoke),
        ('BOLD', (0, 1), (-1, 1)),
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
        ('BOLD', (0, -1), (-1, -1)),
    ])

    table1.setStyle(common_style)
    table2.setStyle(common_style)

    # Posicionar las tablas y dibujarlas en el canvas
    table1.wrapOn(p, 30, height - 150)
    table2.wrapOn(p, 30, height - 150)
    
    table1.drawOn(p, 30, height - 250)  # Ajusta la posición según sea necesario
    table2.drawOn(p, 470, height - 220)  # Ajusta la posición según sea necesario
    
    # Datos para el QR
    cueanexo = cueanexo
    fecha_generacion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    total_referencia = total_t_general 
    total_virtual = total_t_general1    
    
    
    # Formatear los totales para el QR (solo el valor total de la última columna)
    qr_data = f"CUE: {cueanexo}\nMes: {mes}\nAño:{anio}\nFecha de generación: {fecha_generacion}\nServicios de Referencia: {total_referencia:,.2f}\nServicios Referencia Virtual: {total_virtual}\nResponsable: {apellido_resp} {nombre_resp}"

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


########################################################
#                  SERVICIO PRÉSTAMO                   #
########################################################
    
        
    turnos_sp = ServicioPrestamo.objects.filter(cueanexo=cueanexo).select_related('turnos_id').values_list('turnos__nom_turno', flat=True).distinct()
   
    
    # Obtener los datos desde el modelo ServicioPrestamo
    datos = (ServicioPrestamo.objects.filter(cueanexo=cueanexo, mes=mes, anio=anio)
        .values(
            'servicio__nom_servicio', 
            'turnos__nom_turno', 
            'instalacion', 
            'total'
    ))

    # Agrupar datos por servicio y turno
    servicios_dict = {}
    for item in datos:
        servicio = item['servicio__nom_servicio']
        turno = item['turnos__nom_turno']
        instalacion = item['instalacion']
        total = item['total']

        if servicio not in servicios_dict:
            servicios_dict[servicio] = {}

        if turno not in servicios_dict[servicio]:
            servicios_dict[servicio][turno] = {'SALA': 0, 'AULA': 0, 'DOMICILIO': 0, 'OTRAS': 0, 'TOTAL': 0}

        servicios_dict[servicio][turno][instalacion] += total
        servicios_dict[servicio][turno]['TOTAL'] += total
    
    
    # Agregar encabezados estáticos
    p.setFont("Helvetica-Bold", 14)
    p.drawString(30, height - 40, "ESTADISTICA DE SERVICIOS BIBLIOTECARIOS-MENSUAL-")  
    p.setFont("Helvetica", 14)  
    p.drawString(30, height - 55, f"CUE: {cueanexo} OFICINA: {cuof_loc} MES: {mes} AÑO: {anio}")
    p.setFont("Helvetica-Bold", 14)
    p.drawString(30, height - 70, f"BIBLIOTECA: {nom_est} MODALIDAD: {oferta}")
    p.setFont("Helvetica", 14)
    p.drawString(30, height - 85, f"CATEGORÍA: {categoria} REG.: {region_loc} DOMICILIO: {calle} {numero} LOCALIDAD: {localidad} MAIL: {resploc_email}")
    p.setFont("Helvetica-Bold", 14)
    p.drawString(30, height - 100, f"TURNO: {', '.join(turnos_lista)}")
    p.drawString(550, height - 560, f"RESPONSABLE: {apellido_resp} {nombre_resp} - TEL: {resploc_telefono}")

    # Crear una lista de filas para la tabla
    tabla_data = [['4. OTROS SERVICIOS / PRÉSTAMOS']]  # Primera fila con el título
    tabla_data.append(['SERVICIO', 'TURNO', 'SALA', 'AULA', 'DOM.', 'OTRAS', 'TOTAL'])  # Encabezado real de la tabla

    # Inicializar los totales de cada columna
    total_columnas = {'SALA': 0, 'AULA': 0, 'DOMICILIO': 0, 'OTRAS': 0, 'TOTAL': 0}


    for servicio, turnos in servicios_dict.items():
        for turno, valores in turnos.items():
            fila = [
                servicio, turno,
                valores['SALA'], valores['AULA'], valores['DOMICILIO'], valores['OTRAS'], valores['TOTAL']
            ]
            tabla_data.append(fila)

            # Sumar totales por columna
            for key in total_columnas.keys():
                total_columnas[key] += valores[key]

    # Agregar fila de totales generales
    tabla_data.append(['TOTALES', '', total_columnas['SALA'], total_columnas['AULA'], total_columnas['DOMICILIO'], total_columnas['OTRAS'], total_columnas['TOTAL']])

    
    p.setFont("Helvetica-Bold", 14)
    

    # Posicionamiento de la tabla
    x_offset = 30
    y_offset = height - 100
    col_widths = [350, 80, 40, 40, 40, 40, 40]

    tabla = Table(tabla_data, colWidths=col_widths)
    tabla.setStyle(TableStyle([
        ('SPAN', (0, 0), (-1, 0)),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0),'Helvetica-Bold'),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
    ]))

    tabla.wrapOn(p, width, height)
    tabla.drawOn(p, x_offset, y_offset - (20 * len(tabla_data)))

    p.showPage()
    p.setPageSize(portrait(legal))
    

###########################################
#          INFORME PEDAGÓGICO             #
###########################################
    
        
       
    # Obtener los datos desde el modelo InformePedagogico
    datos = InformePedagogico.objects.filter(cueanexo=cueanexo, mes=mes, anio=anio).values(
        'servicio__nom_servicio', 
        'varones', 
        'total'
    )
    
    # Agrupar datos por servicio
    servicios_dict = {}

    for item in datos:
        servicio = item['servicio__nom_servicio']
        varones = item.get('varones', 0)  # Usa .get() para evitar KeyError
        total = item.get('total', 0)

        # Si el servicio no está en el diccionario, inicializarlo con valores en 0
        if servicio not in servicios_dict:
            servicios_dict[servicio] = {'VARONES': 0, 'TOTAL': 0}

        # Sumar los valores a las claves correspondientes
        servicios_dict[servicio]['VARONES'] += varones
        servicios_dict[servicio]['TOTAL'] += total

    # Obtener estilos de texto
    styles = getSampleStyleSheet()
    style_normal = styles["Normal"]
    style_bold = styles["Heading3"]

    # Función para dibujar texto con wrapOn y drawOn
    def draw_paragraph(text, x, y, style=style_normal, width=500, height=20):
        paragraph = Paragraph(text, style)
        paragraph.wrapOn(p, width, height)
        paragraph.drawOn(p, x, y)

    # Agregar encabezados estáticos
    p.setFont("Helvetica-Bold", 12)
    p.drawString(30, height - 40, "ESTADISTICA DE SERVICIOS BIBLIOTECARIOS-MENSUAL-")  
    p.setFont("Helvetica", 12)  
    p.drawString(30, height - 55, f"CUE: {cueanexo} OFICINA: {cuof_loc} MES: {mes} AÑO: {anio}")
    p.setFont("Helvetica-Bold", 12)
    p.drawString(30, height - 70, f"BIBLIOTECA: {nom_est} MODALIDAD: {oferta}")
    p.setFont("Helvetica", 12)
    p.drawString(30, height - 85, f"CATEGORÍA: {categoria} REG.: {region_loc} MAIL: {resploc_email}")
    p.drawString(30, height - 100, f"DOMICILIO: {calle} {numero} LOCALIDAD: {localidad}")
    p.setFont("Helvetica-Bold", 12)
    p.drawString(30, height - 120, f"TURNO: {', '.join(turnos_lista)}")
    p.drawString(150, height - 560, f"RESPONSABLE: {apellido_resp} {nombre_resp} - TEL: {resploc_telefono}")

    # Definir coordenadas y tamaños
    x_start = 30
    y_start = height - 150  # Ajustamos la posición inicial más arriba
    row_height = 20
    col_widths = [200, 100, 100]  # Ancho de columnas (ajusta según necesidad)

    # Dibujar la fila de título "5. INFORME PEDAGÓGICO DE SERVICIOS"
    p.setFillColor(colors.lightgrey)
    p.rect(x_start, y_start, sum(col_widths), row_height, fill=1)
    p.setFillColor(colors.whitesmoke)
    draw_paragraph("<b>5. INFORME PEDAGÓGICO DE SERVICIOS</b>", x_start + 10, y_start + 5)

    # Inicializar la posición y ajustar correctamente
    y_start -= row_height  # Ajuste de la posición para la fila de encabezado

    # Dibujar la fila de encabezado
    p.setFillColor(colors.lightgrey)
    p.rect(x_start, y_start, sum(col_widths), row_height, fill=1)
    p.setFillColor(colors.whitesmoke)
    draw_paragraph("<b>SERVICIO</b>", x_start + 5, y_start + 5)
    draw_paragraph("<b>VARONES</b>", x_start + col_widths[0] + 10, y_start + 5)
    draw_paragraph("<b>TOTAL</b>", x_start + col_widths[0] + col_widths[1] + 10, y_start + 5)

    # Ajustar y_start para las filas de datos
    y_start -= row_height  

    # Dibujar líneas verticales hasta la última fila de datos
    p.setStrokeColor(colors.black)
    p.setFillColor(colors.black)
    p.line(x_start, y_start, x_start, y_start - (len(servicios_dict) + 2) * row_height)
    p.line(x_start + col_widths[0], y_start, x_start + col_widths[0], y_start - (len(servicios_dict) + 2) * row_height)
    p.line(x_start + col_widths[0] + col_widths[1], y_start, x_start + col_widths[0] + col_widths[1], y_start - (len(servicios_dict) + 2) * row_height)
    p.line(x_start + sum(col_widths), y_start, x_start + sum(col_widths), y_start - (len(servicios_dict) + 2) * row_height)

    total_varones=0
    total_total=0
    
    # Dibujar las filas de datos
    y_current = y_start - row_height
    for servicio, valores in servicios_dict.items():
        varones = valores['VARONES']
        total = valores['TOTAL']
        draw_paragraph(servicio, x_start + 5, y_current + 5)
        draw_paragraph(str(varones), x_start + col_widths[0] + 10, y_current + 5)
        draw_paragraph(str(total), x_start + col_widths[0] + col_widths[1] + 10, y_current + 5)
        
        # Acumular totales
        total_varones += varones
        total_total += total
        
        p.line(x_start, y_current, x_start + sum(col_widths), y_current)  # Línea horizontal
        y_current -= row_height  # Mover hacia abajo

    # Fila de totales
    y_current -= row_height
    p.setFillColor(colors.lightgrey)
    p.rect(x_start, y_current, sum(col_widths), row_height, fill=1)
    p.setFillColor(colors.black)
    draw_paragraph("<b>TOTAL</b>", x_start + 5, y_current + 5)
    draw_paragraph(f"<b>{total_varones}</b>", x_start + col_widths[0] + 10, y_current + 5)
    draw_paragraph(f"<b>{total_total}</b>", x_start + col_widths[0] + col_widths[1] + 10, y_current + 5)

    # Línea final
    p.line(x_start, y_current, x_start + sum(col_widths), y_current)

    
    p.showPage()


#####################################
#     ASISTENCIA DE USUARIOS        #
#####################################
    

    p.setPageSize(landscape(legal))

    x_start = 50  # Margen izquierdo para la tabla
    y_start = height - 150  # Posición inicial de la tabla después de los encabezados
    

    # Agregar encabezados estáticos
    p.setFont("Helvetica-Bold", 14)
    p.drawString(30, height - 40, "ESTADISTICA DE SERVICIOS BIBLIOTECARIOS-MENSUAL-")  
    p.setFont("Helvetica", 14)  
    p.drawString(30, height - 55, f"CUE: {cueanexo} OFICINA: {cuof_loc} MES: {mes} AÑO: {anio}")
    p.setFont("Helvetica-Bold", 14)
    p.drawString(30, height - 70, f"BIBLIOTECA: {nom_est} MODALIDAD: {oferta}")
    p.setFont("Helvetica", 14)
    p.drawString(30, height - 85, f"CATEGORÍA: {categoria} REG.: {region_loc} DOMICILIO: {calle} {numero} LOCALIDAD: {localidad} MAIL: {resploc_email}")
    p.setFont("Helvetica-Bold", 14)
    p.drawString(30, height - 100, f"TURNO: {', '.join(turnos_lista)}")
    p.drawString(550, height - 560, f"RESPONSABLE: {apellido_resp} {nombre_resp} - TEL: {resploc_telefono}")

    # Espacio entre encabezados y la tabla
    y_start -= 50  

    # Encabezado general centrado para la tabla
    p.setFont("Helvetica-Bold", 12)
    
    # Consultar la base de datos y sumar por nivel y tipo de usuario
    asistencia = (
        AsistenciaUsuarios.objects.filter(cueanexo=cueanexo, mes=mes, anio=anio)
        .values('nivel', 'usuario')  
        .annotate(
            total=Sum('total'),
            varones=Sum('varones')
        )
    )

    # Separar datos por tipo de usuario
    asistencia_dict = {}
    for item in asistencia:
        nivel = item['nivel']
        tipo_usuario = item['usuario']
        total = item['total'] or 0  # Evitar valores None
        varones = item['varones'] or 0  # Evitar valores None

        if nivel not in asistencia_dict:
            asistencia_dict[nivel] = {
                'ALUMNOS': {'total': 0, 'varones': 0},
                'DOCENTES': {'total': 0, 'varones': 0},
            }

        asistencia_dict[nivel][tipo_usuario] = {'total': total, 'varones': varones}

    # Verificar si hay datos antes de generar la tabla
    if not asistencia_dict:
        p.setFont("Helvetica", 10)
        p.drawString(x_start, y_start - 20, "No hay datos de asistencia para este mes y año.")
    else:
        y_position = y_start - 20  # Ajuste para empezar la tabla debajo del título general
        p.setFont("Helvetica-Bold", 10)

        # Encabezados de la tabla
        table_data = [["6. - ASISTENCIA DE USUARIOS"],
            ["NIVEL", "ALUMNOS","", "DOCENTES",""],["", "Total","Varones","Total","Varones"]]

        total_alumnos = 0
        total_alumnos_varones = 0
        total_docentes = 0
        total_docentes_varones = 0

        p.setFont("Helvetica", 10)
        for nivel, datos in asistencia_dict.items():
            alumnos_total = datos['ALUMNOS']['total']
            alumnos_varones = datos['ALUMNOS']['varones']
            docentes_total = datos['DOCENTES']['total']
            docentes_varones = datos['DOCENTES']['varones']

            table_data.append([
                nivel,
                str(alumnos_total),
                str(alumnos_varones),
                str(docentes_total),
                str(docentes_varones),
            ])

            total_alumnos += alumnos_total
            total_alumnos_varones += alumnos_varones
            total_docentes += docentes_total
            total_docentes_varones += docentes_varones

        # Agregar fila de totales
        table_data.append([
            "ASISTENCIA TOTAL DE USUARIOS",
            str(total_alumnos),
            str(total_alumnos_varones),
            str(total_docentes),
            str(total_docentes_varones),
        ])

        # Crear la tabla
        table = Table(table_data, colWidths=[200, 80, 80, 80, 80])

        # Aplicar estilos a la tabla
        style = TableStyle([
            ('SPAN', (0, 0), (-1, 0)),  
            ('SPAN', (1, 1), (2, 1)),  
            ('SPAN', (3, 1), (4, 1)),  
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),  
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey), 
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),  
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),  
            ('BACKGROUND', (1, 1), (4, 1), colors.lightgrey),  
            ('GRID', (0, 0), (-1, -1), 1, colors.black)  
        ])
        table.setStyle(style)

        # Dibujar la tabla en el PDF
        table.wrapOn(p, width, height)
        table.drawOn(p, 50, y_position - (len(table_data) * 20))


    p.showPage()


###################################################
#         INSTITUCIONES PRESTA SERVICIOS          #
###################################################
            
    # Obtener datos de la base de datos
    instituciones = list(InstitucionesPrestaServicios.objects.filter(cueanexo=cueanexo, mes=mes, anio=anio)
                     .values_list('escuela', 'matricula', 'docentes', 'matricdisc', 'etnia'))

    p.setFont("Helvetica", 14)    

    # Agregar encabezados estáticos
    p.setFont("Helvetica-Bold", 14)
    p.drawString(30, height - 40, "ESTADISTICA DE SERVICIOS BIBLIOTECARIOS-MENSUAL-")  
    p.setFont("Helvetica", 14)  
    p.drawString(30, height - 55, f"CUE: {cueanexo} OFICINA: {cuof_loc} MES: {mes} AÑO: {anio}")
    p.setFont("Helvetica-Bold", 14)
    p.drawString(30, height - 70, f"BIBLIOTECA: {nom_est} MODALIDAD: {oferta}")
    p.setFont("Helvetica", 14)
    p.drawString(30, height - 85, f"CATEGORÍA: {categoria} REG.: {region_loc} DOMICILIO: {calle} {numero} LOCALIDAD: {localidad} MAIL: {resploc_email}")
    p.setFont("Helvetica-Bold", 14)
    p.drawString(30, height - 100, f"TURNO: {', '.join(turnos_lista)}")
    p.drawString(550, height - 560, f"RESPONSABLE: {apellido_resp} {nombre_resp} - TEL: {resploc_telefono}")

    # Definir encabezados de la tabla
    data = [["7. - INSTITUCIONES A LAS QUE SE PRESTA SERVICIOS"],
        ["INSTITUCIÓN EDUCATIVA", "MATRÍCULA ESCOLAR", "DOCENTES", 
         "CON DISCAPACIDAD", "ALGUNA ETNIA"]
    ]

    # Agregar datos de la base de datos a la tabla
    if instituciones:
        data.extend(instituciones)
    else:
        data.append(["No hay datos registrados","","","",""])
    
    # Crear la tabla
    table = Table(data, colWidths=[250, 80, 80, 80, 80])
        
    # Aplicar estilos a la tabla
    style = TableStyle([
        ('SPAN', (0, 0), (-1, 0)),         
        ('SPAN', (1, 1), (2, 1)),  
        ('SPAN', (3, 1), (4, 1)),  
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'), 
        ('BACKGROUND', (0, 0), (-1, 1), colors.lightgrey), 
        ('TEXTCOLOR', (0, 0), (-1, 1), colors.black), 
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8), 
        ('BACKGROUND', (1, 1), (4, 1), colors.lightgrey),  
        ('GRID', (0, 0), (-1, -1), 1, colors.black)  
    ])
    table.setStyle(style)

    # Dibujar la tabla en el PDF
    table.wrapOn(p, width, height)
    table.drawOn(p, 50, y_position - len(table_data)*20)

    p.showPage()
    
###################################
#        PROCESOS TÉCNICOS        #
###################################
   
    # Crear el canvas        
    # Crear el canvas (suponiendo que 'p' es un objeto canvas)
    p.setFont("Helvetica-Bold", 12)
    
    # Agregar encabezados estáticos
    p.setFont("Helvetica-Bold", 14)
    p.drawString(30, height - 40, "ESTADISTICA DE SERVICIOS BIBLIOTECARIOS-MENSUAL-")  
    p.setFont("Helvetica", 14)  
    p.drawString(30, height - 55, f"CUE: {cueanexo} OFICINA: {cuof_loc} MES: {mes} AÑO: {anio}")
    p.setFont("Helvetica-Bold", 14)
    p.drawString(30, height - 70, f"BIBLIOTECA: {nom_est} MODALIDAD: {oferta}")
    p.setFont("Helvetica", 14)
    p.drawString(30, height - 85, f"CATEGORÍA: {categoria} REG.: {region_loc} DOMICILIO: {calle} {numero} LOCALIDAD: {localidad} MAIL: {resploc_email}")
    p.setFont("Helvetica-Bold", 14)
    p.drawString(30, height - 100, f"TURNO: {', '.join(turnos_lista)}")
    p.drawString(550, height - 560, f"RESPONSABLE: {apellido_resp} {nombre_resp} - TEL: {resploc_telefono}")
    
    # Obtener datos desde la base de datos
    registros = ProcesosTecnicos.objects.filter(cueanexo=cueanexo, mes=mes, anio=anio).values_list('material__nom_material', 'procesos', 'total')

    # Agrupar datos por material y procesos
    datos_agrupados = defaultdict(lambda: defaultdict(int))
    procesos_unicos = set()

    for material, proceso, total in registros:
        datos_agrupados[material][proceso] += total
        procesos_unicos.add(proceso)

    procesos_unicos = sorted(procesos_unicos)

    # Crear encabezados de la tabla
    encabezados = [
        ["8. - SECTOR PROCESOS TÉCNICOS"],  # Encabezado principal
        ["Tipo de Material"] + list(procesos_unicos) + ["Subtotal"]  # Subencabezado
    ]

    # Construcción de los datos de la tabla
    tabla_datos = []
    total_general = defaultdict(int)

    for material, procesos in datos_agrupados.items():
        fila = [material]  # Primera columna con el tipo de material
        subtotal = 0

        for proceso in procesos_unicos:
            valor = procesos.get(proceso, 0)
            fila.append(valor)
            subtotal += valor
            total_general[proceso] += valor

        fila.append(subtotal)  # Agregar subtotal de la fila
        tabla_datos.append(fila)

    # Agregar fila de total general
    fila_total = ["TOTAL GENERAL"] + [total_general[proceso] for proceso in procesos_unicos] + [sum(total_general.values())]
    tabla_datos.append(fila_total)

    # Crear tabla
    data = encabezados + tabla_datos
    table = Table(data, colWidths=[200] + [90] * len(procesos_unicos) + [90])

    # Estilos de la tabla
    style = TableStyle([
        ('SPAN', (0, 0), (-1, 0)), 
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),  # Encabezados en negrita
        ('BACKGROUND', (0, 0), (-1, 1), colors.lightgrey),  # Fondo gris para encabezados
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),  
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),  # Espaciado
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),  
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),       
        ('GRID', (0, 0), (-1, -1), 1, colors.black),  # Bordes en la tabla
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),  # Centrar números
    ])
    table.setStyle(style)

    # Ajustar la posición de la tabla
    y_position = height - 200
    table.wrapOn(p, width, height)
    table_height = len(data) * 20  # Estimación de la altura de la tabla
    if y_position - table_height < 0:
        p.showPage()  # Salto de página si la tabla no cabe
        y_position = height - 200

    table.drawOn(p, 50, y_position - table_height)
    
    
    p.showPage()
    
     #########################################
    #     PLANILLAS ANEXAS DE ESTADÍSTICA   #
    #########################################
    
    width, height = landscape(legal)
    y_position = height - 50  # Margen superior
    
    agrupamientos = {
        "10. - RECURSOS ELECTRÓNICOS": range(711, 717),
        "11. - APLICACIONES": range(811, 818),
        "12. - OTROS SERVICIOS": range(911, 917),
        "13. EXTENSION BIBLIOTECARIA Y CULTURAL": range(1011, 1017),
        "14. - PLATAFORMAS": range(1111, 1118),
        "15. - PROCESOS TECNICOS": range(1211, 1217),
        "16. - ACONTECIMIENTOS": range(1311, 1317),
    }
    
    # Función para imprimir encabezados y devolver la nueva posición de y
    def imprimir_encabezados(p, y_position):
        p.setFont("Helvetica", 10)
        p.drawString(30, y_position, "ESTADÍSTICA DE SERVICIOS BIBLIOTECARIOS - MENSUAL")
        y_position -= 20
        
        p.drawString(30, y_position, f"CUE: {cueanexo}   OFICINA: {cuof_loc}   MES: {mes}   AÑO: {anio}")
        y_position -= 15
        p.drawString(30, y_position, f"BIBLIOTECA: {nom_est}   MODALIDAD: {oferta}")
        y_position -= 15
        p.drawString(30, y_position, f"CATEGORÍA: {categoria}   REG.: {region_loc}   DOMICILIO: {calle} {numero}  LOCALIDAD: {localidad}   MAIL: {resploc_email}")
        y_position -= 15
        p.drawString(30, y_position, f"TURNO: {', '.join(turnos_lista)}")
        y_position -= 30

        p.drawString(560, height - 560, f"RESPONSABLE: {apellido_resp} {nombre_resp} - TEL: {resploc_telefono}")
        y_position -= 20
        
        return y_position
    
    # Imprimir encabezados en la primera página
    #y_position = imprimir_encabezados(p, y_position)
    
    for nombre, rango in agrupamientos.items():
        registros = (
            PlanillasAnexas.objects
            .filter(cueanexo=cueanexo,mes=mes, anio=anio, servicio__cod_servicio__in=rango)
            .values("servicio__nom_servicio")
            .annotate(total_cantidad=Sum("cantidad"))
        )
        
        if not registros.exists():
            continue  # Si no hay registros, pasa al siguiente grupo
        
        datos = [[nombre, ""]]
        datos.append(["Servicio", "Total"]) # Encabezados
        total_general = 0
        
        for registro in registros:
            datos.append([registro["servicio__nom_servicio"], registro["total_cantidad"]])
            total_general += registro["total_cantidad"]
        
        datos.append(["TOTAL GENERAL", total_general])  # Agrega total general
        
        # Encabezado del grupo
        p.setFont("Helvetica-Bold", 12)
        
                
        # Crear tabla con bordes y colores
        tabla = Table(datos, colWidths=[400, 100])
        tabla.setStyle(TableStyle([
            ('SPAN', (0, 0), (-1, 0)), # Fusionar primera fila
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 0), (-1, 1), colors.lightgrey), 
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'), 
            ('GRID', (0, 0), (-1, -1), 1, colors.black),            
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'), 
            ('BOTTOMPADDING', (0, 0), (-1, 0), 5), 
            ('TOPPADDING', (0, 0), (-1, 0), 5),
        ]))
        
        # Calcular altura necesaria para la tabla
        table_height = len(datos) * 20  # Asume 20px por fila
        
        # Verificar si hay espacio suficiente para la tabla
        if y_position - table_height < 50:
            p.showPage()  # Salto de página
            y_position = height - 50  # Reajustar la posición en la nueva página
            y_position = imprimir_encabezados(p, y_position)  # Imprimir encabezados en la nueva página
        
        tabla.wrapOn(p, width, height)
        tabla.drawOn(p, 50, y_position - table_height)
        y_position -= (table_height + 30)  # Espaciado extra
        
    p.save()
    
    return response
