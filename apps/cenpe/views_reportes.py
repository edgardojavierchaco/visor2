from django.shortcuts import render
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4, landscape  
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
import qrcode
from io import BytesIO
from django.db import connection

def GenerarCertificado(request):
    """
    Genera un certificado en formato PDF para un usuario autenticado, mostrando sus datos personales y cargos docentes.

    Este certificado incluye:
    - Encabezado con información institucional.
    - Detalles de los datos personales del usuario, obtenidos de la base de datos.
    - Una tabla con los cargos y horas trabajadas.
    - Un código QR que contiene los datos completos del certificado.

    Args:
        request (HttpRequest): Objeto de la solicitud HTTP que contiene información del usuario autenticado.

    Returns:
        HttpResponse: Un archivo PDF con el certificado generado.

    Funcionalidad:
    1. Obtiene los datos personales y los cargos del usuario autenticado a partir de una consulta SQL a la base de datos.
    2. Genera un PDF con el módulo `reportlab`, incluyendo los datos personales y una tabla de cargos.
    3. Genera un código QR que contiene la información del certificado.
    4. Envía el archivo PDF generado como respuesta HTTP.
    
    Ejemplo:
        - El usuario autenticado accede a la vista, y se genera un PDF con su certificado.
        - El código QR incrustado contiene información clave del certificado, como nombre, DNI, título, cargos y fechas.

    Uso:
        Esta vista se puede integrar como parte de un sistema que genere certificados para docentes o personal administrativo.

    Notas:
        - La consulta SQL es específica a la base de datos `cenpe.certificado_cenpe`, asegurando que los datos se obtengan según el `dni` del usuario.
        - Se utiliza el módulo `qrcode` para generar un código QR y `reportlab` para generar el PDF.
    """
    
    username = request.user.username
    print(username)
    
    with connection.cursor() as cursor:
        # obtener los datos del certificado
        query = f"""
        SELECT apellidos, nombres, dni, titulo, cueanexo, cargos_horas, cant_horas, situacion_revista, fecha_desde, fecha_hasta 
        FROM cenpe.certificado_cenpe
        WHERE dni = '{username}'
        """
        cursor.execute(query)
        certificado = cursor.fetchall()  
        print('certificado:', certificado)

    # buffer para el PDF
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=landscape(A4)) 
    width, height = landscape(A4)  
    y = height - 2 * cm  
    
    # recuadro del encabezado
    c.setStrokeColorRGB(0, 0, 0)  
    c.setFillColorRGB(0.9, 0.9, 0.9) 
    c.rect(1 * cm, height - 3 * cm, width - 2 * cm, 2 * cm, fill=1)  
    
    # texto del encabezado
    c.setFont("Helvetica-Bold", 14)
    c.setFillColorRGB(0, 0, 0)
    c.drawCentredString(width / 2, height - 1.5 * cm, "Departamento Estadística Educativa - MECCyT Chaco")  
    c.drawCentredString(width / 2, height - 2.5 * cm, "Relevamiento de Docentes y no Docentes - RePEE Chaco 2024")

    # Ajustar la posición del encabezado
    y -= 2 * cm
    
    # Títulos
    c.setFont("Helvetica-Bold", 12)
    c.drawString(2 * cm, y, "Datos Personales")
    y -= 1 * cm

    # datos personales una sola vez
    if certificado:
        dato = certificado[0]  
        c.setFont("Helvetica", 10)
        c.drawString(2 * cm, y, f"Apellidos y Nombres: {dato[0]}, {dato[1]}")
        y -= 0.5 * cm
        c.drawString(2 * cm, y, f"DNI: {dato[2]}")
        y -= 0.5 * cm
        c.drawString(2 * cm, y, f"Título: {dato[3]}")
        y -= 1 * cm

    # datos detallados en forma de tabla
    c.setFont("Helvetica-Bold", 12)
    c.drawString(2 * cm, y, "Detalle de Cargos")
    y -= 1 * cm
    
    # encabezados de la tabla
    c.setFont("Helvetica-Bold", 10)
    c.drawString(2 * cm, y, "Cueanexo")
    c.drawString(4 * cm, y, "Cargo/Horas")
    c.drawString(17 * cm, y, "Cant. Horas")
    c.drawString(19 * cm, y, "Situación Revista")
    c.drawString(22 * cm, y, "Fecha Desde")
    c.drawString(25 * cm, y, "Fecha Hasta")
    y -= 0.5 * cm

    # filas de la tabla
    c.setFont("Helvetica", 10)
    row_height = 0.7 * cm  

    for dato in certificado:
        # margen inferior de la página
        if y < 2 * cm:
            c.showPage()  
            y = height - 2 * cm 
            c.setFont("Helvetica-Bold", 10)
            # Reimpresión de encabezado en una nueva página
            c.drawString(2 * cm, y, "Cueanexo")
            c.drawString(4 * cm, y, "Cargo/Horas")
            c.drawString(17 * cm, y, "Cant. Horas")
            c.drawString(19 * cm, y, "Situación Revista")
            c.drawString(22 * cm, y, "Fecha Desde")
            c.drawString(27 * cm, y, "Fecha Hasta")
            y -= 0.5 * cm
        
        c.setFont("Helvetica", 10)
        c.drawString(2 * cm, y, str(dato[4]))  # Cueanexo
        c.drawString(4 * cm, y, str(dato[5]))  # Cargo/Horas
        c.drawString(17 * cm, y, str(dato[6]))  # Cant. Horas
        c.drawString(19 * cm, y, str(dato[7]))  # Situación Revista
        c.drawString(22 * cm, y, str(dato[8]))  # Fecha Desde
        c.drawString(25 * cm, y, str(dato[9]))  # Fecha Hasta
        y -= row_height  

    # Generar el código QR 
    qr_data = "\n".join([f"{dato[2]} - {dato[0]}, {dato[1]}, {dato[3]}, {dato[4]}, {dato[5]}, {dato[6]}, {dato[7]}, {dato[8]}, {dato[9]}" for dato in certificado])
    qr = qrcode.make(qr_data)
    qr_buffer = BytesIO()
    qr.save(qr_buffer)
    qr_buffer.seek(0)
    
    # ImageReader para interpretar el contenido del buffer como una imagen
    qr_image = ImageReader(qr_buffer)
    
    # Dibujar el QR en el PDF
    c.drawImage(qr_image, width - 5 * cm, 2 * cm, 4 * cm, 4 * cm)

    # Terminar el PDF
    c.showPage()
    c.save()
    
    # Enviar el PDF como respuesta
    buffer.seek(0)
    return HttpResponse(buffer, content_type='application/pdf')


