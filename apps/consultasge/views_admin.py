from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse
from django.utils import timezone
from datetime import datetime
from io import BytesIO
import pandas as pd
from xhtml2pdf import pisa
from .utils_admin import consultas_por_gestor
from apps.usuarios.models_regional import RegionalUsuariosAgentes

# Función auxiliar para evitar repetición de lógica de fechas
def obtener_fechas_y_region(request):
    inicio_str = request.GET.get("inicio")
    fin_str = request.GET.get("fin")
    region = request.GET.get("region") # Capturamos la región

    inicio = None
    fin = None

    if inicio_str:
        inicio = timezone.make_aware(datetime.strptime(inicio_str, "%Y-%m-%d"))
    if fin_str:
        fin = timezone.make_aware(datetime.strptime(fin_str, "%Y-%m-%d"))
    
    return inicio, fin, region

@login_required
def admin_dashboard_interactivo(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Acceso denegado.")
    
    # Obtenemos las regiones únicas para el selector del filtro
    regiones = RegionalUsuariosAgentes.objects.filter(activo=True).values_list('region_loc', flat=True).distinct()
    return render(request, "consultasge/admin_dashboard_interactivo.html", {"regiones": regiones})

@login_required
def admin_dashboard_datos(request):
    if not request.user.is_superuser:
        return JsonResponse({"error": "Acceso denegado"}, status=403)

    try:
        inicio, fin, region = obtener_fechas_y_region(request)
        # Desempaquetamos los dos valores que devuelve la función corregida
        stats, kpis = consultas_por_gestor(inicio, fin, region)
    except (ValueError, TypeError):
        return JsonResponse({"error": "Parámetros inválidos"}, status=400)

    # Preparar listas para Chart.js
    labels = list(stats.keys())
    datasets = {
        "pendiente": [v["pendiente"] for v in stats.values()],
        "en_proceso": [v["en_proceso"] for v in stats.values()],
        "respondida": [v["respondida"] for v in stats.values()],
        "cerrada": [v["cerrada"] for v in stats.values()],
        "vencidas": [v["vencidas"] for v in stats.values()],
        "SLA": [v["SLA_promedio"] for v in stats.values()],
    }

    return JsonResponse({
        "labels": labels,
        "datasets": datasets,
        "kpis": kpis  # Enviamos los totales para los cuadros superiores
    })

@login_required
def exportar_excel_admin(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden()
    
    try:
        inicio, fin, region = obtener_fechas_y_region(request)
        stats, _ = consultas_por_gestor(inicio, fin, region)
    except:
        return HttpResponse("Error en los parámetros", status=400)

    if not stats:
        return HttpResponse("No hay datos para exportar")

    df = pd.DataFrame.from_dict(stats, orient='index')
    df = df.reset_index().rename(columns={"index": "username"})
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Reporte Gestores', index=False)
    
    output.seek(0)
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="reporte_admin_consultas.xlsx"'
    return response

@login_required
def exportar_pdf_admin(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden()

    try:
        inicio, fin, region = obtener_fechas_y_region(request)
        stats, kpis = consultas_por_gestor(inicio, fin, region)
    except:
        return HttpResponse("Error en los parámetros", status=400)

    context = {
        "stats": stats,
        "kpis": kpis,
        "fecha_reporte": timezone.now(),
        "region_filtro": region or "Todas"
    }
    
    html = render(request, "consultasge/admin_dashboard_pdf.html", context).content
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="reporte_{timezone.now().date()}.pdf"'
    
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse("Error al generar PDF", status=500)
    return response