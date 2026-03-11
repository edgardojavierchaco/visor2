from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from django.db import transaction
from django.db.models import Count

from .decorators import rol_requerido
from .models import Consulta, Adjunto
from .services import crear_consulta, notificaciones_usuario
from .forms import ConsultaForm, RespuestaForm
from .utils import progreso_sla

# --------------------------
# Dashboard Director
# --------------------------
@login_required
def dashboard(request):
    consultas_agrupadas = Consulta.objects.filter(usuario=request.user) \
        .values("estado") \
        .annotate(total=Count("id"))

    data = {
        'pendientes': 0,
        'en_proceso': 0,
        'respondidas': 0,
        'cerrada': 0,
        'total': 0
    }

    total_general = 0
    for item in consultas_agrupadas:
        estado_db = item['estado'].lower()
        cantidad = item['total']
        total_general += cantidad

        if estado_db == 'pendiente':
            data['pendientes'] = cantidad
        elif estado_db == 'en_proceso':
            data['en_proceso'] = cantidad
        elif estado_db == 'respondida':
            data['respondidas'] = cantidad
        elif estado_db == 'cerrada':
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
        messages.success(request, "Consulta creada correctamente.")
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
# Detalle Consulta (Hilo Director)
# --------------------------
@login_required
@transaction.atomic
def consulta_detalle(request, id):
    consulta = get_object_or_404(
        Consulta.objects.prefetch_related(
            'respuestas__usuario', 
            'respuestas__adjuntos_respuesta', 
            'adjuntos'
        ), 
        id=id, 
        usuario=request.user
    )
    
    if request.method == "POST":
        if consulta.estado == Consulta.Estado.CERRADA:
            messages.error(request, "La consulta está cerrada y no admite más mensajes.")
            return redirect("consultasge:consulta_detalle", id=id)

        form = RespuestaForm(request.POST, request.FILES)
        if form.is_valid():
            respuesta = form.save(commit=False)
            respuesta.consulta = consulta
            respuesta.usuario = request.user
            respuesta.save()
            
            # Guardar adjuntos múltiples
            for f in request.FILES.getlist('archivos'):
                Adjunto.objects.create(consulta=consulta, respuesta=respuesta, archivo=f)
            
            # Si el director responde, el gestor debe verla de nuevo como "En Proceso"
            consulta.estado = Consulta.Estado.EN_PROCESO
            consulta.save(update_fields=['estado'])
            
            messages.success(request, "Mensaje enviado al gestor.")
            return redirect("consultasge:consulta_detalle", id=id)
    else:
        form = RespuestaForm()

    # ✅ Aquí generamos los colores HSL para cada mensaje
    mensajes = list(consulta.respuestas.all().order_by('fecha'))
    for msg in mensajes:
        hue = (msg.usuario.id * 137) % 360  # número pseudo-aleatorio
        msg.color_hsl = f"hsl({hue}, 70%, 45%)"

    return render(request, "consultasge/detalle.html", {
        "consulta": consulta,
        "mensajes": mensajes,  # enviamos ya con color_hsl
        "form": form,
        "progreso": progreso_sla(consulta, request.user)
    })
    
@login_required
def notificaciones_consultas(request):
    stats = notificaciones_usuario(request.user)
    return JsonResponse(stats)

@login_required
def mensajes_ajax(request, id):
    consulta = get_object_or_404(Consulta, id=id)
    # Importante: prefetch para optimizar nombres y adjuntos
    respuestas = consulta.respuestas.all().order_by('fecha').select_related('usuario').prefetch_related('adjuntos_respuesta')
    
    return render(request, 'consultasge/includes/lista_mensajes.html', {
        'respuestas': respuestas,
        'consulta': consulta
    })