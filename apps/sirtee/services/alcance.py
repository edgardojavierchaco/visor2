# apps/sirtee/services/alcance.py
from django.db.models import Func, F, Value, CharField
from apps.sirtee.services.permisos import PermisosSirtee
from apps.consultasge.models_padron import CapaUnicaOfertas
from apps.supervisa2.models.supervisor import RegionalUsuario
from django.db.models.functions import Cast
from django.db.models import CharField


class RegexpReplace(Func):

    function = "REGEXP_REPLACE"
    arity = 3




class AlcanceSirtee:


    # ==================================================
    # MAPA
    # ==================================================

    @staticmethod
    def mapa(usuario):

        if PermisosSirtee.es_global(usuario):

            return CapaUnicaOfertas.objects.all()


        categoria = PermisosSirtee.categoria(usuario)


        if categoria == "regional":

            return CapaUnicaOfertas.objects.filter(
                region_loc__in=
                AlcanceSirtee.regionales(usuario)
            )


        if categoria == "propio":

            return AlcanceSirtee.escuelas_director(usuario)


        return CapaUnicaOfertas.objects.none()



    # ==================================================
    # INDICADORES
    # ==================================================

    @staticmethod
    def indicadores(usuario):

        return AlcanceSirtee.mapa(usuario)



    # ==================================================
    # CUEANEXOS PERMITIDOS
    # ==================================================

    @staticmethod
    def cueanexos(usuario):

        return (
            AlcanceSirtee
            .relevamientos(usuario)
            .annotate(
                cueanexo_texto=Cast(
                    "cueanexo",
                    output_field=CharField()
                )
            )
            .values_list(
                "cueanexo_texto",
                flat=True
            )
        )



    # ==================================================
    # RELEVAMIENTOS
    # ==================================================

    @staticmethod
    def relevamientos(usuario):


        if PermisosSirtee.es_global(usuario):

            return CapaUnicaOfertas.objects.all()



        categoria = PermisosSirtee.categoria(usuario)



        if categoria == "regional":

            return (
                CapaUnicaOfertas.objects
                .filter(
                    region_loc__in=
                    AlcanceSirtee.regionales(usuario)
                )
            )



        if categoria == "propio":

            return (
                AlcanceSirtee
                .escuelas_director(usuario)
            )



        return (
            CapaUnicaOfertas.objects.none()
        )



    # ==================================================
    # HALLAZGOS
    # ==================================================

    @staticmethod
    def hallazgos(usuario):

        return AlcanceSirtee.cueanexos(usuario)



    # ==================================================
    # INTERVENCIONES
    # ==================================================

    @staticmethod
    def intervenciones(usuario):

        return AlcanceSirtee.cueanexos(usuario)



    # ==================================================
    # REGIONALES
    # ==================================================

    @staticmethod
    def regionales(usuario):

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
    # DIRECTOR
    # ==================================================

    @staticmethod
    def escuelas_director(usuario):


        cuit = (
            usuario.username
            .replace("-", "")
            .replace(".", "")
            .replace(" ", "")
        )


        return (
            CapaUnicaOfertas.objects
            .annotate(
                cuit_limpio=Func(
                    F("resploc_cuitcuil"),
                    Value(r"[^0-9]"),
                    Value(""),
                    Value("g"),
                    function="REGEXP_REPLACE",
                    output_field=CharField(),
                )
            )
            .filter(
                cuit_limpio=cuit
            )
        )