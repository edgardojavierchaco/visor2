import re
from urllib import response
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_GET
from django.db.models import Sum
from django.shortcuts import render
from django.template.loader import render_to_string
import pdfkit
from django.db import connection
from django.db.models import Count, Avg, F, FloatField, ExpressionWrapper
from decimal import Decimal, ROUND_HALF_UP
import tempfile
import os
import qrcode
import base64
from io import BytesIO
from django.conf import settings
from django.utils.timezone import now
from django.contrib.auth.decorators import login_required
from datetime import datetime
from .models import (    
    VistaGeneralLenguaReg,
    VistaEvaluarLenguaReg,
    VistaExtraerLenguaReg,
    VistaInterpretarLenguaReg,
    VistaEscrituraLenguaReg,
    VistaGeneralMatematicaReg,
    VistaReconocimientoMatematicaReg,
    VistaResolucionMatematicaReg,
    VistaComunicacionMatematicaReg,
)


def redondear(queryset):
    for item in queryset:
        if item['porcentaje'] is not None:
            item['porcentaje'] = Decimal(item['porcentaje']).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return list(queryset)


#####################
# Resultados Lengua #
#####################
@require_GET
def ResultadosRegionLengua(request):
    region=request.GET.get('region')
    print('region', region)
    
    if not region:
        return JsonResponse({'error': 'Region not provided'}, status=400)
    
    if region == 'Todas':
        # Agrupar por nivel y calcular la suma de cantidad y el promedio de porcentaje
        resultado_gral = VistaGeneralLenguaReg.objects.values('nivel').annotate(
            cantidad=Sum('cantidad'),
            porcentaje=Avg('porcentaje')
        )
        resultado_evaluar = VistaEvaluarLenguaReg.objects.values('nivel').annotate(
            cantidad=Sum('cantidad'),
            porcentaje=Avg('porcentaje')
        )
        resultado_extraer = VistaExtraerLenguaReg.objects.values('nivel').annotate(
            cantidad=Sum('cantidad'),
            porcentaje=Avg('porcentaje')
        )
        resultado_escribir = VistaEscrituraLenguaReg.objects.values('nivel').annotate(
            cantidad=Sum('cantidad'),
            porcentaje=Avg('porcentaje')
        )
        resultado_interpretar = VistaInterpretarLenguaReg.objects.values('nivel').annotate(
            cantidad=Sum('cantidad'),
            porcentaje=Avg('porcentaje')
        )

        resultado = {
            'resultado_gral': redondear(resultado_gral),
            'resultado_evaluar': redondear(resultado_evaluar),
            'resultado_extraer': redondear(resultado_extraer),
            'resultado_escribir': redondear(resultado_escribir),
            'resultado_interpretar': redondear(resultado_interpretar),
            'usuario': region,
        }
    else:
        resultado_gral=  VistaGeneralLenguaReg.objects.filter(region=region).values()
        resultado_evaluar= VistaEvaluarLenguaReg.objects.filter(region=region).values()
        resultado_extraer= VistaExtraerLenguaReg.objects.filter(region=region).values()
        resultado_escribir= VistaEscrituraLenguaReg.objects.filter(region=region).values()
        resultado_interpretar= VistaInterpretarLenguaReg.objects.filter(region=region).values()
    resultado= {
        'resultado_gral': list(resultado_gral) if resultado_gral else [],
        'resultado_evaluar': list(resultado_evaluar) if resultado_evaluar else [],
        'resultado_extraer': list(resultado_extraer) if resultado_extraer else [],
        'resultado_escribir': list(resultado_escribir) if resultado_escribir else [],
        'resultado_interpretar': list(resultado_interpretar) if resultado_interpretar else [],
        'usuario': region,
    }    
    
    print('ver los resultados', resultado)
    return JsonResponse(resultado)


def ResultadosLenguaRegionalView(request):
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



#########################
# Resultados Matematica #
#########################
@require_GET
def ResultadosRegionMatematica(request):
    region=request.GET.get('region')
    print('region', region)
    
    if not region:
        return JsonResponse({'error': 'Region not provided'}, status=400)

    if region == 'Todas':
        # Agrupar por nivel y calcular la suma de cantidad y el promedio de porcentaje
        resultado_gral = VistaGeneralMatematicaReg.objects.values('nivel').annotate(
            cantidad=Sum('cantidad'),
            porcentaje=Avg('porcentaje')
        )
        resultado_comunicacion = VistaComunicacionMatematicaReg.objects.values('nivel').annotate(
            cantidad=Sum('cantidad'),
            porcentaje=Avg('porcentaje')
        )
        resultado_reconocimiento = VistaReconocimientoMatematicaReg.objects.values('nivel').annotate(
            cantidad=Sum('cantidad'),
            porcentaje=Avg('porcentaje')
        )
        resultado_resolucion = VistaResolucionMatematicaReg.objects.values('nivel').annotate(
            cantidad=Sum('cantidad'),
            porcentaje=Avg('porcentaje')
        )  
        resultado = {
            'resultado_gral': redondear(resultado_gral),
            'resultado_comunicacion': redondear(resultado_comunicacion),
            'resultado_reconocimiento': redondear(resultado_reconocimiento),
            'resultado_resolucion': redondear(resultado_resolucion),
            'usuario': region,
        }      
    else:
        resultado_gral=  VistaGeneralMatematicaReg.objects.filter(region=region).values()
        resultado_comunicacion= VistaComunicacionMatematicaReg.objects.filter(region=region).values()
        resultado_reconocimiento= VistaReconocimientoMatematicaReg.objects.filter(region=region).values()
        resultado_resolucion= VistaResolucionMatematicaReg.objects.filter(region=region).values()
    resultado= {
        'resultado_gral': list(resultado_gral) if resultado_gral else [],
        'resultado_comunicacion': list(resultado_comunicacion) if resultado_comunicacion else [],
        'resultado_reconocimiento': list(resultado_reconocimiento) if resultado_reconocimiento else [],
        'resultado_resolucion': list(resultado_resolucion) if resultado_resolucion else [],
        'usuario': region,
    }
    print('ver los resultados', resultado)
    return JsonResponse(resultado, safe=False)


def ResultadosMatematicaRegionalView(request):
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


@login_required
def exportar_pdf_resultados_finales(request):    
    materia = request.GET.get('materia')  # "lengua" o "matematica"
    region = request.GET.get('region')    # puede ser "Todas" o una regional

    if materia not in ['lengua', 'matematica']:
        return HttpResponse("Parámetro 'materia' inválido", status=400)

    # Títulos según materia
    titulos = {
        'resultado_gral': 'Resultado General',
        'resultado_evaluar': 'Evaluar' if materia == 'lengua' else 'Comunicación',
        'resultado_extraer': 'Extraer' if materia == 'lengua' else 'Reconocimiento',
        'resultado_escribir': 'Escribir' if materia == 'lengua' else 'Resolución',
    }

    # Modelos según materia
    if materia == 'lengua':
        modelos = {
            'resultado_gral': VistaGeneralLenguaReg,
            'resultado_evaluar': VistaEvaluarLenguaReg,
            'resultado_extraer': VistaExtraerLenguaReg,
            'resultado_escribir': VistaEscrituraLenguaReg,
            'resultado_interpretar': VistaInterpretarLenguaReg,
        }
        titulos['resultado_interpretar'] = 'Interpretar'
    else:
        modelos = {
            'resultado_gral': VistaGeneralMatematicaReg,
            'resultado_evaluar': VistaComunicacionMatematicaReg,
            'resultado_extraer': VistaReconocimientoMatematicaReg,
            'resultado_escribir': VistaResolucionMatematicaReg,
        }
        # No se agrega resultado_interpretar en matemática

    resultado = {}
    niveles_orden = ['Debajo del Básico', 'Básico', 'Satisfactorio', 'Avanzado']
    totales = {}

    for key, modelo in modelos.items():
        if region == 'Todas':
            queryset = modelo.objects.values('nivel').annotate(cantidad=Sum('cantidad'))
        else:
            queryset = modelo.objects.filter(region=region).values('nivel').annotate(cantidad=Sum('cantidad'))

        total = sum(item['cantidad'] for item in queryset)
        for item in queryset:
            item['porcentaje'] = round((item['cantidad'] / total) * 100, 2) if total > 0 else 0

        ordenados = []
        for nivel in niveles_orden:
            item = next((i for i in queryset if i['nivel'] == nivel), None)
            if item:
                ordenados.append(item)

        otros = [i for i in queryset if i['nivel'] not in niveles_orden]
        ordenados.extend(otros)

        resultado[key] = ordenados
        totales[key] = total

    # Generación del QR con los datos de los resultados
    usuario = request.user.username
    fecha_hora = now().strftime('%Y-%m-%d %H:%M:%S')

    # Iniciar la estructura de datos del QR
    qr_data = f"Usuario: {usuario}\nRegión: {region}\nMateria: {materia}\nFecha y Hora: {fecha_hora}\n\n"

    # Añadir los resultados por cada tipo
    for key, result in resultado.items():
        qr_data += f"\n{titulos[key]}:\n"
        for item in result:
            qr_data += f"  - Nivel: {item['nivel']} | Cantidad: {item['cantidad']} | Porcentaje: {item['porcentaje']}%\n"

    # Crear el QR
    qr_img = qrcode.make(qr_data)
    temp_file = tempfile.NamedTemporaryFile(delete=False, dir=settings.MEDIA_ROOT)
    temp_file_path = temp_file.name + '.png'
    qr_img.save(temp_file_path)

    
    context = {
        'resultado': resultado,
        'usuario': region,
        'titulos': titulos,
        'totales': totales,
        'qr_path': temp_file_path,
    }

    print('ver los resultados contexto', context)

    template = (
        'operativchaco/lengua/resultados_final_lengua_pdf.html'
        if materia == 'lengua'
        else 'operativchaco/matematica/resultados_final_matematica_pdf.html'
    )

    html_string = render_to_string(template, context)

    options = {
        'encoding': 'UTF-8',
        'enable-local-file-access': None,
    }

    pdf = pdfkit.from_string(html_string, False, options=options)

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="resultados_{materia}_{region}.pdf"'
    return response
