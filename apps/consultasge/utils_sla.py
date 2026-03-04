from datetime import datetime, time, timedelta
from django.utils import timezone
from .utils import obtener_turno_gestor

SLA_HORAS = 48

TURNOS = {
    "manana": {
        "inicio": time(7, 0),
        "fin": time(13, 0),
    },
    "tarde": {
        "inicio": time(13, 0),
        "fin": time(18, 0),
    }
}


def es_dia_habil(fecha):
    return fecha.weekday() < 5


def horas_habiles_transcurridas(inicio, turno, fin=None):

    if not fin:
        fin = timezone.now()

    if inicio >= fin:
        return 0

    if turno not in TURNOS:
        return 0

    inicio = timezone.localtime(inicio)
    fin = timezone.localtime(fin)

    config = TURNOS[turno]

    total_horas = 0
    fecha_actual = inicio.date()
    fecha_fin = fin.date()

    while fecha_actual <= fecha_fin:

        if es_dia_habil(fecha_actual):

            inicio_dia = timezone.make_aware(
                datetime.combine(fecha_actual, config["inicio"])
            )

            fin_dia = timezone.make_aware(
                datetime.combine(fecha_actual, config["fin"])
            )

            rango_inicio = max(inicio, inicio_dia)
            rango_fin = min(fin, fin_dia)

            if rango_inicio < rango_fin:
                diferencia = rango_fin - rango_inicio
                total_horas += diferencia.total_seconds() / 3600

        fecha_actual += timedelta(days=1)

    return round(total_horas, 2)


def progreso_sla(consulta, user):

    turno = obtener_turno_gestor(user)

    if not turno:
        return None

    horas = horas_habiles_transcurridas(
        consulta.fecha_creacion,
        turno
    )

    porcentaje = (horas / SLA_HORAS) * 100

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
        "horas_restantes": round(max(SLA_HORAS - horas, 0), 2),
    }