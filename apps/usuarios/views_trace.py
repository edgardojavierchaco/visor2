# usuarios/views_trace.py

from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Count, Max
from .models import UsuarioAccesoLog


# ==========================
# PANEL
# ==========================
def trazabilidad_panel(request):
    return render(request, "usuarios/trazabilidad.html")


# ==========================
# DATA PRINCIPAL
# ==========================
def trazabilidad_data(request):
    print("🔍 PARAMS:", request.GET.dict())
    print("🔍 USERNAME RAW:", request.GET.get("username"))
    print("📊 TOTAL LOGS:", UsuarioAccesoLog.objects.count())

    logs = UsuarioAccesoLog.objects.all().order_by("-fecha")

    username = request.GET.get("username")
    accion = request.GET.get("accion")
    fecha_desde = request.GET.get("desde")
    fecha_hasta = request.GET.get("hasta")

    if username:
        username = username.strip()
        logs = logs.filter(username=username)

    if accion:
        logs = logs.filter(accion=accion)

    if fecha_desde:
        logs = logs.filter(fecha__date__gte=fecha_desde)

    if fecha_hasta:
        logs = logs.filter(fecha__date__lte=fecha_hasta)

    logs = logs[:500]  # 🔥 LIMIT DESPUÉS DEL FILTRO

    data = [
        {
            "fecha": l.fecha.strftime("%d/%m/%Y %H:%M"),
            "username": l.username,
            "accion": l.accion,
            "ip": l.ip or "-",
            "path": l.path
        }
        for l in logs
    ]

    return JsonResponse({"data": data})


# ==========================
# RESUMEN POR USUARIO
# ==========================
def trazabilidad_resumen(request):

    qs = UsuarioAccesoLog.objects.values("username").annotate(
        total=Count("id"),
        ultimo=Max("fecha")
    ).order_by("-total")

    data = []

    for x in qs:
        data.append({
            "username": x["username"],
            "total": x["total"],
            "ultimo": x["ultimo"].strftime("%d/%m/%Y %H:%M")
        })

    return JsonResponse({"data": data})


# ==========================
# LOGS POR USUARIO
# ==========================
def trazabilidad_usuario(request, username):

    logs = UsuarioAccesoLog.objects.filter(
        username=username
    )[:100]

    data = [
        {
            "fecha": l.fecha.strftime("%d/%m/%Y %H:%M"),
            "accion": l.accion,
            "ip": l.ip,
            "path": l.path
        }
        for l in logs
    ]

    return JsonResponse({"logs": data})