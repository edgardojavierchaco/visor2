from django.db.models import Q
from ..models import Supervisor2
from apps.supervisa2.services.regional_service import get_region_usuario


# =========================================================
# 🔎 BASE OPTIMIZADA
# =========================================================
def get_supervisores_base():

    return Supervisor2.objects.select_related(
        "usuario",
        "situacion_revista",
        "validado_por"
    ).prefetch_related(
        "supervisor_regiones"  # 🔥 FIX REAL
    )


# =========================================================
# 🔎 SUPERVISOR POR USUARIO
# =========================================================
def get_supervisor_by_user(user):

    return (
        Supervisor2.objects
        .select_related(
            "usuario",
            "situacion_revista",
            "validado_por"
        )
        .prefetch_related(
            "supervisor_regiones",
            "niveles_modalidad"   # 🔥 CORRECTO
        )
        .filter(usuario__username=user.username)
        .first()
    )


# =========================================================
# 🔎 GLOBAL
# =========================================================
def get_supervisores_global(query=None):

    qs = get_supervisores_base()

    if query:
        qs = qs.filter(
            Q(usuario__apellido__icontains=query) |
            Q(usuario__nombres__icontains=query) |
            Q(usuario__username__icontains=query)
        )

    return qs.order_by("usuario__apellido")


# =========================================================
# 🔎 POR REGIÓN (MULTI-REGIÓN CORRECTO)
# =========================================================
def get_supervisores_por_region(user, query=None):

    regiones = get_region_usuario(user)

    print("REGIONES USER:", regiones)

    if not regiones:
        return Supervisor2.objects.none()

    qs = get_supervisores_base().filter(
        supervisor_regiones__region_loc__in=regiones  # 🔥 OK si region_loc es string
    ).distinct()

    if query:
        qs = qs.filter(
            Q(usuario__apellido__icontains=query) |
            Q(usuario__nombres__icontains=query) |
            Q(usuario__username__icontains=query)
        )

    return qs.order_by("usuario__apellido")


# =========================================================
# 🔎 PENDIENTES REGIONAL
# =========================================================
def get_pendientes_regional(user):

    regiones = get_region_usuario(user)

    if not regiones:
        return Supervisor2.objects.none()

    return (
        get_supervisores_base()
        .filter(
            estado_validacion="EN_REVISION",
            supervisor_regiones__region_loc__in=regiones
        )
        .distinct()
    )