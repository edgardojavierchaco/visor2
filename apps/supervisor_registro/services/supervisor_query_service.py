# services/supervisor_query_service.py
from django.db.models import Prefetch, Q

from apps.supervisor_registro.models import (
    ABMSupervisores,
    SupervisorRegional,
    SupervisorRegionalNivel,
    SupervisorRegionalOferta,
    SupervisorSituacionRevista,
)


class SupervisorQueryService:
    """Consultas optimizadas y centralizadas de supervisores."""

    @staticmethod
    def base(regiones=None):
        """
        Query base.
        regiones=None significa alcance global.
        Si se proporciona una lista, también se limita el prefetch de
        regionales para evitar filtrar registros pero luego exponer regiones
        fuera del alcance del usuario.
        """
        regional_qs = (
            SupervisorRegional.objects
            .filter(activo=True)
            .select_related("region")
            .prefetch_related(
                Prefetch(
                    "niveles",
                    queryset=(
                        SupervisorRegionalNivel.objects
                        .filter(activo=True)
                        .select_related("nivel")
                    ),
                ),
                Prefetch(
                    "ofertas",
                    queryset=(
                        SupervisorRegionalOferta.objects
                        .filter(activo=True)
                    ),
                ),
            )
        )

        if regiones is not None:
            regional_qs = regional_qs.filter(region_id__in=regiones)

        return (
            ABMSupervisores.objects
            .filter(activo=True)
            .select_related("usuario")
            .prefetch_related(
                Prefetch(
                    "situaciones",
                    queryset=(
                        SupervisorSituacionRevista.objects
                        .filter(activo=True)
                        .select_related("situacion_revista")
                    ),
                ),
                Prefetch(
                    "asignaciones_regionales",
                    queryset=regional_qs,
                ),
            )
            .order_by("usuario__apellido", "usuario__nombres", "pk")
        )

    @staticmethod
    def por_regiones(queryset, regiones):
        if regiones is None:
            return queryset
        if not regiones:
            return queryset.none()
        return queryset.filter(
            asignaciones_regionales__activo=True,
            asignaciones_regionales__region_id__in=regiones,
        ).distinct()

    @staticmethod
    def buscar(queryset, texto):
        texto = (texto or "").strip()
        if not texto:
            return queryset

        return queryset.filter(
            Q(usuario__apellido__icontains=texto)
            | Q(usuario__nombres__icontains=texto)
            | Q(usuario__username__icontains=texto)
        ).distinct()

    @staticmethod
    def filtrar_region(queryset, region):
        if not region:
            return queryset
        return queryset.filter(
            asignaciones_regionales__activo=True,
            asignaciones_regionales__region_id=region,
        ).distinct()

    @staticmethod
    def filtrar_situacion(queryset, situacion):
        if not situacion:
            return queryset
        return queryset.filter(
            situaciones__activo=True,
            situaciones__situacion_revista_id=situacion,
        ).distinct()

    @staticmethod
    def filtrar_nivel(queryset, nivel):
        if not nivel:
            return queryset
        return queryset.filter(
            asignaciones_regionales__activo=True,
            asignaciones_regionales__niveles__activo=True,
            asignaciones_regionales__niveles__nivel_id=nivel,
        ).distinct()

    @classmethod
    def filtros(cls, queryset, q="", region=None, situacion=None, nivel=None):
        queryset = cls.buscar(queryset, q)
        queryset = cls.filtrar_region(queryset, region)
        queryset = cls.filtrar_situacion(queryset, situacion)
        queryset = cls.filtrar_nivel(queryset, nivel)
        return queryset

