from collections import OrderedDict

from django.http import JsonResponse
from django.views.decorators.http import require_GET

from apps.sirtee.data.padron import PadronEscuelas


# ==========================================================
# NORMALIZADOR
# ==========================================================

def normalizar_lista(valor):

    """
    Convierte cualquier valor en lista.

    "123"      -> ["123"]
    None       -> []
    ["1","2"]  -> ["1","2"]
    """

    if valor is None:
        return []

    if isinstance(valor, list):
        return valor

    return [valor]


# ==========================================================
# BUSCADOR
# ==========================================================

@require_GET
def buscar_escuelas(request):

    texto = request.GET.get(
        "q",
        ""
    ).strip()

    if len(texto) < 3:

        return JsonResponse(
            [],
            safe=False
        )

    resultados = PadronEscuelas.search(texto)

    escuelas = OrderedDict()

    for fila in resultados:

        cue = str(
            fila["cueanexo"]
        )

        if cue not in escuelas:

            escuelas[cue] = {

                "cueanexo": fila["cueanexo"],

                "nom_est": fila.get(
                    "nom_est",
                    ""
                ),

                "cui": [],

                "oferta": [],

            }

        # -------------------------
        # CUI
        # -------------------------

        for cui in normalizar_lista(
            fila.get("cui")
        ):

            if cui and cui not in escuelas[cue]["cui"]:

                escuelas[cue]["cui"].append(
                    cui
                )

        # -------------------------
        # OFERTAS
        # -------------------------

        for oferta in normalizar_lista(
            fila.get("oferta")
        ):

            if (
                oferta
                and
                oferta not in escuelas[cue]["oferta"]
            ):

                escuelas[cue]["oferta"].append(
                    oferta
                )

    return JsonResponse(

        list(
            escuelas.values()
        ),

        safe=False

    )


# ==========================================================
# DETALLE
# ==========================================================

@require_GET
def detalle_escuela(request, cueanexo):

    registros = PadronEscuelas.search(
        cueanexo
    )

    registros = [

        r
        for r in registros

        if str(
            r["cueanexo"]
        ) == str(
            cueanexo
        )

    ]

    if not registros:

        return JsonResponse(

            {
                "error": "Escuela no encontrada"
            },

            status=404

        )

    escuela = {

        "cueanexo": cueanexo,

        "nom_est": registros[0].get(
            "nom_est",
            ""
        ),

        "cui": [],

        "oferta": [],

    }

    for fila in registros:

        for cui in normalizar_lista(
            fila.get("cui")
        ):

            if cui and cui not in escuela["cui"]:

                escuela["cui"].append(
                    cui
                )

        for oferta in normalizar_lista(
            fila.get("oferta")
        ):

            if (
                oferta
                and
                oferta not in escuela["oferta"]
            ):

                escuela["oferta"].append(
                    oferta
                )

    return JsonResponse(
        escuela
    )