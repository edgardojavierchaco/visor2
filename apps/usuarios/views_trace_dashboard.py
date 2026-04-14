from django.http import JsonResponse
from django.db.models import Count
from django.db.models.functions import TruncDate
from .models import UsuarioAccesoLog
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

def dashboard_data(request):

    # =========================
    # 📊 ACCESOS POR DÍA
    # =========================
    accesos_dia = (
        UsuarioAccesoLog.objects
        .annotate(fecha_dia=TruncDate('fecha'))
        .values('fecha_dia')
        .annotate(total=Count('id'))
        .order_by('fecha_dia')
    )

    accesos_labels = [x['fecha_dia'].strftime("%d/%m") for x in accesos_dia]
    accesos_data = [x['total'] for x in accesos_dia]

    # =========================
    # 📊 ACCIONES
    # =========================
    acciones = (
        UsuarioAccesoLog.objects
        .values('accion')
        .annotate(total=Count('id'))
    )

    acciones_labels = [x['accion'] for x in acciones]
    acciones_data = [x['total'] for x in acciones]

    # =========================
    # 📊 TOP USUARIOS
    # =========================
    top_users = (
        UsuarioAccesoLog.objects
        .values('username')
        .annotate(total=Count('id'))
        .order_by('-total')[:10]
    )

    top_labels = [x['username'] for x in top_users]
    top_data = [x['total'] for x in top_users]

    return JsonResponse({
        "accesos": {
            "labels": accesos_labels,
            "data": accesos_data
        },
        "acciones": {
            "labels": acciones_labels,
            "data": acciones_data
        },
        "top": {
            "labels": top_labels,
            "data": top_data
        }
    })


@login_required
def dashboard_view(request):
    return render(request, "usuarios/dashboard_trace.html")