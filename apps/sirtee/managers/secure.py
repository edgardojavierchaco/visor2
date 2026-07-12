from apps.sirtee.managers.base import SirteeManager

from apps.sirtee.services.alcance import AlcanceSirtee



# ======================================================
# MANAGER SEGURO RELEVAMIENTOS
# ======================================================

class RelevamientoManager(SirteeManager):
    """
    Manager con control de alcance SIRTEE.

    Filtra por CUEANEXO permitido.
    """

    def permitidos(
        self,
        usuario
    ):

        cueanexos = (
            AlcanceSirtee
            .cueanexos(usuario)
        )


        return (
            self.get_queryset()
            .filter(
                cueanexo__in=cueanexos
            )
        )





# ======================================================
# MANAGER SEGURO HALLAZGOS
# ======================================================

class HallazgoManager(SirteeManager):
    """
    Manager seguro de Hallazgos.

    El acceso se hereda desde
    Relevamiento.
    """

    def permitidos(
        self,
        usuario
    ):

        cueanexos = (
            AlcanceSirtee
            .cueanexos(usuario)
        )


        return (
            self.get_queryset()
            .filter(
                relevamiento__cueanexo__in=cueanexos
            )
        )





# ======================================================
# MANAGER SEGURO INTERVENCIONES
# ======================================================

class IntervencionManager(SirteeManager):
    """
    Manager seguro de Intervenciones.

    El acceso se hereda desde
    Hallazgo -> Relevamiento.
    """

    def permitidos(
        self,
        usuario
    ):

        cueanexos = (
            AlcanceSirtee
            .cueanexos(usuario)
        )


        return (
            self.get_queryset()
            .filter(
                hallazgo__relevamiento__cueanexo__in=cueanexos
            )
        )