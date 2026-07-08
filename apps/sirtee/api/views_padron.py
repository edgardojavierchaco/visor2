from django.http import JsonResponse
from django.views.decorators.http import require_GET

from apps.sirtee.data.padron import PadronEscuelas



# --------------------------------------
# BUSCADOR DE ESCUELAS
# --------------------------------------

@require_GET
def buscar_escuelas(request):

    texto = request.GET.get(
        "q",
        ""
    )

    escuelas = PadronEscuelas.search(
        texto
    )


    return JsonResponse(
        escuelas,
        safe=False
    )



# --------------------------------------
# DETALLE ESCUELA
# --------------------------------------

@require_GET
def detalle_escuela(request, cueanexo):

    escuela = PadronEscuelas.get(
        cueanexo
    )


    if escuela is None:

        return JsonResponse(
            {
                "error": "Escuela no encontrada"
            },
            status=404
        )


    return JsonResponse(
        escuela
    )