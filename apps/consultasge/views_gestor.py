from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.db import transaction
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.http import HttpResponseForbidden
from django.db.models import Count, Q
from django.http import JsonResponse

from .decorators import rol_requerido
from .models import Consulta
from .utils import (
    obtener_region_gestor,
    validar_consulta_regional,
    filtrar_vencidas,
    progreso_sla,
    obtener_turno_gestor,
    horas_habiles_transcurridas,
    SLA_HORAS_DEFAULT
)


# =========================================================
# 📋 LISTADO DE CONSULTAS DEL GESTOR
# =========================================================

@login_required
@rol_requerido("Gestor")
def gestor_consultas(request):

    region = obtener_region_gestor(request.user)

    if not region:
        messages.error(request, "No tiene regional asignada.")
        return redirect("home")

    consultas = (
        Consulta.objects
        .select_related("usuario")
        .filter(region=region)
        .order_by("-fecha_creacion")
    )

    estado = request.GET.get("estado")

    if estado in ["pendiente", "en_proceso", "respondida", "cerrada"]:
        consultas = consultas.filter(estado=estado)

    elif estado == "vencidas":
        consultas = filtrar_vencidas(consultas)
    

    return render(request, "consultasge/gestor_lista.html", {"consultas": consultas, "estado_actual": estado})


# =========================================================
# 📨 RESPONDER CONSULTA
# =========================================================

@login_required
@transaction.atomic
@rol_requerido("Gestor")
def gestor_responder(request, pk):

    consulta = get_object_or_404(
        Consulta.objects.select_for_update(),
        pk=pk
    )

    validar_consulta_regional(consulta, request.user)

    # Cambio automático a EN_PROCESO cuando se abre
    if request.method == "GET" and consulta.estado == Consulta.Estado.PENDIENTE:
        consulta.pasar_a_en_proceso()

    if request.method == "POST":
        try:
            consulta.pasar_a_respondida()
            messages.success(request, "Consulta respondida correctamente.")
            return redirect("consultasge:gestor_consultas")

        except ValidationError as e:
            messages.error(request, str(e))

    return render(
        request,
        "consultasge/gestor_responder.html",
        {"consulta": consulta}
    )


# =========================================================
# 📊 DASHBOARD DEL GESTOR
# =========================================================

@login_required
@rol_requerido("Gestor")
def gestor_dashboard(request):

    region = obtener_region_gestor(request.user)

    if not region:
        return HttpResponseForbidden("No tiene regional asignada.")

    ahora = timezone.now()

    queryset = Consulta.objects.filter(region=region)

    stats = queryset.aggregate(
        total=Count("id"),
        pendientes=Count("id", filter=Q(estado="pendiente")),
        en_proceso=Count("id", filter=Q(estado="en_proceso")),
        respondidas=Count("id", filter=Q(estado="respondida")),
        cerradas=Count("id", filter=Q(estado="cerrada")),
        vencidas=Count(
            "id",
            filter=Q(
                fecha_limite__lt=ahora,
                estado__in=["pendiente", "en_proceso"]
            )
        ),
    )
    

    return render(request, "consultasge/gestor_dashboard.html", {**stats, "datos_grafico": stats})


# =========================================================
# 🔒 CERRAR CONSULTA
# =========================================================

@login_required
@rol_requerido("Gestor")
@require_POST
@transaction.atomic
def cerrar_consulta(request, pk):

    consulta = get_object_or_404(
        Consulta.objects.select_for_update(),
        pk=pk
    )

    validar_consulta_regional(consulta, request.user)

    try:
        consulta.cerrar()
        messages.success(request, "Consulta cerrada correctamente.")

    except ValidationError as e:
        messages.error(request, str(e))

    return redirect("consultasge:gestor_consultas")


@login_required
@rol_requerido("Gestor")
def gestor_dashboard_interactivo_json(request):
    """
    Retorna los datos para el gráfico interactivo en JSON.
    """
    region = obtener_region_gestor(request.user)
    if not region:
        return JsonResponse({"error": "No tiene regional asignada."}, status=403)

    consultas = Consulta.objects.filter(region=region)
    ahora = timezone.now()
    lista_estados = ["pendiente", "en_proceso", "respondida", "cerrada"]

    stats = {estado: consultas.filter(estado=estado).count() for estado in lista_estados}
    stats["vencidas"] = consultas.filter(fecha_limite__lt=ahora, estado__in=["pendiente", "en_proceso"]).count()

    progreso_por_estado = {}
    for estado in lista_estados:
        qs = consultas.filter(estado=estado)
        if qs.exists():
            total_horas = sum([horas_habiles_transcurridas(c.fecha_creacion, obtener_turno_gestor(request.user)) for c in qs])
            promedio = (total_horas / qs.count()) / SLA_HORAS_DEFAULT * 100
            progreso_por_estado[estado] = round(promedio, 2)
        else:
            progreso_por_estado[estado] = 0

    labels = [e.capitalize() for e in lista_estados] + ["Vencidas"]
    datos = [stats[e] for e in lista_estados] + [stats["vencidas"]]
    colores = []
    for e in lista_estados:
        p = progreso_por_estado[e]
        if p <= 60:
            colores.append("#28a745")
        elif p <= 85:
            colores.append("#ffc107")
        elif p <= 100:
            colores.append("#fd7e14")
        else:
            colores.append("#dc3545")
    colores.append("#343a40")  # Vencidas

    return JsonResponse({
        "labels": labels,
        "datos": datos,
        "colores": colores,
        "progreso_por_estado": progreso_por_estado,
    })

@login_required
@rol_requerido("Gestor")
def gestor_dashboard_interactivo_template(request):
    """
    Renderiza el template del dashboard interactivo.
    Los datos reales se obtendrán por AJAX.
    """
    region = obtener_region_gestor(request.user)
    if not region:
        return HttpResponseForbidden("No tiene regional asignada.")

    # Pasamos la URL del endpoint JSON al template
    return render(request, "consultasge/gestor_dashboard_interactivo.html", {
        "json_endpoint": request.build_absolute_uri("/consultasge/gestor/dashboard/json/"),
    })