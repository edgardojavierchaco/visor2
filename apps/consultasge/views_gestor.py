from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.contrib import messages
from apps.usuarios.models_regional import RegionalUsuariosAgentes
from django.views.decorators.http import require_POST
from .decorators import rol_requerido
from .models import Consulta, Respuesta, Adjunto
from .forms import RespuestaForm
from .utils import validar_consulta_regional, filtrar_vencidas

# --------------------------
# Gestor: Lista consultas
# --------------------------
@login_required
@rol_requerido("Gestor")
def gestor_consultas(request):
    perfiles = RegionalUsuariosAgentes.objects.filter(
        usuario=request.user.username,
        activo=True
    )
    if not perfiles.exists():
        messages.error(request, "No tiene regional asignada.")
        return redirect("home")
        
    region = perfiles.first().region_loc
    consultas = Consulta.objects.filter(region=region).order_by("-fecha_creacion")
    
    estado = request.GET.get("estado")
    if estado in ["pendiente", "en_proceso", "respondida", "cerrada"]:
        consultas = consultas.filter(estado=estado)
    elif estado == "vencidas":
        consultas = filtrar_vencidas(consultas)
        
    return render(request, "consultasge/gestor_lista.html", {
        "consultas": consultas, 
        "estado_actual": estado
    })

# --------------------------
# Gestor: Responder consulta (Atención Hilo)
# --------------------------
@login_required
@rol_requerido("Gestor")
@transaction.atomic
def gestor_responder(request, pk):
    consulta = get_object_or_404(
        Consulta.objects.select_for_update().prefetch_related(
            'respuestas__usuario', 
            'respuestas__adjuntos_respuesta'
        ), 
        pk=pk
    )
    validar_consulta_regional(consulta, request.user)

    if consulta.estado == Consulta.Estado.CERRADA:
        messages.warning(request, "Este caso ya se encuentra cerrado.")
        return redirect("consultasge:gestor_consultas")

    # Al abrir una consulta pendiente, pasa a "En Proceso"
    if consulta.estado == Consulta.Estado.PENDIENTE:
        consulta.pasar_a_en_proceso()

    if request.method == "POST":
        form = RespuestaForm(request.POST, request.FILES)
        if form.is_valid():
            respuesta = form.save(commit=False)
            respuesta.consulta = consulta
            respuesta.usuario = request.user
            respuesta.save()
            
            # Guardar adjuntos múltiples
            for f in request.FILES.getlist('archivos'):
                Adjunto.objects.create(consulta=consulta, respuesta=respuesta, archivo=f)
            
            # El gestor marca la consulta como respondida
            consulta.pasar_a_respondida()
            
            messages.success(request, "Respuesta enviada correctamente.")
            return redirect("consultasge:gestor_responder", pk=pk)
    else:
        form = RespuestaForm()
        
    return render(request, "consultasge/gestor_responder.html", {
        "consulta": consulta,
        "respuestas": consulta.respuestas.all().order_by('fecha'),
        "form": form
    })

# --------------------------
# Gestor: Cerrar consulta
# --------------------------
@login_required
@rol_requerido("Gestor")
@transaction.atomic
@require_POST
def cerrar_consulta(request, pk):
    consulta = get_object_or_404(Consulta.objects.select_for_update(), pk=pk)
    validar_consulta_regional(consulta, request.user)
    
    # Solo permitimos cerrar si ya hubo al menos una respuesta
    if consulta.estado == Consulta.Estado.RESPONDIDA or consulta.estado == Consulta.Estado.EN_PROCESO:
        consulta.cerrar()
        messages.success(request, "Consulta finalizada y cerrada definitivamente.")
    else:
        messages.error(request, "No se puede cerrar una consulta sin responder.")
        
    return redirect("consultasge:gestor_consultas")