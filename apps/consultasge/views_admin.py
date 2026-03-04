# apps/consultasge/views_admin.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse
from django.utils import timezone
from datetime import datetime
from io import BytesIO
import pandas as pd
from xhtml2pdf import pisa
from .utils_admin import consultas_por_gestor

@login_required
def admin_dashboard_interactivo(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Acceso denegado.")
    return render(request, "consultasge/admin_dashboard_interactivo.html", {})

@login_required
def admin_dashboard_datos(request):
    if not request.user.is_superuser:
        return JsonResponse({"error":"Acceso denegado"}, status=403)

    fecha_inicio = request.GET.get("inicio")
    fecha_fin = request.GET.get("fin")
    rango = request.GET.get("rango", "total")  # total, semanal, mensual

    try:
        if fecha_inicio:
            fecha_inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d")
        if fecha_fin:
            fecha_fin = datetime.strptime(fecha_fin, "%Y-%m-%d")
    except ValueError:
        return JsonResponse({"error":"Formato de fecha inválido"}, status=400)

    stats = consultas_por_gestor(fecha_inicio, fecha_fin)
    lista_gestores = list(stats.keys())

    data = {
        "labels": lista_gestores,
        "datasets": {
            "pendiente": [stats[g]["pendiente"] for g in lista_gestores],
            "en_proceso": [stats[g]["en_proceso"] for g in lista_gestores],
            "respondida": [stats[g]["respondida"] for g in lista_gestores],
            "cerrada": [stats[g]["cerrada"] for g in lista_gestores],
            "vencidas": [stats[g]["vencidas"] for g in lista_gestores],
            "SLA": [stats[g]["SLA_promedio"] for g in lista_gestores],
            "semanal": [stats[g]["semanal"] for g in lista_gestores],
            "mensual": [stats[g]["mensual"] for g in lista_gestores],
            "region": [stats[g]["region"] for g in lista_gestores],
            "turno": [stats[g]["turno"] for g in lista_gestores],
        }
    }
    return JsonResponse(data)

@login_required
def exportar_excel_admin(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Acceso denegado.")

    fecha_inicio = request.GET.get("inicio")
    fecha_fin = request.GET.get("fin")
    stats = consultas_por_gestor(
        datetime.strptime(fecha_inicio, "%Y-%m-%d") if fecha_inicio else None,
        datetime.strptime(fecha_fin, "%Y-%m-%d") if fecha_fin else None
    )

    df = pd.DataFrame.from_dict(stats, orient='index')
    df = df.reset_index().rename(columns={"index": "username"})
    output = BytesIO()
    df.to_excel(output, sheet_name='Reporte', index=False)
    output.seek(0)
    response = HttpResponse(output.read(),
                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="reporte_gestores.xlsx"'
    return response

@login_required
def exportar_pdf_admin(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Acceso denegado.")

    fecha_inicio = request.GET.get("inicio")
    fecha_fin = request.GET.get("fin")
    stats = consultas_por_gestor(
        datetime.strptime(fecha_inicio, "%Y-%m-%d") if fecha_inicio else None,
        datetime.strptime(fecha_fin, "%Y-%m-%d") if fecha_fin else None
    )

    html = render(request, "consultasge/admin_dashboard_pdf.html", {"stats": stats}).content
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_gestores.pdf"'
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse("Error al generar PDF", status=500)
    return response