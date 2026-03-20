import json
from django.db import connection
from django.shortcuts import render
from django.http import JsonResponse
from pyparsing import C
from .models import GenerarInforme
from apps.consultasge.models import CapaUnicaOfertas
from django.db.models import Func, F, Value
import re

def generar_informe(request):
    # 🔹 Obtener usuario logueado correctamente
    usuario_logueado = request.user.username  
    usuario_limpio = re.sub(r'\D', '', usuario_logueado)
    print("Usuario logueado:", usuario_logueado)  # Debug: Verificar el usuario logueado
        
    # 🔹 Obtener todos los cueanexos que cumplan la condición
    cueanexos_qs = CapaUnicaOfertas.objects.annotate(
        cuit_limpio=Func(
            F('resploc_cuitcuil'),
            Value('-'),
            Value(''),
            function='REPLACE'
            )
        ).filter(
            cuit_limpio=usuario_limpio,
            oferta='Común - Servicios complementarios ',
            acronimo='BI'
        ).values_list('cueanexo', flat=True)
        
    cueanexos = list(cueanexos_qs)
    cue=cueanexos[0] if cueanexos else None
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT DISTINCT cueanexo FROM v_capa_unica_ofertas WHERE acronimo ILIKE 'BI%'")
            ofertas = cursor.fetchall()
            print("✅ Ofertas encontradas:", ofertas)  # Depuración
    except Exception as e:
        print("❌ Error en la consulta SQL:", e)  # Depuración
        
    cant_ofertas=len(ofertas)
    print("✅ Cantidad de ofertas:", cant_ofertas)  # Depuración
    
    ultimo_informe = GenerarInforme.objects.filter(cueanexo=cue).order_by('-annos', '-meses').first()

    if ultimo_informe:
        mes = ultimo_informe.meses
        anio = ultimo_informe.annos
            
    informes = GenerarInforme.objects.filter(cueanexo=cue, meses=mes, annos=anio)
    total_generados = informes.filter(estado='GENERADO').count()
    total_enviados = informes.filter(estado='ENVIADO').count()
    total_faltantes=cant_ofertas-total_enviados

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':  # Detecta AJAX
        informes_data = list(informes.values('cueanexo', 'meses', 'annos', 'estado', 'f_generacion', 'f_envio'))
        return JsonResponse({
            'informes': informes_data,
            'total_generados': total_generados,
            'total_enviados': total_enviados,
            'total_faltantes': total_faltantes,
            'no_registros_message': "No hay registros disponibles" if not informes_data else "",
        })

    context = {
        'informes': informes,
        'total_generados': total_generados,
        'total_enviados': total_enviados,
        'total_faltantes': total_faltantes,
    }
    return render(request, 'biblioteca/generar_informe_list.html', context)

def generar_informe_list(request):
    print("📌 La vista se ejecutó")  # Depuración
    cue = request.GET.get('cueanexo', '').strip()
    meses = request.GET.get('meses', '').strip()
    annos = request.GET.get('annos', '').strip()
    
    print('datos enviados',cue, meses, annos)  # Debugging

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT DISTINCT cueanexo FROM v_capa_unica_ofertas WHERE acronimo ILIKE 'BI%'")
            ofertas = cursor.fetchall()
            print("✅ Ofertas encontradas:", ofertas)  # Depuración
    except Exception as e:
        print("❌ Error en la consulta SQL:", e)  # Depuración
        
    cant_ofertas=len(ofertas)
    print("✅ Cantidad de ofertas:", cant_ofertas)  # Depuración
    
    
    # Construcción dinámica de filtros
    filtros = {}
    if cue:
        filtros["cueanexo"] = cue
    if meses:
        filtros["meses"] = meses
    if annos.isdigit():  # Verifica que el año sea un número válido
        filtros["annos"] = int(annos)

    informes = GenerarInforme.objects.filter(**filtros)
    total_generados = informes.filter(estado='GENERADO').count()
    total_enviados = informes.filter(estado='ENVIADO').count()
    total_faltantes=cant_ofertas-total_enviados
    
    print('informes',informes)  # Debugging
    print("Informes encontrados:", informes.count())

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':  # Detecta AJAX
        informes_data = list(informes.values('cueanexo', 'meses', 'annos', 'estado', 'f_generacion', 'f_envio'))
        return JsonResponse({
            'informes': informes_data,
            'total_generados': total_generados,
            'total_enviados': total_enviados,
            'total_faltantes': total_faltantes,
            'no_registros_message': "No hay registros disponibles" if not informes_data else "",
        })

    context = {
        'informes': informes,
        'total_generados': total_generados,
        'total_enviados': total_enviados,
        'total_faltantes': total_faltantes
    }
    return render(request, 'biblioteca/generar_informe_list.html', context)
