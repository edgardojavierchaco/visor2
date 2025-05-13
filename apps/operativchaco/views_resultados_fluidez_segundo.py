from urllib import response
from django.http import JsonResponse, HttpResponse
from .models import (
    EscuelasPrimarias, 
    ExamenFluidezSegundo,      
    AlumnosPrimariaFluidez, 
    RegistroAsistenciaFluidezSegundo,
    VistaVelocidadSegundo,
    VistaPrecisionSegundo,
    VistaProsodiaSegundo,
    VistaComprensionSegundo,
)
from django.views.decorators.http import require_GET
from django.db.models import Sum
from django.shortcuts import render
from django.template.loader import render_to_string
import pdfkit
from django.db import connection
import tempfile
import os
import qrcode
import base64
from io import BytesIO
from django.conf import settings
from django.utils.timezone import now
from django.contrib.auth.decorators import login_required
from datetime import datetime

######################
# Resultados Segundo #
######################
@require_GET
def ResultadosCueanexoFluidezSegundo(request):
    usuario= request.user.username
    
    resultado_velocidad=  VistaVelocidadSegundo.objects.filter(cueanexo=usuario).values()
    resultado_precision= VistaPrecisionSegundo.objects.filter(cueanexo=usuario).values()
    resultado_prosodia= VistaProsodiaSegundo.objects.filter(cueanexo=usuario).values()
    resultado_comprension= VistaComprensionSegundo.objects.filter(cueanexo=usuario).values()
    resultado= {
        'resultado_velocidad': list(resultado_velocidad),
        'resultado_precision': list(resultado_precision),
        'resultado_prosodia': list(resultado_prosodia),
        'resultado_comprension': list(resultado_comprension),
        'usuario': usuario,
    }    
    
    print('ver los resultados', resultado)
    return JsonResponse(resultado, safe=False)

def ResultadosFluidezSegundoView(request):
    usuario= request.user.username
    query = """
            SELECT nom_est 
            FROM public.v_capa_unica_ofertas
            WHERE cueanexo = %s            
        """
    with connection.cursor() as cursor:
        cursor.execute(query, [usuario])
        rows = cursor.fetchone()
        print(rows)
    context = {
        'usuario': request.user.username,
        'nom_est': rows[0] if rows else None,
    }
    return render(request, 'operativchaco/segundo/resultados_segundo.html', context)


def exportar_pdf_segundo(request):
    usuario = request.user.username
    
    query = """
            SELECT nom_est 
            FROM public.v_capa_unica_ofertas
            WHERE cueanexo = %s            
        """
    with connection.cursor() as cursor:
        cursor.execute(query, [usuario])
        rows = cursor.fetchone()
        print(rows)

    resultado = {
        'resultado_velocidad': list(VistaVelocidadSegundo.objects.filter(cueanexo=usuario).values()),
        'resultado_precision': list(VistaPrecisionSegundo.objects.filter(cueanexo=usuario).values()),
        'resultado_prosodia': list(VistaProsodiaSegundo.objects.filter(cueanexo=usuario).values()),
        'resultado_comprension': list(VistaComprensionSegundo.objects.filter(cueanexo=usuario).values()),
    }

    titulos = {
        'resultado_velocidad': 'Velocidad',
        'resultado_precision': 'Precisión',
        'resultado_prosodia': 'Prosodia',
        'resultado_comprension': 'Comprensión'
    }

    context = {
        'resultado': resultado,
        'usuario': usuario,
        'titulos': titulos,
        'nom_est': rows[0] if rows else None,
    }

    html_string = render_to_string('operativchaco/segundo/resultados_final_segundo_pdf.html', context)

    options = {
        'encoding': 'UTF-8',
        'enable-local-file-access': None,
    }

    pdf = pdfkit.from_string(html_string, False, options=options)

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="resultados_segundo_{usuario}.pdf"'
    return response

def exportar_pdf_segundo_cueanexo(request):
    usuario = request.user.username
    
    query = """
            SELECT nom_est 
            FROM public.v_capa_unica_ofertas
            WHERE cueanexo = %s            
        """
    with connection.cursor() as cursor:
        cursor.execute(query, [usuario])
        rows = cursor.fetchone()
        print(rows)
    
    # Generación del QR con los datos de los resultados
    usuario = request.user.username
    fecha_hora = now().strftime('%Y-%m-%d %H:%M:%S')

    # Iniciar la estructura de datos del QR
    qr_data = f"Usuario: {usuario}\nEscuela: {rows}\nFecha y Hora: {fecha_hora}\n\n"

    # Crear el QR
    qr_img = qrcode.make(qr_data)
    temp_file = tempfile.NamedTemporaryFile(delete=False, dir=settings.MEDIA_ROOT)
    temp_file_path = temp_file.name + '.png'
    qr_img.save(temp_file_path)
    
    resultado = {
        'resultado_velocidad': list(VistaVelocidadSegundo.objects.filter(cueanexo=usuario).values()),
        'resultado_precision': list(VistaPrecisionSegundo.objects.filter(cueanexo=usuario).values()),
        'resultado_prosodia': list(VistaProsodiaSegundo.objects.filter(cueanexo=usuario).values()),
        'resultado_comprension': list(VistaComprensionSegundo.objects.filter(cueanexo=usuario).values()),
    }

    titulos = {
        'resultado_velocidad': 'Velocidad',
        'resultado_precision': 'Precisión',
        'resultado_prosodia': 'Prosodia',
        'resultado_comprension': 'Comprensión'
    }

    context = {
        'resultado': resultado,
        'usuario': usuario,
        'titulos': titulos,
        'nom_est': rows[0] if rows else None,
    }   
    

    html_string = render_to_string('operativchaco/segundo/resultados_cueanexo_segundo_pdf.html', context)

    options = {
        'encoding': 'UTF-8',
        'enable-local-file-access': None,
    }

    pdf = pdfkit.from_string(html_string, False, options=options)

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="resultados_segundo_{usuario}.pdf"'
    return response