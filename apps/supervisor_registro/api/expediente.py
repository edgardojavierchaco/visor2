from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

from ..services import expediente_service as svc
from ..services.permission_service import (
    assert_responsable, 
    get_regiones_usuario,
    puede_operar_region
)

from ..selectors.supervisor_selectors import (
    get_supervisor,
    get_supervisor_regional
)
from ..audit.services import log_change
from ..audit.utils import snapshot

def validar_region(request, region_id):

    regiones_permitidas = get_regiones_usuario(
        request.user
    )

    return region_id in regiones_permitidas


# =========================
# SITUACION
# =========================

@login_required
def add_situacion(request):

    supervisor = get_supervisor(request.POST["supervisor_id"])

    obj = svc.add_situacion(supervisor, request.POST)

    log_change(
        user=request.user,
        action="CREATE",
        instance=obj,
        before=None,
        after=snapshot(obj),
        request=request
    )

    return JsonResponse({"id": obj.id})


@login_required
@require_POST
def update_situacion(request, pk):

    obj = svc.get_situacion(pk)

    before = snapshot(obj)

    svc.update_situacion(obj, request.POST)

    log_change(
        user=request.user,
        action="UPDATE",
        instance=obj,
        before=before,
        after=snapshot(obj),
        request=request
    )

    return JsonResponse({"ok": True})


@login_required
def delete_situacion(request, pk):

    obj = svc.get_situacion(pk)

    before = snapshot(obj)

    svc.delete_situacion(obj)

    log_change(
        user=request.user,
        action="DELETE",
        instance=obj,
        before=before,
        after=None,
        request=request
    )

    return JsonResponse({"ok": True})


# =========================
# REGIONAL
# =========================

@login_required
def add_regional(request):

    resp = assert_responsable(request.user)

    supervisor = get_supervisor(request.POST["supervisor_id"])

    region = resp.regiones.get(pk=request.POST["region_id"])

    obj = svc.add_regional(supervisor, region, resp)

    log_change(
        user=request.user,
        action="CREATE",
        instance=obj,
        before=None,
        after=snapshot(obj),
        request=request
    )

    return JsonResponse({"id": obj.id})


@login_required
def delete_regional(request, pk):

    obj = get_supervisor_regional(pk)
    
    if not puede_operar_region(
        request.user,
        obj.region_id
    ):
        return JsonResponse(
            {"error": "Sin permisos"},
            status=403
        )

    before = snapshot(obj)

    svc.delete_regional(obj)

    log_change(
        user=request.user,
        action="DELETE",
        instance=obj,
        before=before,
        after=None,
        request=request
    )

    return JsonResponse({"ok": True})


# =========================
# NIVEL
# =========================

@login_required
@require_POST
def add_nivel(request):

    sr = get_supervisor_regional(request.POST["sr_id"])
    
    if not puede_operar_region(
        request.user,
        sr.region_id
    ):
        return JsonResponse(
            {"error": "Sin permisos"},
            status=403
        )

    obj = svc.add_nivel(sr, request.POST["nivel_id"])

    log_change(
        user=request.user,
        action="CREATE",
        instance=obj,
        before=None,
        after=snapshot(obj),
        request=request
    )

    return JsonResponse({"id": obj.id})


@login_required
def delete_nivel(request):

    obj = svc.get_nivel(request.POST["id"])
    
    if not puede_operar_region(
        request.user,
        obj.supervisor_regional.region_id
    ):
        return JsonResponse(
            {"error": "Sin permisos"},
            status=403
        )

    before = snapshot(obj)

    svc.delete_nivel(obj)

    log_change(
        user=request.user,
        action="DELETE",
        instance=obj,
        before=before,
        after=None,
        request=request
    )

    return JsonResponse({"ok": True})


@login_required
@require_POST
def update_nivel(request, pk):

    obj = svc.get_nivel(pk)
    
    if not puede_operar_region(
        request.user,
        obj.supervisor_regional.region_id
    ):
        return JsonResponse(
            {"error": "Sin permisos"},
            status=403
        )

    before = snapshot(obj)

    svc.update_nivel(obj, request.POST)

    obj.save()

    log_change(
        user=request.user,
        action="UPDATE",
        instance=obj,
        before=before,
        after=snapshot(obj),
        request=request
    )

    return JsonResponse({
        "ok": True
    })


# =========================
# OFERTA
# =========================

@login_required
def add_oferta(request):

    sr = get_supervisor_regional(request.POST["sr_id"])
    
    if not puede_operar_region(
        request.user,
        sr.region_id
    ):
        return JsonResponse(
            {"error": "Sin permisos"},
            status=403
        )

    obj = svc.add_oferta(sr, request.POST)

    log_change(
        user=request.user,
        action="CREATE",
        instance=obj,
        before=None,
        after=snapshot(obj),
        request=request
    )

    return JsonResponse({"id": obj.id})


@login_required
def delete_oferta(request, pk):

    obj = svc.get_oferta(pk)
    
    if not puede_operar_region(
        request.user,
        obj.supervisor_regional.region_id
    ):
        return JsonResponse(
            {"error": "Sin permisos"},
            status=403
        )

    before = snapshot(obj)

    svc.delete_oferta(obj)

    log_change(
        user=request.user,
        action="DELETE",
        instance=obj,
        before=before,
        after=None,
        request=request
    )

    return JsonResponse({"ok": True})


@login_required
@require_POST
def update_oferta(request, pk):

    obj = svc.get_oferta(pk)
    
    if not puede_operar_region(
        request.user,
        obj.supervisor_regional.region_id
    ):
        return JsonResponse(
            {"error": "Sin permisos"},
            status=403
        )

    before = snapshot(obj)

    svc.update_oferta(obj, request.POST)

    obj.save()

    log_change(
        user=request.user,
        action="UPDATE",
        instance=obj,
        before=before,
        after=snapshot(obj),
        request=request
    )

    return JsonResponse({
        "ok": True
    })


@login_required
def get_expediente(request, supervisor_id):

    supervisor = get_supervisor(supervisor_id)

    regiones_permitidas = get_regiones_usuario(
        request.user
    )
    
    situaciones = list(
        supervisor.situaciones.filter(
            activo=True
        ).values(
            "id",
            "fecha_desde",
            "fecha_hasta",
            "situacion_revista",
            "situacion_revista__nombre"
        )
    )

    regionales = []

    niveles = []

    ofertas = []

    for sr in supervisor.asignaciones_regionales.filter(
        activo=True,
        region_id__in=regiones_permitidas
    ):

        regionales.append({
            "id": sr.id,
            "region": str(sr.region)
        })

        for n in sr.niveles.filter(activo=True):

            niveles.append({
                "id": n.id,
                "regional": str(sr.region),
                "nivel": n.nivel.nombre,
                "nivel_id": n.nivel_id
            })

        for o in sr.ofertas.filter(activo=True):

            ofertas.append({
                "id": o.id,
                "regional": str(sr.region),
                
                "cueanexo": o.cueanexo,
                "establecimiento": o.nom_est,
                
                "oferta": o.oferta,
                "acronimo": o.acronimo,
                
                "supervisor_regional_id": sr.id
            })

    return JsonResponse({
        "situaciones": situaciones,
        "regionales": regionales,
        "niveles": niveles,
        "ofertas": ofertas
    })


