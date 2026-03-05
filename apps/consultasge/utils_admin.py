from django.db.models import Count, Q
from django.utils import timezone
from .models import Consulta, SLA_HORAS_DEFAULT
from apps.usuarios.models_regional import RegionalUsuariosAgentes
from .utils import horas_habiles_transcurridas

def consultas_por_gestor(fecha_inicio=None, fecha_fin=None, region_filtro=None):
    # 1. Filtros base para la consulta
    filtros = Q(gestor_asignado__isnull=False)
    if fecha_inicio:
        filtros &= Q(fecha_creacion__gte=fecha_inicio)
    if fecha_fin:
        filtros &= Q(fecha_creacion__lte=fecha_fin)
    if region_filtro:
        filtros &= Q(region__iexact=region_filtro)

    # 2. Obtenemos las consultas y los perfiles de gestores (Evitando N+1)
    consultas_qs = Consulta.objects.filter(filtros)
    perfiles_qs = RegionalUsuariosAgentes.objects.filter(activo=True)
    
    # Mapeo de perfiles para acceso rápido: {username: objeto_perfil}
    mapa_perfiles = {p.usuario: p for p in perfiles_qs}
    
    # 3. Agrupación inicial por base de datos (Conteos básicos)
    resumen_db = consultas_qs.values("gestor_asignado").annotate(
        pendiente=Count("id", filter=Q(estado="pendiente")),
        en_proceso=Count("id", filter=Q(estado="en_proceso")),
        respondida=Count("id", filter=Q(estado="respondida")),
        cerrada=Count("id", filter=Q(estado="cerrada")),
    )

    data_gestores = {}
    total_vencidas_global = 0

    # 4. Cálculo preciso de Vencidas y SLA por gestor
    for item in resumen_db:
        username = item["gestor_asignado"]
        perfil = mapa_perfiles.get(username)
        
        # Filtramos las consultas de ESTE gestor para calcular vencimientos reales
        consultas_gestor = consultas_qs.filter(gestor_asignado=username, estado__in=["pendiente", "en_proceso"])
        
        vencidas_reales = 0
        for c in consultas_gestor:
            # Usamos tu lógica de horas hábiles según el turno del gestor
            if perfil and perfil.turno:
                horas = horas_habiles_transcurridas(c.fecha_creacion, perfil.turno)
                if horas > SLA_HORAS_DEFAULT:
                    vencidas_reales += 1
            else:
                # Si no tiene perfil/turno, usamos tiempo cronológico como fallback
                if c.fecha_limite and timezone.now() > c.fecha_limite:
                    vencidas_reales += 1

        total_vencidas_global += vencidas_reales
        total_resueltas = item["respondida"] + item["cerrada"]
        total_consultas = item["pendiente"] + item["en_proceso"] + total_resueltas

        data_gestores[username] = {
            "region": perfil.region_loc if perfil else "N/A",
            "pendiente": item["pendiente"],
            "en_proceso": item["en_proceso"],
            "respondida": item["respondida"],
            "cerrada": item["cerrada"],
            "vencidas": vencidas_reales,
            "SLA_promedio": round((total_resueltas / total_consultas * 100), 2) if total_consultas > 0 else 0
        }

    # 5. KPIs para los cuadros superiores del Dashboard
    totales_kpi = {
        "total_consultas": sum(item["pendiente"] + item["en_proceso"] + item["respondida"] + item["cerrada"] for item in resumen_db),
        "total_pendientes": sum(item["pendiente"] for item in resumen_db),
        "total_en_proceso": sum(item["en_proceso"] for item in resumen_db),
        "total_vencidas": total_vencidas_global
    }

    return data_gestores, totales_kpi