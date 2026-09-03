# apps/supervisor_registro/api/mapa.py
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from ..services.permission_service import (
    get_regiones_usuario,
    puede_ver_supervisores,
)
from ..services.supervisor_geo_service import SupervisorGeoService
from ..services.supervisor_query_service import SupervisorQueryService


@login_required
@require_GET
def mapa_supervisores(request):
    """
    Endpoint del mapa territorial de supervisores.

    Permite:

    - mapa general;
    - mapa de un supervisor;
    - filtro por región;
    - filtro por nivel;
    - filtro por situación de revista;
    - búsqueda por CUIL / apellido / nombre.

    Respeta siempre el alcance territorial del usuario conectado.
    """

    # ============================================================
    # PERMISOS
    # ============================================================

    if not puede_ver_supervisores(request.user):
        return JsonResponse(
            {
                "ok": False,
                "error": "No posee permisos para consultar supervisores.",
            },
            status=403,
        )

    regiones_usuario = get_regiones_usuario(request.user)

    # None:
    #     administrador / funcionario -> alcance global
    #
    # []:
    #     usuario sin regiones habilitadas
    #
    # [1, 2, 3]:
    #     responsable regional

    if regiones_usuario == []:
        return JsonResponse(
            {
                "ok": True,
                "modo": "general",
                "cantidad": 0,
                "estadisticas": {
                    "total": 0,
                    "geolocalizadas": 0,
                    "sin_geolocalizar": 0,
                    "supervisores": 0,
                    "regiones": 0,
                    "ofertas": 0,
                },
                "escuelas": [],
            }
        )

    # ============================================================
    # PARÁMETROS
    # ============================================================

    q = (request.GET.get("q") or "").strip()

    region = request.GET.get("region") or None
    nivel = request.GET.get("nivel") or None
    situacion = request.GET.get("situacion") or None
    supervisor_id = request.GET.get("supervisor_id") or None

    # ============================================================
    # VALIDACIÓN DE IDs
    # ============================================================

    def entero_o_none(valor, nombre):
        if valor in (None, ""):
            return None

        try:
            return int(valor)

        except (TypeError, ValueError):
            raise ValueError(
                f"El parámetro '{nombre}' no es válido."
            )

    try:
        region = entero_o_none(region, "region")
        nivel = entero_o_none(nivel, "nivel")
        situacion = entero_o_none(
            situacion,
            "situacion",
        )
        supervisor_id = entero_o_none(
            supervisor_id,
            "supervisor_id",
        )

    except ValueError as exc:
        return JsonResponse(
            {
                "ok": False,
                "error": str(exc),
            },
            status=400,
        )

    # ============================================================
    # VALIDAR REGIÓN SOLICITADA
    # ============================================================

    # Si el usuario no es administrador,
    # no puede pedir una región fuera de su alcance.

    if (
        region is not None
        and regiones_usuario is not None
        and region not in regiones_usuario
    ):
        return JsonResponse(
            {
                "ok": False,
                "error": (
                    "No posee permisos para consultar "
                    "la región seleccionada."
                ),
            },
            status=403,
        )

    # ============================================================
    # QUERY BASE
    # ============================================================

    queryset = SupervisorQueryService.base(
        regiones_usuario
    )

    queryset = SupervisorQueryService.por_regiones(
        queryset,
        regiones_usuario,
    )

    # ============================================================
    # FILTROS
    # ============================================================

    queryset = SupervisorQueryService.filtros(
        queryset,
        q=q,
        region=region,
        situacion=situacion,
        nivel=nivel,
    )

    # ============================================================
    # ALCANCE GEOGRÁFICO EFECTIVO
    # ============================================================

    # Si se seleccionó una región, queremos que el mapa muestre
    # únicamente establecimientos de esa región.
    #
    # Si no se seleccionó:
    #     None -> todo para administrador
    #     lista -> regiones permitidas del responsable

    if region is not None:
        regiones_mapa = [region]
    else:
        regiones_mapa = regiones_usuario

    # ============================================================
    # SUPERVISOR INDIVIDUAL
    # ============================================================

    if supervisor_id is not None:

        supervisor = (
            queryset
            .filter(pk=supervisor_id)
            .select_related("usuario")
            .first()
        )

        if supervisor is None:
            return JsonResponse(
                {
                    "ok": False,
                    "error": (
                        "Supervisor no encontrado o fuera "
                        "del alcance del usuario."
                    ),
                },
                status=404,
            )

        escuelas = SupervisorGeoService.escuelas_supervisor(
            supervisor=supervisor,
            regiones=regiones_mapa,
        )

        estadisticas = (
            SupervisorGeoService.estadisticas(
                escuelas
            )
        )

        return JsonResponse(
            {
                "ok": True,
                "modo": "supervisor",
                "supervisor_id": supervisor.id,
                "cantidad": len(escuelas),
                "estadisticas": estadisticas,
                "escuelas": escuelas,
            }
        )

    # ============================================================
    # MAPA GENERAL
    # ============================================================

    supervisores = list(
        queryset
        .select_related("usuario")
        .distinct()
    )

    escuelas = SupervisorGeoService.mapa_general(
        supervisores=supervisores,
        regiones=regiones_mapa,
    )

    estadisticas = (
        SupervisorGeoService.estadisticas(
            escuelas
        )
    )

    return JsonResponse(
        {
            "ok": True,
            "modo": "general",
            "cantidad": len(escuelas),
            "estadisticas": estadisticas,
            "escuelas": escuelas,
        }
    )