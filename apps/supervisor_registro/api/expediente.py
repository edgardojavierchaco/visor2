#api/expediente.py
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET, require_POST

from ..audit.services import log_change
from ..audit.utils import snapshot
from ..models import (
    Region,
    SupervisorRegional,
    SupervisorRegionalNivel,
    SupervisorRegionalOferta,
    SupervisorSituacionRevista,
)
from ..selectors.supervisor_selectors import (
    get_supervisor,
    get_supervisor_regional,
)
from ..services import expediente_service as svc
from ..services.permission_service import (
    get_regiones_usuario,
    puede_administrar_supervisores,
    puede_operar_supervisor,
)


def _forbidden():
    return JsonResponse(
        {
            "ok": False,
            "error": "Sin permisos",
        },
        status=403,
    )


def _puede_crud(request):
    return puede_administrar_supervisores(request.user)


@login_required
@require_POST
def add_situacion(request):
    if not _puede_crud(request):
        return _forbidden()

    supervisor = get_supervisor(
        request.POST.get("supervisor_id")
    )

    obj = svc.add_situacion(
        supervisor,
        request.POST,
    )

    log_change(
        user=request.user,
        action="CREATE",
        instance=obj,
        before=None,
        after=snapshot(obj),
        request=request,
    )

    return JsonResponse({
        "ok": True,
        "id": obj.id,
    })


@login_required
@require_POST
def update_situacion(request, pk):
    if not _puede_crud(request):
        return _forbidden()

    obj = get_object_or_404(
        SupervisorSituacionRevista.objects.select_related(
            "supervisor"
        ),
        pk=pk,
    )

    before = snapshot(obj)

    svc.update_situacion(
        obj,
        request.POST,
    )

    log_change(
        user=request.user,
        action="UPDATE",
        instance=obj,
        before=before,
        after=snapshot(obj),
        request=request,
    )

    return JsonResponse({"ok": True})


@login_required
@require_POST
def delete_situacion(request, pk):
    if not _puede_crud(request):
        return _forbidden()

    obj = get_object_or_404(
        SupervisorSituacionRevista.objects.select_related(
            "supervisor"
        ),
        pk=pk,
    )

    before = snapshot(obj)

    svc.delete_situacion(obj)

    log_change(
        user=request.user,
        action="DELETE",
        instance=obj,
        before=before,
        after=None,
        request=request,
    )

    return JsonResponse({"ok": True})


@login_required
@require_POST
def add_regional(request):
    if not _puede_crud(request):
        return _forbidden()

    supervisor = get_supervisor(
        request.POST.get("supervisor_id")
    )

    region = get_object_or_404(
        Region,
        pk=request.POST.get("region_id"),
    )

    # Administrador y Gestor no necesitan ResponsableRegional.
    obj = svc.add_regional(
        supervisor,
        region,
        None,
    )

    log_change(
        user=request.user,
        action="CREATE",
        instance=obj,
        before=None,
        after=snapshot(obj),
        request=request,
    )

    return JsonResponse({
        "ok": True,
        "id": obj.id,
    })


@login_required
@require_POST
def delete_regional(request, pk):
    if not _puede_crud(request):
        return _forbidden()

    obj = get_supervisor_regional(pk)
    before = snapshot(obj)

    svc.delete_regional(obj)

    log_change(
        user=request.user,
        action="DELETE",
        instance=obj,
        before=before,
        after=None,
        request=request,
    )

    return JsonResponse({"ok": True})


@login_required
@require_POST
def add_nivel(request):
    if not _puede_crud(request):
        return _forbidden()

    sr = get_supervisor_regional(
        request.POST.get("sr_id")
    )

    obj = svc.add_nivel(
        sr,
        request.POST.get("nivel_id"),
    )

    log_change(
        user=request.user,
        action="CREATE",
        instance=obj,
        before=None,
        after=snapshot(obj),
        request=request,
    )

    return JsonResponse({
        "ok": True,
        "id": obj.id,
    })


@login_required
@require_POST
def delete_nivel(request):
    if not _puede_crud(request):
        return _forbidden()

    obj = get_object_or_404(
        SupervisorRegionalNivel.objects.select_related(
            "supervisor_regional"
        ),
        pk=request.POST.get("id"),
    )

    before = snapshot(obj)

    svc.delete_nivel(obj)

    log_change(
        user=request.user,
        action="DELETE",
        instance=obj,
        before=before,
        after=None,
        request=request,
    )

    return JsonResponse({"ok": True})


@login_required
@require_POST
def update_nivel(request, pk):
    if not _puede_crud(request):
        return _forbidden()

    obj = get_object_or_404(
        SupervisorRegionalNivel.objects.select_related(
            "supervisor_regional"
        ),
        pk=pk,
    )

    before = snapshot(obj)

    svc.update_nivel(
        obj,
        request.POST,
    )

    log_change(
        user=request.user,
        action="UPDATE",
        instance=obj,
        before=before,
        after=snapshot(obj),
        request=request,
    )

    return JsonResponse({"ok": True})


@login_required
@require_POST
def add_oferta(request):
    if not _puede_crud(request):
        return _forbidden()

    sr = get_supervisor_regional(
        request.POST.get("sr_id")
    )

    obj = svc.add_oferta(
        sr,
        request.POST,
    )

    log_change(
        user=request.user,
        action="CREATE",
        instance=obj,
        before=None,
        after=snapshot(obj),
        request=request,
    )

    return JsonResponse({
        "ok": True,
        "id": obj.id,
    })


@login_required
@require_POST
def delete_oferta(request, pk):
    if not _puede_crud(request):
        return _forbidden()

    obj = get_object_or_404(
        SupervisorRegionalOferta.objects.select_related(
            "supervisor_regional"
        ),
        pk=pk,
    )

    before = snapshot(obj)

    svc.delete_oferta(obj)

    log_change(
        user=request.user,
        action="DELETE",
        instance=obj,
        before=before,
        after=None,
        request=request,
    )

    return JsonResponse({"ok": True})


@login_required
@require_POST
def update_oferta(request, pk):
    if not _puede_crud(request):
        return _forbidden()

    obj = get_object_or_404(
        SupervisorRegionalOferta.objects.select_related(
            "supervisor_regional"
        ),
        pk=pk,
    )

    before = snapshot(obj)

    svc.update_oferta(
        obj,
        request.POST,
    )

    log_change(
        user=request.user,
        action="UPDATE",
        instance=obj,
        before=before,
        after=snapshot(obj),
        request=request,
    )

    return JsonResponse({"ok": True})


@login_required
@require_GET
def get_expediente(request, supervisor_id):
    supervisor = get_supervisor(supervisor_id)

    if not puede_operar_supervisor(
        request.user,
        supervisor,
        "ver",
    ):
        return _forbidden()

    regiones = get_regiones_usuario(request.user)

    regional_qs = (
        SupervisorRegional.objects
        .filter(
            supervisor=supervisor,
            activo=True,
        )
        .select_related("region")
        .prefetch_related(
            "niveles__nivel",
            "ofertas",
        )
    )

    if regiones is not None:
        regional_qs = regional_qs.filter(
            region_id__in=regiones
        )

    situaciones = list(
        supervisor.situaciones
        .filter(activo=True)
        .select_related("situacion_revista")
        .values(
            "id",
            "fecha_desde",
            "fecha_hasta",
            "situacion_revista",
            "situacion_revista__nombre",
        )
    )

    regionales = []
    niveles = []
    ofertas = []

    for sr in regional_qs:
        regionales.append({
            "id": sr.id,
            "region": str(sr.region),
        })

        for n in sr.niveles.all():
            if n.activo:
                niveles.append({
                    "id": n.id,
                    "regional": str(sr.region),
                    "nivel": str(n.nivel),
                    "nivel_id": n.nivel_id,
                    "supervisor_regional_id": sr.id,
                })

        for o in sr.ofertas.all():
            if o.activo:
                ofertas.append({
                    "id": o.id,
                    "regional": str(sr.region),
                    "cueanexo": o.cueanexo,
                    "establecimiento": o.nom_est,
                    "oferta": o.oferta,
                    "acronimo": o.acronimo,
                    "supervisor_regional_id": sr.id,
                })

    return JsonResponse({
        "ok": True,
        "puede_crud": puede_administrar_supervisores(
            request.user
        ),
        "situaciones": situaciones,
        "regionales": regionales,
        "niveles": niveles,
        "ofertas": ofertas,
    })
