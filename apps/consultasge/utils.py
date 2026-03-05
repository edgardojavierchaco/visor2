# apps/consultasge/utils.py
from datetime import datetime, timedelta, time
from django.utils import timezone
from django.core.exceptions import PermissionDenied
from apps.usuarios.models_regional import RegionalUsuariosAgentes
from .models import Consulta
from .constants import SLA_HORAS_DEFAULT, TURNOS

# --------------------------
# Días hábiles
# --------------------------
def es_dia_habil(fecha):
    return fecha.weekday() < 5  # lunes=0 ... viernes=4

# --------------------------
# Horas hábiles transcurridas según turno
# --------------------------
def horas_habiles_transcurridas(inicio, turno, fin=None):
    if not fin:
        fin = timezone.now()
    if inicio >= fin or turno not in TURNOS:
        return 0

    inicio = timezone.localtime(inicio)
    fin = timezone.localtime(fin)
    config = TURNOS[turno]
    total_horas = 0
    fecha_actual = inicio.date()
    fecha_fin = fin.date()

    while fecha_actual <= fecha_fin:
        if es_dia_habil(fecha_actual):
            inicio_dia = timezone.make_aware(datetime.combine(fecha_actual, time(config["inicio"], 0)))
            fin_dia = timezone.make_aware(datetime.combine(fecha_actual, time(config["fin"], 0)))
            rango_inicio = max(inicio, inicio_dia)
            rango_fin = min(fin, fin_dia)
            if rango_inicio < rango_fin:
                total_horas += (rango_fin - rango_inicio).total_seconds() / 3600
        fecha_actual += timedelta(days=1)
    return round(total_horas, 2)

# --------------------------
# Turno activo del gestor
# --------------------------
def obtener_turno_gestor(user, region=None):
    query = RegionalUsuariosAgentes.objects.filter(
        usuario=user.username, 
        activo=True
    )
    
    # Si nos pasan una región, buscamos el turno específico de esa región
    if region:
        perfil = query.filter(region_loc__iexact=region).first()
    else:
        # Si no hay región (fallback), tomamos el primero que encuentre
        perfil = query.first()
    
    return perfil.turno if perfil else None

# --------------------------
# Progreso SLA
# --------------------------
def progreso_sla(consulta, user):
    # Pasamos la región de la consulta para obtener el turno exacto de ese gestor en esa zona
    turno = obtener_turno_gestor(user, region=consulta.region)
    
    if not turno:
        return None

    horas = horas_habiles_transcurridas(consulta.fecha_creacion, turno)
    porcentaje = (horas / SLA_HORAS_DEFAULT) * 100

    if porcentaje <= 60:
        color = "success"
    elif porcentaje <= 85:
        color = "warning"
    elif porcentaje <= 100:
        color = "orange"
    else:
        color = "danger"

    return {
        "porcentaje": round(min(porcentaje, 100), 2),
        "porcentaje_real": round(porcentaje, 2),
        "color": color,
        "vencido": porcentaje > 100,
        "horas_consumidas": round(horas, 2),
        "horas_restantes": round(max(SLA_HORAS_DEFAULT - horas, 0), 2),
    }

# --------------------------
# Estado SLA
# --------------------------
def estado_sla(consulta):
    if not consulta.fecha_limite:
        return "sin_sla"
    if consulta.estado in [Consulta.Estado.RESPONDIDA, Consulta.Estado.CERRADA]:
        return "finalizada"
    if timezone.now() > consulta.fecha_limite:
        return "vencido"
    return "en_termino"

# --------------------------
# Validar que la consulta pertenece a la región del usuario
# --------------------------
def validar_consulta_regional(consulta, user):
    # Ya no existe user.perfiles_regionales, buscamos en el modelo
    perfiles = RegionalUsuariosAgentes.objects.filter(
        usuario=user.username, 
        activo=True
    )
    
    if not perfiles.exists():
        raise PermissionDenied("No tiene regional asignada.")
        
    regiones = [str(p.region_loc).lower() for p in perfiles]
    if str(consulta.region).lower() not in regiones:
        raise PermissionDenied("No pertenece a su regional.")
    return True

# --------------------------
# Filtrar consultas vencidas
# --------------------------
def filtrar_vencidas(queryset):
    ahora = timezone.now()
    return queryset.filter(
        fecha_limite__lt=ahora,
        estado__in=[Consulta.Estado.PENDIENTE, Consulta.Estado.EN_PROCESO]
    )