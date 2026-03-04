# apps/consultasge/utils_admin.py
from apps.consultasge.models import Consulta
from apps.consultasge.utils import horas_habiles_transcurridas, obtener_turno_gestor, SLA_HORAS_DEFAULT
from apps.usuarios.models_regional import RegionalUsuariosAgentes
from django.utils import timezone
from datetime import timedelta

def consultas_por_gestor(fecha_inicio=None, fecha_fin=None):
    """
    Retorna un dict por cada gestor con:
    - username, región, turno
    - conteo por estado y SLA promedio
    - conteo semanal y mensual
    """
    qs = Consulta.objects.all()
    if fecha_inicio:
        qs = qs.filter(fecha_creacion__gte=fecha_inicio)
    if fecha_fin:
        qs = qs.filter(fecha_creacion__lte=fecha_fin)

    ahora = timezone.now()
    data = {}

    # Obtener todos los usuarios únicos en las consultas
    usuarios = set([c.usuario.username for c in qs])

    for username in usuarios:
        qs_g = qs.filter(usuario__username=username)

        stats = {}
        # Estados
        lista_estados = ["pendiente","en_proceso","respondida","cerrada"]
        for estado in lista_estados:
            stats[estado] = qs_g.filter(estado=estado).count()

        # Vencidas
        stats["vencidas"] = qs_g.filter(fecha_limite__lt=ahora, estado__in=["pendiente","en_proceso"]).count()

        # SLA promedio
        if qs_g.exists():
            total_horas = sum([horas_habiles_transcurridas(c.fecha_creacion, obtener_turno_gestor(c.usuario)) for c in qs_g])
            promedio = (total_horas / qs_g.count()) / SLA_HORAS_DEFAULT * 100
            stats["SLA_promedio"] = round(promedio, 2)
        else:
            stats["SLA_promedio"] = 0

        # Conteo semanal
        inicio_semana = ahora - timedelta(days=7)
        stats["semanal"] = qs_g.filter(fecha_creacion__gte=inicio_semana).count()

        # Conteo mensual
        inicio_mes = ahora - timedelta(days=30)
        stats["mensual"] = qs_g.filter(fecha_creacion__gte=inicio_mes).count()

        # Obtener región y turno desde RegionalUsuariosAgentes
        try:
            perfil = RegionalUsuariosAgentes.objects.get(usuario__username=username)
            stats["region"] = perfil.region_loc
            stats["turno"] = perfil.turno
        except RegionalUsuariosAgentes.DoesNotExist:
            stats["region"] = "Sin asignar"
            stats["turno"] = "Sin asignar"

        data[username] = stats

    return data