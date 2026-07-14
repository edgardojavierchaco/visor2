# apps/sirtee/services/permisos.py

from django.db.models import Func, CharField

from apps.supervisa2.models.supervisor import RegionalUsuario
from apps.consultasge.models_padron import CapaUnicaOfertas



# ======================================================
# FUNCION POSTGRESQL REGEXP_REPLACE
# ======================================================

class RegexpReplace(Func):

    function = "REGEXP_REPLACE"
    arity = 3



# ======================================================
# SERVICIO CENTRAL DE PERMISOS SIRTEE
# ======================================================

class PermisosSirtee:
    """
    Servicio centralizado de permisos SIRTEE.

    Fuentes:

    Usuario:
        apps.usuarios

    Rol:
        usuario.perfil.rol

    Regionales:
        apps.supervisa2.RegionalUsuario

    Escuelas:
        apps.consultasge.CapaUnicaOfertas
    """



    # ==================================================
    # OBTENER ROL
    # ==================================================

    @staticmethod
    def obtener_rol(usuario):

        try:
            return usuario.perfil.rol

        except AttributeError:
            return None



    # ==================================================
    # OBTENER CATEGORIA
    # ==================================================

    @staticmethod
    def categoria(usuario):

        rol = PermisosSirtee.obtener_rol(usuario)

        if rol:
            return rol.categoria_acceso

        return None



    # ==================================================
    # SUPERUSUARIO
    # ==================================================

    @staticmethod
    def es_superusuario(usuario):

        return (
            usuario.is_superuser
        )



    # ==================================================
    # INFRAESTRUCTURA
    # ==================================================

    @staticmethod
    def es_infraestructura(usuario):

        rol = PermisosSirtee.obtener_rol(usuario)

        if not rol:
            return False


        return (
            rol.nombre.lower()
            ==
            "infraestructura"
        )



    # ==================================================
    # ACCESO GLOBAL
    # Mapa / Indicadores
    # ==================================================

    @staticmethod
    def es_global(usuario):

        """
        Acceso global para:

        - Superusuario
        - Infraestructura
        - Ministro
        - Subsecretario
        - Director General
        """

        if PermisosSirtee.es_superusuario(usuario):

            return True


        categoria = (
            PermisosSirtee.categoria(usuario)
        )


        return categoria == "all"



    # ==================================================
    # MAPA
    # ==================================================

    @staticmethod
    def puede_ver_mapa(usuario):

        if PermisosSirtee.es_global(usuario):

            return True


        categoria = (
            PermisosSirtee.categoria(usuario)
        )


        return categoria == "regional"



    # ==================================================
    # INDICADORES
    # ==================================================

    @staticmethod
    def puede_ver_indicadores(usuario):

        return (
            PermisosSirtee
            .puede_ver_mapa(usuario)
        )



    # ==================================================
    # RELEVAMIENTOS
    # ==================================================

    @staticmethod
    def puede_ver_relevamientos(usuario):

        """
        Gestión técnica:

        Permitido:

        - Superusuario
        - Infraestructura
        - Director por CUEANEXO

        """

        if PermisosSirtee.es_superusuario(usuario):

            return True



        if PermisosSirtee.es_infraestructura(usuario):

            return True



        categoria = (
            PermisosSirtee.categoria(usuario)
        )


        return categoria == "propio"



    # ==================================================
    # HALLAZGOS
    # ==================================================

    @staticmethod
    def puede_ver_hallazgos(usuario):

        return (
            PermisosSirtee
            .puede_ver_relevamientos(usuario)
        )



    # ==================================================
    # INTERVENCIONES
    # ==================================================

    @staticmethod
    def puede_ver_intervenciones(usuario):

        return (
            PermisosSirtee
            .puede_ver_relevamientos(usuario)
        )



    # ==================================================
    # REGIONALES DEL USUARIO
    # ==================================================

    @staticmethod
    def regionales_usuario(usuario):

        return (
            RegionalUsuario.objects
            .filter(
                usuario=usuario.username,
                activo=True
            )
            .values_list(
                "region_loc",
                flat=True
            )
        )



    # ==================================================
    # ESCUELAS PERMITIDAS
    # ==================================================

    @staticmethod
    def escuelas_usuario(usuario):

        """
        Devuelve queryset de escuelas
        permitidas por SIRTEE.
        """


        # ----------------------------------
        # GLOBAL
        # ----------------------------------

        if PermisosSirtee.es_global(usuario):

            return (
                CapaUnicaOfertas.objects.all()
            )



        categoria = (
            PermisosSirtee.categoria(usuario)
        )



        # ----------------------------------
        # REGIONAL
        # ----------------------------------

        if categoria == "regional":

            regiones = (
                PermisosSirtee
                .regionales_usuario(usuario)
            )


            return (
                CapaUnicaOfertas.objects
                .filter(
                    region_loc__in=regiones
                )
            )



        # ----------------------------------
        # DIRECTOR
        # ----------------------------------

        if categoria == "propio":


            cuit = (
                usuario.username
                .replace("-", "")
                .replace(".", "")
                .replace(" ", "")
            )


            return (
                CapaUnicaOfertas.objects
                .annotate(

                    cuit_limpio=RegexpReplace(
                        "resploc_cuitcuil",
                        r"[^0-9]",
                        "",
                        output_field=CharField()
                    )

                )
                .filter(
                    cuit_limpio=cuit
                )
            )



        return (
            CapaUnicaOfertas.objects.none()
        )



    # ==================================================
    # CUEANEXOS PERMITIDOS
    # ==================================================

    @staticmethod
    def cueanexos_usuario(usuario):

        return (
            PermisosSirtee
            .escuelas_usuario(usuario)
            .values_list(
                "cueanexo",
                flat=True
            )
        )


    # ==================================================
    # GESTIÓN SIRTEE
    # ==================================================

    @staticmethod
    def puede_gestionar(usuario):
        """
        Puede crear, modificar y eliminar registros.
        """

        return (
            PermisosSirtee.es_superusuario(usuario)
            or
            PermisosSirtee.es_infraestructura(usuario)
        )
        
    
    @staticmethod
    def puede_crear_relevamientos(usuario):
        return PermisosSirtee.puede_gestionar(usuario)


    @staticmethod
    def puede_editar_relevamientos(usuario):
        return PermisosSirtee.puede_gestionar(usuario)


    @staticmethod
    def puede_eliminar_relevamientos(usuario):
        return PermisosSirtee.puede_gestionar(usuario)
    
    
    @staticmethod
    def puede_crear_hallazgos(usuario):
        return PermisosSirtee.puede_gestionar(usuario)


    @staticmethod
    def puede_editar_hallazgos(usuario):
        return PermisosSirtee.puede_gestionar(usuario)


    @staticmethod
    def puede_eliminar_hallazgos(usuario):
        return PermisosSirtee.puede_gestionar(usuario)
    
    
    @staticmethod
    def puede_crear_intervenciones(usuario):
        return PermisosSirtee.puede_gestionar(usuario)


    @staticmethod
    def puede_editar_intervenciones(usuario):
        return PermisosSirtee.puede_gestionar(usuario)


    @staticmethod
    def puede_eliminar_intervenciones(usuario):
        return PermisosSirtee.puede_gestionar(usuario)