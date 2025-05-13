from urllib import response
from django.http import JsonResponse, HttpResponse
from .models import (
    EscuelasSecundarias, 
    ExamenLenguaAlumno, 
    ExamenMatematicaAlumno, 
    AlumnosSecundariaDiagnostico, 
    RegistroAsistenciaLengua, 
    RegistroAsistenciaMatematica,
    VistaGeneralLengua,
    VistaEvaluarLengua,
    VistaExtraerLengua,
    VistaInterpretarLengua,
    VistaEscrituraLengua,
    VistaGeneralMatematica,
    VistaReconocimientoMatematica,
    VistaResolucionMatematica,
    VistaComunicacionMatematica,
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

#####################
# Resultados Lengua #
#####################
@require_GET
def ResultadosCueanexoLengua(request):
    usuario= request.user.username
    
    resultado_gral=  VistaGeneralLengua.objects.filter(cueanexo=usuario).values()
    resultado_evaluar= VistaEvaluarLengua.objects.filter(cueanexo=usuario).values()
    resultado_extraer= VistaExtraerLengua.objects.filter(cueanexo=usuario).values()
    resultado_escribir= VistaEscrituraLengua.objects.filter(cueanexo=usuario).values()
    resultado_interpretar= VistaInterpretarLengua.objects.filter(cueanexo=usuario).values()
    resultado= {
        'resultado_gral': list(resultado_gral),
        'resultado_evaluar': list(resultado_evaluar),
        'resultado_extraer': list(resultado_extraer),
        'resultado_escribir': list(resultado_escribir),
        'resultado_interpretar': list(resultado_interpretar),
        'usuario': usuario,
    }    
    
    print('ver los resultados', resultado)
    return JsonResponse(resultado, safe=False)

def ResultadosLenguaView(request):
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
    return render(request, 'operativchaco/lengua/resultados_lengua.html', context)


def exportar_pdf_lengua(request):
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
        'resultado_gral': list(VistaGeneralLengua.objects.filter(cueanexo=usuario).values()),
        'resultado_evaluar': list(VistaEvaluarLengua.objects.filter(cueanexo=usuario).values()),
        'resultado_extraer': list(VistaExtraerLengua.objects.filter(cueanexo=usuario).values()),
        'resultado_escribir': list(VistaEscrituraLengua.objects.filter(cueanexo=usuario).values()),
        'resultado_interpretar': list(VistaInterpretarLengua.objects.filter(cueanexo=usuario).values()),
    }

    titulos = {
        'resultado_gral': 'Resultado General',
        'resultado_evaluar': 'Evaluar',
        'resultado_extraer': 'Extraer',
        'resultado_escribir': 'Escribir',
        'resultado_interpretar': 'Interpretar'
    }

    context = {
        'resultado': resultado,
        'usuario': usuario,
        'titulos': titulos,
        'nom_est': rows[0] if rows else None,
    }

    html_string = render_to_string('operativchaco/lengua/resultados_final_lengua_pdf.html', context)

    options = {
        'encoding': 'UTF-8',
        'enable-local-file-access': None,
    }

    pdf = pdfkit.from_string(html_string, False, options=options)

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="resultados_lengua_{usuario}.pdf"'
    return response

#########################
# Resultados Matematica #
#########################
@require_GET
def ResultadosCueanexoMatematica(request):
    usuario= request.user.username
    resultado_gral=  VistaGeneralMatematica.objects.filter(cueanexo=usuario).values()
    resultado_comunicacion= VistaComunicacionMatematica.objects.filter(cueanexo=usuario).values()
    resultado_reconocimiento= VistaReconocimientoMatematica.objects.filter(cueanexo=usuario).values()
    resultado_resolucion= VistaResolucionMatematica.objects.filter(cueanexo=usuario).values()
    resultado= {
        'resultado_gral': list(resultado_gral),
        'resultado_comunicacion': list(resultado_comunicacion),
        'resultado_reconocimiento': list(resultado_reconocimiento),
        'resultado_resolucion': list(resultado_resolucion),
        'usuario': usuario,
    }
    print('ver los resultados', resultado)
    return JsonResponse(resultado, safe=False)


def ResultadosMatematicaView(request):
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
    return render(request, 'operativchaco/matematica/resultados_matematica.html', context)


def exportar_pdf_matematica(request):
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
        'resultado_gral': list(VistaGeneralMatematica.objects.filter(cueanexo=usuario).values()),
        'resultado_comunicacion': list(VistaComunicacionMatematica.objects.filter(cueanexo=usuario).values()),
        'resultado_reconocimiento': list(VistaReconocimientoMatematica.objects.filter(cueanexo=usuario).values()),
        'resultado_resolucion': list(VistaResolucionMatematica.objects.filter(cueanexo=usuario).values()),
    }
    titulos = {
        'resultado_gral': 'Resultado General',
        'resultado_comunicacion': 'Comunicacion en Matemática',
        'resultado_reconocimiento': 'Reconocimiento de Conceptos',
        'resultado_resolucion': 'Resolucion de Situaciones en Contextos Intra y/o extra matemáticos'
    }
    context = {
        'resultado': resultado,
        'usuario': usuario,
        'titulos': titulos,
        'nom_est': rows[0] if rows else None,
    }
    html_string = render_to_string('operativchaco/matematica/resultados_final_matematica_pdf.html', context)
    options = {
        'encoding': 'UTF-8',
        'enable-local-file-access': None,
    }
    pdf = pdfkit.from_string(html_string, False, options=options)
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="resultados_matematica_{usuario}.pdf"'
    return response



def exportar_pdf_lengua_cueanexo(request):
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
        'resultado_gral': list(VistaGeneralLengua.objects.filter(cueanexo=usuario).values()),
        'resultado_evaluar': list(VistaEvaluarLengua.objects.filter(cueanexo=usuario).values()),
        'resultado_extraer': list(VistaExtraerLengua.objects.filter(cueanexo=usuario).values()),
        'resultado_escribir': list(VistaEscrituraLengua.objects.filter(cueanexo=usuario).values()),
        'resultado_interpretar': list(VistaInterpretarLengua.objects.filter(cueanexo=usuario).values()),
    }

    titulos = {
        'resultado_gral': 'Resultado General',
        'resultado_evaluar': 'Evaluar',
        'resultado_extraer': 'Extraer',
        'resultado_escribir': 'Escribir',
        'resultado_interpretar': 'Interpretar'
    }

    context = {
        'resultado': resultado,
        'usuario': usuario,
        'titulos': titulos,
        'nom_est': rows[0] if rows else None,
    }   
    

    html_string = render_to_string('operativchaco/lengua/resultados_cueanexo_lengua_pdf.html', context)

    options = {
        'encoding': 'UTF-8',
        'enable-local-file-access': None,
    }

    pdf = pdfkit.from_string(html_string, False, options=options)

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="resultados_lengua_{usuario}.pdf"'
    return response


def exportar_pdf_matematica_cueanexo(request):
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
        'resultado_gral': list(VistaGeneralMatematica.objects.filter(cueanexo=usuario).values()),
        'resultado_comunicacion': list(VistaComunicacionMatematica.objects.filter(cueanexo=usuario).values()),
        'resultado_reconocimiento': list(VistaReconocimientoMatematica.objects.filter(cueanexo=usuario).values()),
        'resultado_resolucion': list(VistaResolucionMatematica.objects.filter(cueanexo=usuario).values()),
    }
    titulos = {
        'resultado_gral': 'Resultado General',
        'resultado_comunicacion': 'Comunicacion en Matemática',
        'resultado_reconocimiento': 'Reconocimiento de Conceptos',
        'resultado_resolucion': 'Resolucion de Situaciones en Contextos Intra y/o extra matemáticos'
    }
    context = {
        'resultado': resultado,
        'usuario': usuario,
        'titulos': titulos,
        'nom_est': rows[0] if rows else None,
    }
    html_string = render_to_string('operativchaco/matematica/resultados_cueanexo_matematica_pdf.html', context)
    options = {
        'encoding': 'UTF-8',
        'enable-local-file-access': None,
    }
    pdf = pdfkit.from_string(html_string, False, options=options)
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="resultados_matematica_{usuario}.pdf"'
    return response