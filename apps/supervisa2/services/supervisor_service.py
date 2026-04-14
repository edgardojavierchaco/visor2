from django.db import transaction
from apps.supervisa2.models.supervisor import (
    Supervisor2,
    SupervisorRegion
)


# =========================================================
# 🔥 GET SUPERVISOR BY USER
# =========================================================
def get_supervisor_from_user(user):
    return (
        Supervisor2.objects
        .select_related("usuario")
        .prefetch_related("regiones")
        .filter(usuario=user)
        .first()
    )


# =========================================================
# 🔥 CREATE / UPDATE CORE (PRO VERSION)
# =========================================================
@transaction.atomic
def crear_o_actualizar_supervisor(form, user, instance=None):

    cleaned = form.cleaned_data

    obj = instance or Supervisor2.objects.filter(usuario=user).first()

    # =====================================================
    # 🔥 M2M SAFE (FIX CRÍTICO)
    # =====================================================
    if "niveles_modalidad" in cleaned:
        niveles = cleaned.pop("niveles_modalidad")
    else:
        niveles = obj.niveles_modalidad.all() if obj else []

    if "regiones" in cleaned:
        regiones = cleaned.pop("regiones")
    else:
        regiones = obj.regiones.all() if obj else []

    # =====================================================
    # CREATE
    # =====================================================
    if obj is None:
        obj = Supervisor2.objects.create(
            usuario=user,
            situacion_revista=cleaned["situacion_revista"],
            fecha_desde=cleaned["fecha_desde"],
            fecha_hasta=cleaned.get("fecha_hasta"),
            telefono=cleaned.get("telefono"),
            email=cleaned.get("email"),
            activo=cleaned.get("activo", True),
            estado_validacion="EN_REVISION",
        )

    # =====================================================
    # UPDATE
    # =====================================================
    else:
        for k, v in cleaned.items():
            setattr(obj, k, v)
        obj.save()

    # =====================================================
    # M2M UPDATE
    # =====================================================
    obj.niveles_modalidad.set(niveles)
    obj.regiones.set(regiones)

    # =====================================================
    # 🔥 SYNC PUENTE (ROBUSTO)
    # =====================================================
    _sync_supervisor_region(obj, regiones)

    # =====================================================
    # 🔄 WORKFLOW SAFE (NO pisa APROBADO)
    # =====================================================
    if obj.estado_validacion != "APROBADO":
        obj.estado_validacion = "EN_REVISION"
        obj.save(update_fields=["estado_validacion"])

    return obj


# =========================================================
# 🔥 SYNC PUENTE (ROBUST VERSION)
# =========================================================
def _sync_supervisor_region(supervisor, regiones):

    if not regiones:
        return

    # 🔥 soporta queryset o lista
    region_names = [getattr(r, "nombre", r) for r in regiones]

    # =====================================================
    # DELETE (los que ya no están)
    # =====================================================
    SupervisorRegion.objects.filter(
        supervisor=supervisor
    ).exclude(
        region_loc__in=region_names
    ).delete()

    # =====================================================
    # EXISTENTES
    # =====================================================
    existing = set(
        SupervisorRegion.objects.filter(
            supervisor=supervisor
        ).values_list("region_loc", flat=True)
    )

    # =====================================================
    # CREAR NUEVOS
    # =====================================================
    new_objs = [
        SupervisorRegion(
            supervisor=supervisor,
            region_loc=getattr(r, "nombre", r)
        )
        for r in regiones
        if getattr(r, "nombre", r) not in existing
    ]

    if new_objs:
        SupervisorRegion.objects.bulk_create(new_objs)