from django.shortcuts import render
from .models import ArchMapas

def obtener_nombre_mapa(url):
    """
    Extrae el nombre del archivo del mapa a partir de su URL.

    Args:
        url (str): La URL del archivo del mapa.

    Returns:
        str: El nombre del archivo extraído de la URL o 'Archivo no disponible' si la URL es vacía.
    """
    
    return url.split('/')[-1] if url else 'Archivo no disponible'

def ver_mapas(request):
    """
    Vista para mostrar todos los mapas almacenados en la base de datos.

    Obtiene todos los objetos de ArchMapas, extrae el nombre de cada archivo y los pasa a la plantilla para su visualización.

    Args:
        request: El objeto HttpRequest que contiene información sobre la solicitud HTTP.

    Returns:
        HttpResponse: La respuesta que renderiza la plantilla 'mapoteca/ver_mapas.html'
        con el contexto que incluye la lista de mapas.
    """
    
    mapas = ArchMapas.objects.all()
    for mapa in mapas:
        try:
            mapa.nombre_archivo = obtener_nombre_mapa(mapa.archivo.url)
        except ValueError:
            mapa.nombre_archivo = 'Archivo no disponible'
    print(mapas)
    return render(request, 'mapoteca/ver_mapas.html', {'mapas':mapas})