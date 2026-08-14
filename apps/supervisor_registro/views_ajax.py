from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_GET

from .services.permission_service import (
    get_regiones_usuario,
    puede_ver_supervisores,
)
from .services.supervisor_query_service import SupervisorQueryService


@login_required
@require_GET
def supervisores_datatable(request):
    if not puede_ver_supervisores(request.user):
        return JsonResponse({"error": "Sin permisos"}, status=403)

    regiones_usuario = get_regiones_usuario(request.user)

    # Importante: el alcance también limita el prefetch para no exponer
    # regionales que el usuario no puede ver.
    queryset = SupervisorQueryService.base(regiones_usuario)
    queryset = SupervisorQueryService.por_regiones(queryset, regiones_usuario)

    records_total = queryset.count()

    q = request.GET.get("q", "").strip()
    if not q:
        q = request.GET.get("search[value]", "").strip()

    queryset = SupervisorQueryService.filtros(
        queryset,
        q=q,
        region=request.GET.get("region") or None,
        situacion=request.GET.get("situacion") or None,
        nivel=request.GET.get("nivel") or None,
    )

    records_filtered = queryset.count()

    try:
        start = max(int(request.GET.get("start", 0)), 0)
    except (TypeError, ValueError):
        start = 0

    try:
        length = int(request.GET.get("length", 25))
    except (TypeError, ValueError):
        length = 25

    length = 25 if length == 0 else min(max(length, 10), 100)

    # Orden server-side controlado por columnas conocidas.
    order_map = {
        "0": "usuario__username",
        "1": "usuario__apellido",
        "2": "usuario__nombres",
        "6": "email",
        "7": "telefono",
    }
    order_column = request.GET.get("order[0][column]", "1")
    order_dir = request.GET.get("order[0][dir]", "asc")
    order_field = order_map.get(order_column, "usuario__apellido")
    if order_dir == "desc":
        order_field = f"-{order_field}"

    queryset = queryset.order_by(order_field, "usuario__nombres", "pk")
    queryset = queryset[start:start + length]

    data = []
    for supervisor in queryset:
        regiones = []
        niveles = []
        situaciones = []

        for asignacion in supervisor.asignaciones_regionales.all():
            regiones.append(asignacion.region.nombre)
            niveles.extend(
                str(nivel.nivel)
                for nivel in asignacion.niveles.all()
                if nivel.activo
            )

        situaciones.extend(
            str(situacion.situacion_revista)
            for situacion in supervisor.situaciones.all()
            if situacion.activo
        )

        data.append({
            "id": supervisor.pk,
            "cuil": supervisor.usuario.username,
            "apellido": supervisor.usuario.apellido,
            "nombres": supervisor.usuario.nombres,
            "regiones": "<br>".join(dict.fromkeys(regiones)) or "-",
            "niveles": "<br>".join(dict.fromkeys(niveles)) or "-",
            "situaciones": "<br>".join(dict.fromkeys(situaciones)) or "-",
            "email": supervisor.email or "-",
            "telefono": supervisor.telefono or "-",
            "acciones": (
                f'<a href="{reverse("supervisor_registro:detalle", args=[supervisor.pk])}" '
                'class="btn btn-sm btn-primary me-1" title="Ver detalle">'
                '<i class="fas fa-eye"></i></a>'
                f'<a href="{reverse("supervisor_registro:editar", args=[supervisor.pk])}" '
                'class="btn btn-sm btn-warning" title="Editar">'
                '<i class="fas fa-edit"></i></a>'
            ),
        })

    return JsonResponse({
        "draw": int(request.GET.get("draw", 1)),
        "recordsTotal": records_total,
        "recordsFiltered": records_filtered,
        "data": data,
    })
