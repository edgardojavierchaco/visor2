from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

# Vista para mostrar infografía matrícula, cargos y horas
def infografiaview(request):
    """
    Muestra la infografía de matrícula, cargos y horas.

    Esta vista renderiza la plantilla 'reportes/infografia.html',
    que contiene información sobre la matrícula, los cargos y las horas.

    Args:
        request: La solicitud HTTP.

    Returns:
        HttpResponse: Renderiza la plantilla infografía con el contexto adecuado.
    """
    
    return render(request, 'reportes/infografia.html')


def infografiaview2(request):
    """
    Muestra una segunda infografía.

    Esta vista renderiza la plantilla 'reportes/infografia2.html',
    que contiene información adicional en formato de infografía.

    Args:
        request: La solicitud HTTP.

    Returns:
        HttpResponse: Renderiza la segunda plantilla de infografía.
    """
    
    return render(request, 'reportes/infografia2.html')

def equipoview(request):
    """
    Muestra la información del equipo.

    Esta vista renderiza la plantilla 'equipo.html', que
    contiene información sobre el equipo.

    Args:
        request: La solicitud HTTP.

    Returns:
        HttpResponse: Renderiza la plantilla del equipo.
    """
    
    return render(request, 'equipo.html')