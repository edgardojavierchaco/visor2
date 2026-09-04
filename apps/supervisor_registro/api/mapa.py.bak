from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from ..models import ABMSupervisores
from ..services.permission_service import (
    get_regiones_usuario,
    puede_operar_supervisor,
    puede_ver_supervisores,
)
from ..services.supervisor_geo_service import (
    SupervisorGeoService,
)
from ..services.supervisor_query_service import (
    SupervisorQueryService,
)


@login_required
@require_GET
def mapa_supervisores(request):

    if not puede_ver_supervisores(
        request.user
    ):

        return JsonResponse(
            {
                "ok": False,
                "error": "Sin permisos",
            },
            status=403,
        )

    regiones_usuario = (
        get_regiones_usuario(
            request.user
        )
    )

    # -----------------------------------------------------
    # Consulta base respetando permisos
    # -----------------------------------------------------

    queryset = (
        SupervisorQueryService
        .base(regiones_usuario)
    )

    queryset = (
        SupervisorQueryService
        .por_regiones(
            queryset,
            regiones_usuario
        )
    )

    # -----------------------------------------------------
    # Filtros
    # -----------------------------------------------------

    q = request.GET.get(
        "q",
        ""
    ).strip()

    region = (
        request.GET.get("region")
        or None
    )

    situacion = (
        request.GET.get("situacion")
        or None
    )

    nivel = (
        request.GET.get("nivel")
        or None
    )

    supervisor_id = (
        request.GET.get(
            "supervisor_id"
        )
        or None
    )

    queryset = (
        SupervisorQueryService
        .filtros(
            queryset,
            q=q,
            region=region,
            situacion=situacion,
            nivel=nivel,
        )
    )

    # -----------------------------------------------------
    # Supervisor individual
    # -----------------------------------------------------

    if supervisor_id:

        try:

            supervisor_id = int(
                supervisor_id
            )

        except ValueError:

            return JsonResponse(
                {
                    "ok": False,
                    "error":
                        "Supervisor inválido",
                },
                status=400,
            )

        queryset = queryset.filter(
            pk=supervisor_id
        )

    supervisores = list(
        queryset
        .select_related("usuario")
    )

    if supervisor_id:

        if not supervisores:

            return JsonResponse(
                {
                    "ok": False,
                    "error":
                        "Supervisor no encontrado",
                },
                status=404,
            )

        mapa = (
            SupervisorGeoService
            .escuelas_supervisor(
                supervisor_id=
                    supervisor_id,
                regiones=
                    regiones_usuario,
            )
        )

    else:

        mapa = (
            SupervisorGeoService
            .mapa_general(
                supervisores,
                regiones=
                    regiones_usuario,
            )
        )

    return JsonResponse({

        "ok": True,

        "modo":
            (
                "supervisor"
                if supervisor_id
                else "general"
            ),

        "cantidad":

            (
                len(
                    mapa["escuelas"]
                )
                if supervisor_id
                else len(mapa)
            ),

        "escuelas":

            (
                mapa["escuelas"]
                if supervisor_id
                else mapa
            ),

    })