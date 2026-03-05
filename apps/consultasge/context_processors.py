# apps/consultasge/context_processors.py
from django.utils import timezone
from django.db.models import Count, Q
from .models import Consulta

def consultas_notificaciones(request):
    if not request.user.is_authenticated:
        return {}

    consultas = Consulta.objects.filter(usuario=request.user)

    stats = consultas.aggregate(
        pendientes=Count('id', filter=Q(estado=Consulta.Estado.PENDIENTE)),
        en_proceso=Count('id', filter=Q(estado=Consulta.Estado.EN_PROCESO)),
        vencidas=Count('id', filter=Q(
            fecha_limite__lt=timezone.now(),
            estado__in=[Consulta.Estado.PENDIENTE, Consulta.Estado.EN_PROCESO]
        ))
    )

    return {
        "float_pendientes": stats['pendientes'],
        "float_en_proceso": stats['en_proceso'],
        "float_vencidas": stats['vencidas'],
        "float_total_activas": stats['pendientes'] + stats['en_proceso']
    }