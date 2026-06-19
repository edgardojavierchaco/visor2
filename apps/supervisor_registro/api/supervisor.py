from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

from apps.usuarios.models import UsuariosVisualizador

from ..models import (
    ABMSupervisores,
    SupervisorRegional,
    SupervisorSituacionRevista
)

from ..services.permission_service import assert_responsable, get_regiones_usuario
from ..services.supervisor_service import build

@login_required
def buscar_supervisor(request):
    cuil = request.GET.get("q", "").strip()

    if not cuil:
        return JsonResponse({
            "exists": False
        })

    try:

        supervisor = ABMSupervisores.objects.select_related(
            "usuario"
        ).get(
            usuario__username=cuil,
            activo=True
        )

        situaciones = list(
            SupervisorSituacionRevista.objects.filter(
                supervisor=supervisor,
                activo=True
            ).values(
                "id",
                "situacion_revista__nombre",
                "fecha_desde",
                "fecha_hasta"
            )
        )

        regionales = list(
            SupervisorRegional.objects.filter(
                supervisor=supervisor,
                activo=True
            ).select_related("region")
            .values(
                "id",
                "region__id",
                "region__nombre"
            )
        )

        return JsonResponse({
            "exists": True,
            "supervisor": {
                "id": supervisor.id,
                "cuil": supervisor.usuario.username,
                "apellido": supervisor.usuario.apellido,
                "nombres": supervisor.usuario.nombres,
                "email": supervisor.email,
                "telefono": supervisor.telefono,
                "activo": supervisor.activo,
                "situaciones": situaciones,
                "regionales": regionales
            }
        })

    except ABMSupervisores.DoesNotExist:

        try:

            usuario = UsuariosVisualizador.objects.get(
                username=cuil
            )

            return JsonResponse({
                "exists": False,
                "usuario": {
                    "cuil": usuario.username,
                    "apellido": usuario.apellido,
                    "nombres": usuario.nombres,
                }
            })

        except UsuariosVisualizador.DoesNotExist:

            return JsonResponse({
                "exists": False,
                "usuario": None
            })



@login_required
def crear_supervisor(request):

    cuil = request.POST["cuil"]
    
    try:

        usuario = UsuariosVisualizador.objects.get(
            username=cuil
        )

    except UsuariosVisualizador.DoesNotExist:
        return JsonResponse(
            {
                "ok": False,
                "error": "El usuario no existe en Visualizador"
            },
            status=400
        )
        
    supervisor = ABMSupervisores.objects.create(
        usuario=usuario,
        telefono=request.POST.get("telefono"),
        email=request.POST.get("email")
    )

    return JsonResponse({
        "ok": True,
        "id": supervisor.id
    })


@login_required
def actualizar_supervisor(request):

    supervisor = ABMSupervisores.objects.get(
        pk=request.POST["id"]
    )

    supervisor.telefono = request.POST.get("telefono")
    supervisor.email = request.POST.get("email")

    supervisor.save()

    return JsonResponse({
        "ok": True
    })


@login_required
def eliminar_supervisor(request):

    supervisor = ABMSupervisores.objects.get(
        pk=request.POST["id"]
    )

    supervisor.activo = False
    supervisor.save()

    return JsonResponse({
        "ok": True
    })


@login_required
def toggle_supervisor(request):

    supervisor = ABMSupervisores.objects.get(
        pk=request.POST["id"]
    )

    supervisor.activo = not supervisor.activo
    supervisor.save()

    return JsonResponse({
        "ok": True
    })


@login_required
def listado_supervisores(request):

    assert_responsable(request.user)

    regiones = get_regiones_usuario(
        request.user
    )

    supervisores = (
        ABMSupervisores.objects
        .filter(
            activo=True,
            asignaciones_regionales__activo=True,
            asignaciones_regionales__region_id__in=regiones
        )
        .distinct()
        .select_related("usuario")
        .order_by(
            "usuario__apellido",
            "usuario__nombres"
        )
    )

    data = []

    for supervisor in supervisores:

        regionales = list(
            supervisor.asignaciones_regionales
            .filter(
                activo=True,
                region_id__in=regiones
            )
            .values_list(
                "region__nombre",
                flat=True
            )
        )

        data.append({
            "id": supervisor.id,
            "cuil": supervisor.usuario.username,
            "apellido": supervisor.usuario.apellido,
            "nombres": supervisor.usuario.nombres,
            "email": supervisor.email or "",
            "telefono": supervisor.telefono or "",
            "regionales": regionales
        })

    return JsonResponse({
        "results": data
    })