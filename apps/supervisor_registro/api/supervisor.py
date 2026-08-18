#api/supervisor.py
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET, require_POST

from apps.usuarios.models import UsuariosVisualizador

from ..models import ABMSupervisores
from ..services.permission_service import (
    get_regiones_usuario,
    puede_crear_supervisor,
    puede_eliminar_supervisor,
    puede_modificar_supervisor,
    puede_operar_supervisor,
    puede_ver_supervisores,
)
from ..services.supervisor_service import build, create, update, delete, toggle
from ..services.supervisor_query_service import SupervisorQueryService


@login_required
@require_GET
def buscar_supervisor(request):
    cuil = request.GET.get("q", "").strip()
    if not cuil:
        return JsonResponse({"exists": False})

    supervisor = (
        ABMSupervisores.objects
        .select_related("usuario")
        .prefetch_related("situaciones__situacion_revista", "asignaciones_regionales__region")
        .filter(usuario__username=cuil, activo=True)
        .first()
    )

    if supervisor:
        if not puede_operar_supervisor(request.user, supervisor, "ver"):
            return JsonResponse({"exists": False, "error": "Sin permisos"}, status=403)

        return JsonResponse({
            "exists": True,
            "supervisor": {
                **build(supervisor),
                "situaciones": [
                    {
                        "id": s.id,
                        "situacion_revista__nombre": s.situacion_revista.nombre,
                        "fecha_desde": s.fecha_desde,
                        "fecha_hasta": s.fecha_hasta,
                    }
                    for s in supervisor.situaciones.all()
                    if s.activo
                ],
                "regionales": [
                    {
                        "id": sr.id,
                        "region__id": sr.region_id,
                        "region__nombre": sr.region.nombre,
                    }
                    for sr in supervisor.asignaciones_regionales.all()
                    if sr.activo
                ],
            }
        })

    usuario = UsuariosVisualizador.objects.filter(username=cuil).first()
    if usuario:
        return JsonResponse({
            "exists": False,
            "usuario": {
                "cuil": usuario.username,
                "apellido": usuario.apellido,
                "nombres": usuario.nombres,
            },
        })

    return JsonResponse({"exists": False, "usuario": None})


@login_required
@require_POST
def crear_supervisor(request):
    if not puede_crear_supervisor(request.user):
        return JsonResponse({"ok": False, "error": "Sin permisos"}, status=403)

    cuil = request.POST.get("cuil", "").strip()
    if not cuil:
        return JsonResponse({"ok": False, "error": "CUIL obligatorio"}, status=400)

    usuario = UsuariosVisualizador.objects.filter(username=cuil).first()
    if not usuario:
        return JsonResponse({"ok": False, "error": "El usuario no existe en Visualizador"}, status=400)

    if ABMSupervisores.objects.filter(usuario=usuario).exists():
        return JsonResponse({"ok": False, "error": "El usuario ya es supervisor"}, status=409)

    supervisor = create(
        usuario=usuario,
        telefono=request.POST.get("telefono") or None,
        email=request.POST.get("email") or None,
    )
    return JsonResponse({"ok": True, "id": supervisor.pk})


@login_required
@require_POST
def actualizar_supervisor(request):
    supervisor = get_object_or_404(ABMSupervisores, pk=request.POST.get("id"))
    if not puede_operar_supervisor(request.user, supervisor, "modificar"):
        return JsonResponse({"ok": False, "error": "Sin permisos"}, status=403)

    supervisor = update(
        supervisor,
        telefono=request.POST.get("telefono"),
        email=request.POST.get("email"),
    )
    return JsonResponse({"ok": True, "supervisor": build(supervisor)})


@login_required
@require_POST
def eliminar_supervisor(request):
    supervisor = get_object_or_404(ABMSupervisores, pk=request.POST.get("id"))
    if not puede_operar_supervisor(request.user, supervisor, "eliminar"):
        return JsonResponse({"ok": False, "error": "Sin permisos"}, status=403)

    delete(supervisor)
    return JsonResponse({"ok": True})


@login_required
@require_POST
def toggle_supervisor(request):
    supervisor = get_object_or_404(ABMSupervisores, pk=request.POST.get("id"))
    accion = "modificar" if supervisor.activo else "crear"
    if not puede_operar_supervisor(request.user, supervisor, accion):
        return JsonResponse({"ok": False, "error": "Sin permisos"}, status=403)

    toggle(supervisor)
    return JsonResponse({"ok": True, "activo": supervisor.activo})


@login_required
@require_GET
def listado_supervisores(request):
    if not puede_ver_supervisores(request.user):
        return JsonResponse({"error": "Sin permisos"}, status=403)

    regiones = get_regiones_usuario(request.user)
    queryset = SupervisorQueryService.base(regiones)
    queryset = SupervisorQueryService.por_regiones(queryset, regiones)

    data = []
    for supervisor in queryset:
        regionales = [
            sr.region.nombre
            for sr in supervisor.asignaciones_regionales.all()
        ]
        data.append({
            "id": supervisor.id,
            "cuil": supervisor.usuario.username,
            "apellido": supervisor.usuario.apellido,
            "nombres": supervisor.usuario.nombres,
            "email": supervisor.email or "",
            "telefono": supervisor.telefono or "",
            "regionales": regionales,
        })

    return JsonResponse({"results": data})
