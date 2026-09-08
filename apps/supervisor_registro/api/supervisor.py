# apps/supervisor_registro/api/supervisor.py

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET, require_POST

from apps.usuarios.models import UsuariosVisualizador

from ..models import ABMSupervisores
from ..services.permission_service import (
    get_regiones_usuario,
    puede_administrar_supervisores,
    puede_operar_supervisor,
    puede_ver_supervisores,
)
from ..services.supervisor_query_service import SupervisorQueryService
from ..services.supervisor_service import build, create, delete, toggle, update


def _forbidden():
    return JsonResponse(
        {
            "ok": False,
            "error": "Sin permisos",
        },
        status=403,
    )


@login_required
@require_GET
def buscar_supervisor(request):
    if not puede_ver_supervisores(request.user):
        return _forbidden()

    cuil = request.GET.get("q", "").strip()

    if not cuil:
        return JsonResponse({
            "ok": True,
            "exists": False,
            "usuario": None,
        })

    regiones = get_regiones_usuario(request.user)

    queryset = SupervisorQueryService.base(regiones)
    queryset = SupervisorQueryService.por_regiones(
        queryset,
        regiones,
    )

    supervisor = queryset.filter(
        usuario__username=cuil,
    ).first()

    if supervisor:
        return JsonResponse({
            "ok": True,
            "exists": True,
            "supervisor": {
                **build(supervisor),
                "situaciones": [
                    {
                        "id": s.id,
                        "situacion_revista__nombre": (
                            s.situacion_revista.nombre
                        ),
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
            },
            "puede_crud": puede_administrar_supervisores(
                request.user
            ),
        })

    # La búsqueda de usuarios que todavía no son supervisores forma
    # parte del proceso de alta, por lo que sólo Administrador/Gestor
    # pueden usarla.
    if not puede_administrar_supervisores(request.user):
        return JsonResponse({
            "ok": True,
            "exists": False,
            "usuario": None,
            "solo_lectura": True,
        })

    usuario = UsuariosVisualizador.objects.filter(
        username=cuil,
    ).first()

    if usuario:
        return JsonResponse({
            "ok": True,
            "exists": False,
            "usuario": {
                "cuil": usuario.username,
                "apellido": usuario.apellido,
                "nombres": usuario.nombres,
            },
            "puede_crud": True,
        })

    return JsonResponse({
        "ok": True,
        "exists": False,
        "usuario": None,
        "puede_crud": True,
    })


@login_required
@require_POST
def crear_supervisor(request):
    if not puede_administrar_supervisores(request.user):
        return _forbidden()

    cuil = request.POST.get("cuil", "").strip()

    if not cuil:
        return JsonResponse(
            {
                "ok": False,
                "error": "CUIL obligatorio",
            },
            status=400,
        )

    usuario = UsuariosVisualizador.objects.filter(
        username=cuil,
    ).first()

    if not usuario:
        return JsonResponse(
            {
                "ok": False,
                "error": "El usuario no existe en Visualizador",
            },
            status=400,
        )

    if ABMSupervisores.objects.filter(usuario=usuario).exists():
        return JsonResponse(
            {
                "ok": False,
                "error": "El usuario ya es supervisor",
            },
            status=409,
        )

    supervisor = create(
        usuario=usuario,
        telefono=request.POST.get("telefono") or None,
        email=request.POST.get("email") or None,
    )

    return JsonResponse({
        "ok": True,
        "id": supervisor.pk,
    })


@login_required
@require_POST
def actualizar_supervisor(request):
    supervisor = get_object_or_404(
        ABMSupervisores,
        pk=request.POST.get("id"),
    )

    if not puede_operar_supervisor(
        request.user,
        supervisor,
        "modificar",
    ):
        return _forbidden()

    supervisor = update(
        supervisor,
        telefono=request.POST.get("telefono"),
        email=request.POST.get("email"),
    )

    return JsonResponse({
        "ok": True,
        "supervisor": build(supervisor),
    })


@login_required
@require_POST
def eliminar_supervisor(request):
    supervisor = get_object_or_404(
        ABMSupervisores,
        pk=request.POST.get("id"),
    )

    if not puede_operar_supervisor(
        request.user,
        supervisor,
        "eliminar",
    ):
        return _forbidden()

    delete(supervisor)

    return JsonResponse({
        "ok": True,
    })


@login_required
@require_POST
def toggle_supervisor(request):
    supervisor = get_object_or_404(
        ABMSupervisores,
        pk=request.POST.get("id"),
    )

    accion = "modificar" if supervisor.activo else "crear"

    if not puede_operar_supervisor(
        request.user,
        supervisor,
        accion,
    ):
        return _forbidden()

    toggle(supervisor)

    return JsonResponse({
        "ok": True,
        "activo": supervisor.activo,
    })


@login_required
@require_GET
def listado_supervisores(request):
    if not puede_ver_supervisores(request.user):
        return _forbidden()

    regiones = get_regiones_usuario(request.user)

    queryset = SupervisorQueryService.base(regiones)
    queryset = SupervisorQueryService.por_regiones(
        queryset,
        regiones,
    )

    data = []

    for supervisor in queryset:
        regionales = [
            sr.region.nombre
            for sr in supervisor.asignaciones_regionales.all()
            if sr.activo
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

    return JsonResponse({
        "ok": True,
        "results": data,
        "puede_crud": puede_administrar_supervisores(
            request.user
        ),
    })
