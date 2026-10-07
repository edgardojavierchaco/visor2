from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from ..models import SupervisorRegional
from ..services.permission_service import (
    get_regiones_usuario,
    puede_ver_supervisores,
)
from ..services.regional_geo_service import RegionalGeoService
from ..services.supervisor_geo_service import SupervisorGeoService
from ..services.supervisor_query_service import SupervisorQueryService


def _entero_o_none(valor, nombre):
    if valor in (None, ""):
        return None

    try:
        return int(valor)
    except (TypeError, ValueError):
        raise ValueError(f"El parámetro '{nombre}' no es válido.")


def _intersectar_regiones(region_ids, regiones_permitidas):
    """
    None en regiones_permitidas significa alcance global.
    Una lista restringe el resultado a ese alcance territorial.
    """
    region_ids = list(dict.fromkeys(int(x) for x in region_ids))

    if regiones_permitidas is None:
        return region_ids

    permitidas = set(regiones_permitidas)
    return [rid for rid in region_ids if rid in permitidas]


def _regiones_asignadas_supervisor(
    supervisor,
    regiones_permitidas=None,
    nivel_id=None,
):
    qs = SupervisorRegional.objects.filter(
        supervisor=supervisor,
        activo=True,
    )

    if nivel_id is not None:
        qs = qs.filter(
            niveles__activo=True,
            niveles__nivel_id=nivel_id,
        )

    ids = list(
        qs.values_list("region_id", flat=True).distinct()
    )
    return _intersectar_regiones(ids, regiones_permitidas)


def _regiones_asignadas_supervisores(
    supervisores,
    regiones_permitidas=None,
    nivel_id=None,
):
    supervisor_ids = [s.id for s in supervisores]
    if not supervisor_ids:
        return []

    qs = SupervisorRegional.objects.filter(
        supervisor_id__in=supervisor_ids,
        activo=True,
    )

    if nivel_id is not None:
        qs = qs.filter(
            niveles__activo=True,
            niveles__nivel_id=nivel_id,
        )

    ids = list(
        qs.values_list("region_id", flat=True).distinct()
    )
    return _intersectar_regiones(ids, regiones_permitidas)


@login_required
@require_GET
def mapa_supervisores(request):
    """
    Endpoint del mapa territorial de supervisores.

    Reglas principales:
    - respeta el alcance territorial del usuario conectado;
    - el mapa individual sólo muestra las regionales asignadas al supervisor;
    - el mapa general muestra las regionales representadas por los supervisores
      resultantes de los filtros;
    - escuelas y regionales se entregan en una única respuesta JSON.
    """

    if not puede_ver_supervisores(request.user):
        return JsonResponse(
            {
                "ok": False,
                "error": "No posee permisos para consultar supervisores.",
            },
            status=403,
        )

    regiones_usuario = get_regiones_usuario(request.user)

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
                "regionales": RegionalGeoService.vacio(),
            }
        )

    q = (request.GET.get("q") or "").strip()
    region = request.GET.get("region") or None
    nivel = request.GET.get("nivel") or None
    situacion = request.GET.get("situacion") or None
    supervisor_id = request.GET.get("supervisor_id") or None

    try:
        region = _entero_o_none(region, "region")
        nivel = _entero_o_none(nivel, "nivel")
        situacion = _entero_o_none(situacion, "situacion")
        supervisor_id = _entero_o_none(supervisor_id, "supervisor_id")
    except ValueError as exc:
        return JsonResponse(
            {"ok": False, "error": str(exc)},
            status=400,
        )

    if (
        region is not None
        and regiones_usuario is not None
        and region not in regiones_usuario
    ):
        return JsonResponse(
            {
                "ok": False,
                "error": "No posee permisos para consultar la región seleccionada.",
            },
            status=403,
        )

    queryset = SupervisorQueryService.base(regiones_usuario)
    queryset = SupervisorQueryService.por_regiones(queryset, regiones_usuario)
    queryset = SupervisorQueryService.filtros(
        queryset,
        q=q,
        region=region,
        situacion=situacion,
        nivel=nivel,
        situacion_vigente=True,
    )

    # Alcance territorial permitido/seleccionado para las escuelas.
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
                    "error": "Supervisor no encontrado o fuera del alcance del usuario.",
                },
                status=404,
            )

        escuelas = SupervisorGeoService.escuelas_supervisor(
            supervisor=supervisor,
            regiones=regiones_mapa,
            nivel_id=nivel,
        )
        estadisticas = SupervisorGeoService.estadisticas(escuelas)

        # IMPORTANTE:
        # la capa poligonal individual se limita exclusivamente a las
        # regionales activas asignadas a este supervisor, intersectadas
        # con el alcance del usuario y con el filtro regional seleccionado.
        regionales_supervisor = _regiones_asignadas_supervisor(
            supervisor,
            regiones_permitidas=regiones_mapa,
            nivel_id=nivel,
        )

        return JsonResponse(
            {
                "ok": True,
                "modo": "supervisor",
                "supervisor_id": supervisor.id,
                "cantidad": len(escuelas),
                "estadisticas": estadisticas,
                "escuelas": escuelas,
                "regionales": RegionalGeoService.geojson_por_ids(
                    regionales_supervisor
                ),
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
        nivel_id=nivel,
    )
    estadisticas = SupervisorGeoService.estadisticas(escuelas)

    regionales_general = _regiones_asignadas_supervisores(
        supervisores,
        regiones_permitidas=regiones_mapa,
        nivel_id=nivel,
    )

    return JsonResponse(
        {
            "ok": True,
            "modo": "general",
            "cantidad": len(escuelas),
            "estadisticas": estadisticas,
            "escuelas": escuelas,
            "regionales": RegionalGeoService.geojson_por_ids(
                regionales_general
            ),
        }
    )
