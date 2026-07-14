from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.core.exceptions import ValidationError

from django.db import DatabaseError


from apps.sirtee.dashboard.services.mapa import (
    MapaSIRTEE
)



# ======================================================
# API MAPA OPERATIVO
# ======================================================


@require_GET
def mapa_api(request):
    """
    Endpoint AJAX para cargar escuelas
    del mapa operativo SIRTEE.

    Parámetros:

        region
        departamento
        criticidad
        estado

    """

    try:


        # ==============================================
        # RECEPCIÓN DE FILTROS
        # ==============================================


        region = limpiar_parametro(
            request.GET.get("region")
        )


        departamento = limpiar_parametro(
            request.GET.get("departamento")
        )


        criticidad = limpiar_parametro(
            request.GET.get("criticidad")
        )


        estado = limpiar_parametro(
            request.GET.get("estado")
        )



        # ==============================================
        # VALIDACIONES
        # ==============================================


        validar_criticidad(
            criticidad
        )


        validar_estado(
            estado
        )



        # ==============================================
        # CONSULTA SERVICIO
        # ==============================================


        escuelas = (
            MapaSIRTEE
            .escuelas_operativas(

                region=region,

                departamento=departamento,

                criticidad=criticidad,

                estado_intervencion=estado,

            )
        )



        # ==============================================
        # RESPUESTA
        # ==============================================


        return JsonResponse(

            {

                "success": True,


                "cantidad": len(
                    escuelas
                ),


                "data": escuelas,

            },

            safe=False

        )



    except ValidationError as e:


        return JsonResponse(

            {

                "success": False,


                "error": str(e),

            },

            status=400

        )



    except DatabaseError:


        return JsonResponse(

            {

                "success": False,


                "error":

                "Error consultando información territorial.",

            },

            status=500

        )



    except Exception as e:


        return JsonResponse(

            {

                "success": False,


                "error":

                "Error interno del servidor.",


                "detalle":

                str(e),

            },

            status=500

        )





# ======================================================
# LIMPIEZA DE PARAMETROS
# ======================================================


def limpiar_parametro(valor):

    """
    Normaliza valores recibidos
    desde filtros del mapa.
    """

    if not valor:

        return None


    valor = valor.strip()


    if valor == "":

        return None


    return valor.upper()





# ======================================================
# VALIDACION CRITICIDAD
# ======================================================


def validar_criticidad(valor):


    if not valor:

        return



    permitidos = [

        "CRITICA",

        "ALTA",

        "MEDIA",

        "BAJA",

    ]



    if valor not in permitidos:


        raise ValidationError(

            "Criticidad inválida."

        )





# ======================================================
# VALIDACION ESTADO INTERVENCION
# ======================================================


def validar_estado(valor):


    if not valor:

        return



    permitidos = [

        "PENDIENTE",

        "EN_EJECUCION",

        "PAUSADA",

        "FINALIZADA",

        "CANCELADA",

    ]



    if valor not in permitidos:


        raise ValidationError(

            "Estado de intervención inválido."

        )