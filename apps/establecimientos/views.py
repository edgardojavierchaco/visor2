from django.shortcuts import render
from .models import PadronOfertas

def establecimientos(request):
    """
    Vista que filtra y muestra los establecimientos educativos activos.

    Este método obtiene los establecimientos cuyo CUE anexo termina en '00' y cuya oferta educativa
    se encuentra activa. Los resultados son pasados al template `establecimientos/establecimientos.html`
    para su renderización.

    Parámetros:
        request (HttpRequest): La solicitud HTTP enviada por el usuario.

    Retorna:
        HttpResponse: Respuesta HTTP con la plantilla renderizada que incluye los establecimientos filtrados.
    """
    # Filtrar los establecimientos según los criterios requeridos
    establecimientos = PadronOfertas.objects.filter(cueanexo__endswith='00', est_oferta='Activo')

    # Renderizar la vista con los establecimientos filtrados
    return render(request, 'establecimientos/establecimientos.html', {'establecimientos': establecimientos})
