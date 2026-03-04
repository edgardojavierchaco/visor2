# apps/consultasge/utils.py

from datetime import datetime, timedelta, time
from django.utils import timezone
from django.core.exceptions import PermissionDenied
from apps.usuarios.models_regional import RegionalUsuariosAgentes
from .models import Consulta, TURNOS, SLA_HORAS_DEFAULT


# =========================================================
# 🔐 OBTENER REGIÓN DEL GESTOR (OPTIMIZADO)
# =========================================================

def obtener_region_gestor(user):
    """
    Retorna la región del gestor autenticado.
    Retorna None si:
        - Usuario no autenticado
        - No es Gestor
        - No tiene perfil activo en RegionalUsuariosAgentes
    """

    if not user or not user.is_authenticated:
        return None

    # Validación del rol
    if getattr(user, "nivelacceso_id", None) != "Gestor":
        return None

    try:
        perfil = user.perfil_regional
        if perfil.activo and perfil.region_loc:
            return perfil.region_loc.strip()
    except RegionalUsuariosAgentes.DoesNotExist:
        return None
    return None

# =========================================================
# 🔐 VALIDAR ACCESO REGIONAL DEL GESTOR
# =========================================================

def validar_consulta_regional(consulta, user):

    region = obtener_region_gestor(user)

    if not region:
        raise PermissionDenied("No tiene regional asignada.")

    if consulta.region.strip().lower() != region.strip().lower():
        raise PermissionDenied("No pertenece a su regional.")

    return True

# =========================================================
# ⏱ VERIFICAR SI SLA ESTÁ VENCIDO
# =========================================================
   
def sla_vencido(consulta):
    """
    Retorna True si la consulta está vencida.
    Solo aplica si:
        - Tiene fecha_limite
        - No está respondida ni cerrada
    """

    if not consulta.fecha_limite:
        return False

    # No considerar vencidas si ya finalizaron
    if consulta.estado in ["respondida", "cerrada"]:
        return False

    return timezone.now() > consulta.fecha_limite


# =========================================================
# 📊 ESTADO VISUAL DEL SLA (para templates)
# =========================================================

def estado_sla(consulta):
    """
    Devuelve:
        'vencido'
        'en_termino'
        'sin_sla'
        'finalizada'
    """

    if not consulta.fecha_limite:
        return "sin_sla"

    if consulta.estado in ["respondida", "cerrada"]:
        return "finalizada"

    if timezone.now() > consulta.fecha_limite:
        return "vencido"

    return "en_termino"


# =========================================================
# 📌 FILTRO DE CONSULTAS VENCIDAS (REUTILIZABLE)
# =========================================================

def filtrar_vencidas(queryset):

    ahora = timezone.now()

    return queryset.filter(
        fecha_limite__lt=ahora,
        estado__in=["pendiente", "en_proceso"]
    )

def obtener_turno_gestor(user):
    try:
        perfil = user.perfil_regional
        return perfil.turno if perfil.activo else None
    except RegionalUsuariosAgentes.DoesNotExist:
        return None

def es_dia_habil(fecha):
    return fecha.weekday() < 5

def horas_habiles_transcurridas(inicio, turno, fin=None):
    """Calcula horas hábiles transcurridas según turno."""
    if not fin:
        fin = timezone.now()
    if inicio >= fin or turno not in TURNOS:
        return 0

    total_horas = 0
    fecha_actual = inicio.date()
    fecha_fin = fin.date()
    config = TURNOS[turno]

    while fecha_actual <= fecha_fin:
        if es_dia_habil(fecha_actual):
            inicio_dia = timezone.make_aware(datetime.combine(fecha_actual, time(config["inicio"],0)))
            fin_dia = timezone.make_aware(datetime.combine(fecha_actual, time(config["fin"],0)))
            rango_inicio = max(inicio, inicio_dia)
            rango_fin = min(fin, fin_dia)
            if rango_inicio < rango_fin:
                total_horas += (rango_fin - rango_inicio).total_seconds() / 3600
        fecha_actual += timedelta(days=1)

    return round(total_horas, 2)

def progreso_sla(consulta, user):
    """Calcula porcentaje de SLA consumido y color del semáforo."""
    turno = obtener_turno_gestor(user)
    if not turno or not consulta.fecha_creacion:
        return None

    horas = horas_habiles_transcurridas(consulta.fecha_creacion, turno)
    porcentaje = (horas / SLA_HORAS_DEFAULT) * 100
    color = "success" if porcentaje <= 60 else "warning" if porcentaje <= 85 else "orange" if porcentaje <= 100 else "danger"

    return {
        "porcentaje": round(min(porcentaje, 100), 2),
        "porcentaje_real": round(porcentaje, 2),
        "color": color,
        "vencido": porcentaje > 100,
        "horas_consumidas": round(horas, 2),
        "horas_restantes": round(max(SLA_HORAS_DEFAULT - horas, 0), 2),
    }