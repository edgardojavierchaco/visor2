from django.db.models import (
    Count,
    Avg,
)

from apps.sirtee.models.relevamientos import Relevamiento
from apps.sirtee.models.hallazgos import Hallazgo
from apps.sirtee.models.intervenciones import Intervencion
from apps.sirtee.models.empresas import Empresa



class DashboardSIRTEE:


    """
    Servicio central de indicadores SIRTEE.
    """



    @staticmethod
    def escuelas_relevadas():

        return (
            Relevamiento.objects
            .values(
                "cueanexo"
            )
            .distinct()
            .count()
        )



    @staticmethod
    def total_relevamientos():

        return (
            Relevamiento.objects
            .activos()
            .count()
        )



    @staticmethod
    def relevamientos_estado():

        return (

            Relevamiento.objects
            .values(
                "estado",
            )
            .annotate(
                cantidad=Count("id")
            )
            .order_by(
                "estado"
            )

        )



    @staticmethod
    def total_hallazgos():

        return Hallazgo.objects.count()



    @staticmethod
    def hallazgos_criticos():

        return (

            Hallazgo.objects
            .filter(
                criticidad__codigo="CRITICA"
            )
            .count()

        )



    @staticmethod
    def hallazgos_abiertos():

        return (

            Hallazgo.objects
            .filter(
                estado__codigo="ABIERTO"
            )
            .count()

        )



    @staticmethod
    def hallazgos_por_criticidad():

        return (

            Hallazgo.objects
            .values(
                "criticidad__codigo",
                "criticidad__nombre"
            )
            .annotate(
                total=Count("id")
            )

        )



    @staticmethod
    def intervenciones_pendientes():

        return (

            Intervencion.objects
            .filter(
                estado__codigo__in=[
                    "PENDIENTE",
                    "EN_EJECUCION"
                ]
            )
            .count()

        )



    @staticmethod
    def avance_obras():

        resultado = (

            Intervencion.objects
            .aggregate(
                promedio=Avg(
                    "porcentaje_avance"
                )
            )

        )


        return round(
            resultado["promedio"] or 0,
            2
        )



    @staticmethod
    def empresas_activas():

        return (

            Empresa.objects
            .filter(
                activa=True
            )
            .count()

        )



    @classmethod
    def resumen(cls):

        return {

            "escuelas_relevadas":
                cls.escuelas_relevadas(),


            "total_relevamientos":
                cls.total_relevamientos(),


            "total_hallazgos":
                cls.total_hallazgos(),


            "hallazgos_criticos":
                cls.hallazgos_criticos(),


            "hallazgos_abiertos":
                cls.hallazgos_abiertos(),


            "intervenciones_pendientes":
                cls.intervenciones_pendientes(),


            "avance_obras":
                cls.avance_obras(),


            "empresas_activas":
                cls.empresas_activas(),


            "relevamientos_estado":
                cls.relevamientos_estado(),


            "hallazgos_por_criticidad":
                cls.hallazgos_por_criticidad(),

        }