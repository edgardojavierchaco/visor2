from django.db.models import Q

from apps.supervisor_registro.models import (
    ABMSupervisores,
    SupervisorRegional,
    SupervisorRegionalOferta,
)

from apps.consultasge.models import CapaUnicaOfertas


class SupervisorQueryService:
    """
    Capa de consultas para Supervisor Registro.

    Centraliza:
    - supervisores
    - escuelas asignadas
    - ofertas
    - alcance territorial
    """

    # =====================================================
    # SUPERVISORES
    # =====================================================

    @staticmethod
    def todos():
        """
        Todos los supervisores activos.
        """

        return (
            ABMSupervisores.objects
            .select_related(
                "persona",
                "situacion_revista",
            )
            .filter(
                activo=True
            )
            .order_by(
                "persona__apellido",
                "persona__nombre"
            )
        )


    @staticmethod
    def buscar(texto=None):

        qs = SupervisorQueryService.todos()

        if texto:

            qs = qs.filter(
                Q(persona__apellido__icontains=texto)
                |
                Q(persona__nombre__icontains=texto)
                |
                Q(dni__icontains=texto)
            )

        return qs



    # =====================================================
    # SUPERVISORES REGIONALES
    # =====================================================

    @staticmethod
    def regionales():

        return (
            SupervisorRegional.objects
            .select_related(
                "supervisor",
                "regional"
            )
            .filter(
                activo=True
            )
        )


    @staticmethod
    def supervisor_regional(id_supervisor):

        return (
            SupervisorRegional.objects
            .select_related(
                "supervisor",
                "regional"
            )
            .filter(
                supervisor_id=id_supervisor,
                activo=True
            )
        )



    # =====================================================
    # OFERTAS ASIGNADAS
    # =====================================================

    @staticmethod
    def ofertas_supervisor(id_supervisor):

        return (
            SupervisorRegionalOferta.objects
            .select_related(
                "oferta"
            )
            .filter(
                supervisor_id=id_supervisor,
                activo=True
            )
        )



    @staticmethod
    def cueanexos_supervisor(id_supervisor):

        return (
            SupervisorRegionalOferta.objects
            .filter(
                supervisor_id=id_supervisor,
                activo=True
            )
            .values_list(
                "oferta__cueanexo",
                flat=True
            )
            .distinct()
        )



    # =====================================================
    # ESCUELAS
    # =====================================================

    @staticmethod
    def escuelas_supervisor(id_supervisor):

        cueanexos = (
            SupervisorQueryService
            .cueanexos_supervisor(id_supervisor)
        )


        return (
            CapaUnicaOfertas.objects
            .filter(
                cueanexo__in=cueanexos
            )
            .order_by(
                "nom_est"
            )
        )



    # =====================================================
    # DASHBOARD
    # =====================================================

    @staticmethod
    def resumen(id_supervisor):

        cueanexos = list(
            SupervisorQueryService
            .cueanexos_supervisor(id_supervisor)
        )


        return {

            "total_escuelas":
                len(cueanexos),


            "total_ofertas":
                SupervisorQueryService
                .ofertas_supervisor(id_supervisor)
                .count(),


            "escuelas":
                SupervisorQueryService
                .escuelas_supervisor(id_supervisor),

        }