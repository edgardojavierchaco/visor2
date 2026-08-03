from apps.supervisa2.models import (
    SituacionRevista,
    NivelModalidad,
    Region,
)

from .permission_service import get_responsable


class CatalogoService:
    """
    Servicio para cargar catálogos utilizados
    en formularios y filtros.
    """


    @staticmethod
    def contexto(user=None):

        context = {


            "situaciones":

                SituacionRevista.objects
                .all()
                .order_by(
                    "nombre"
                ),



            "niveles":

                NivelModalidad.objects
                .all()
                .order_by(
                    "nombre"
                ),


            "regiones":

                Region.objects.none(),


        }


        if user:

            context["regiones"] = (
                CatalogoService
                .regiones_usuario(user)
            )


        return context



    @staticmethod
    def regiones_usuario(user):
        """
        Regiones visibles según alcance.
        """


        if user.is_superuser:

            return (
                Region.objects
                .all()
                .order_by("nombre")
            )



        if user.nivelacceso in [
            "Administrador",
            "Funcionario",
        ]:

            return (
                Region.objects
                .all()
                .order_by("nombre")
            )



        responsable = get_responsable(user)



        if not responsable:

            return Region.objects.none()



        return (
            responsable.regiones
            .all()
            .order_by("nombre")
        )