# services/supervisor_query_service.py

from django.db.models import Prefetch, Q

from apps.supervisor_registro.models import (
    ABMSupervisores,
    SupervisorRegional,
    SupervisorSituacionRevista,
    SupervisorRegionalNivel,
    SupervisorRegionalOferta,
)


class SupervisorQueryService:
    """
    Servicio de consultas para supervisores.

    Centraliza toda la lógica de búsqueda y filtrado.
    """

    @staticmethod
    def base():
        """
        Query base optimizada.
        """

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
                    )
                ),

                Prefetch(
                    "asignaciones_regionales",
                    queryset=(
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
                                )
                            ),

                            Prefetch(
                                "ofertas",
                                queryset=(
                                    SupervisorRegionalOferta.objects
                                    .filter(activo=True)
                                )
                            )

                        )
                    )
                )

            )
        )

    # =====================================================
    # PERMISOS
    # =====================================================

    @staticmethod
    def por_regiones(queryset, regiones):
        """
        regiones:
            None -> acceso total (Administrador)
            []   -> sin acceso
            [1,2]-> regiones permitidas
        """

        if regiones is None:
            return queryset

        if not regiones:
            return queryset.none()

        return (
            queryset
            .filter(
                asignaciones_regionales__activo=True,
                asignaciones_regionales__region_id__in=regiones,
            )
            .distinct()
        )

    # =====================================================
    # BUSQUEDA
    # =====================================================

    @staticmethod
    def buscar(queryset, texto):

        if not texto:
            return queryset

        return (
            queryset
            .filter(

                Q(usuario__apellido__icontains=texto) |
                Q(usuario__nombres__icontains=texto) |
                Q(usuario__username__icontains=texto)

            )
            .distinct()
        )

    # =====================================================
    # FILTRO REGION
    # =====================================================

    @staticmethod
    def filtrar_region(queryset, region):

        if not region:
            return queryset

        return (
            queryset
            .filter(
                asignaciones_regionales__activo=True,
                asignaciones_regionales__region_id=region,
            )
            .distinct()
        )

    # =====================================================
    # FILTRO SITUACION
    # =====================================================

    @staticmethod
    def filtrar_situacion(queryset, situacion):

        if not situacion:
            return queryset

        return (
            queryset
            .filter(
                situaciones__activo=True,
                situaciones__situacion_revista_id=situacion,
            )
            .distinct()
        )

    # =====================================================
    # FILTRO NIVEL
    # =====================================================

    @staticmethod
    def filtrar_nivel(queryset, nivel):

        if not nivel:
            return queryset

        return (
            queryset
            .filter(
                asignaciones_regionales__activo=True,
                asignaciones_regionales__niveles__activo=True,
                asignaciones_regionales__niveles__nivel_id=nivel,
            )
            .distinct()
        )

    # =====================================================
    # FILTROS GENERALES
    # =====================================================

    @classmethod
    def filtros(
        cls,
        queryset,
        q="",
        region=None,
        situacion=None,
        nivel=None,
    ):

        queryset = cls.buscar(queryset, q)

        queryset = cls.filtrar_region(
            queryset,
            region,
        )

        queryset = cls.filtrar_situacion(
            queryset,
            situacion,
        )

        queryset = cls.filtrar_nivel(
            queryset,
            nivel,
        )

        return queryset