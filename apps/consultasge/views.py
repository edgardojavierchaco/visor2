# views.py

from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .decorators import rol_requerido
from .models import Consulta, Adjunto
from .services import crear_consulta, notificaciones_usuario
from .forms import ConsultaForm
from django.db.models import Count
from .utils import validar_consulta_regional, filtrar_vencidas, progreso_sla, horas_habiles_transcurridas, SLA_HORAS_DEFAULT

# --------------------------
# Dashboard Director
# --------------------------
@login_required
def dashboard(request):
    # 1. Obtenemos los conteos agrupados por estado desde la BD
    consultas_agrupadas = Consulta.objects.filter(usuario=request.user) \
        .values("estado") \
        .annotate(total=Count("id"))

    # 2. Inicializamos el diccionario con ceros para evitar errores en el HTML/JS
    # Importante: Las llaves aquí deben ser IGUALES a las variables del HTML
    data = {
        'pendientes': 0,
        'en_proceso': 0,
        'respondidas': 0,
        'cerrada': 0,
        'total': 0
    }

    # 3. Mapeamos los resultados de la BD a nuestras variables del template
    # Ajusta los strings de la izquierda ('PENDIENTE', etc) a como los tengas en tu MODELO
    total_general = 0
    for item in consultas_agrupadas:
        estado_db = item['estado'].upper()  # Normalizamos a mayúsculas para comparar
        cantidad = item['total']
        total_general += cantidad

        if estado_db == 'PENDIENTE':
            data['pendientes'] = cantidad
        elif estado_db == 'EN_PROCESO':
            data['en_proceso'] = cantidad
        elif estado_db == 'RESPONDIDA':
            data['respondidas'] = cantidad
        elif estado_db == 'CERRADA':
            data['cerrada'] = cantidad

    data['total'] = total_general

    return render(request, "consultasge/dashboard.html", data)

# --------------------------
# Nueva Consulta
# --------------------------
@login_required
@rol_requerido("Director/a")
def nueva_consulta(request):
    form = ConsultaForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        consulta = crear_consulta(
            director=request.user,
            asunto=form.cleaned_data["asunto"],
            mensaje=form.cleaned_data["mensaje"],
            categoria=form.cleaned_data["categoria"],
            archivos=request.FILES.getlist("archivos")
        )
        return redirect("consultasge:consultas_lista")
    return render(request, "consultasge/nueva.html", {"form": form})

# --------------------------
# Lista consultas Director
# --------------------------
@login_required
@rol_requerido("Director/a")
def consultas_lista(request):
    consultas = Consulta.objects.filter(usuario=request.user).order_by("-fecha_creacion")
    return render(request, "consultasge/lista.html", {"consultas": consultas})

# --------------------------
# Detalle Consulta
# --------------------------
@login_required
def consulta_detalle(request, id):
    consulta = get_object_or_404(Consulta, id=id, usuario=request.user)
    return render(request, "consultasge/detalle.html", {"consulta": consulta})

# --------------------------
# Notificaciones
# --------------------------
@login_required
def notificaciones_consultas(request):
    stats = notificaciones_usuario(request.user)
    return JsonResponse(stats)