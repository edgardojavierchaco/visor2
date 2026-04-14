from django.shortcuts import render
from .models import ArchNoramtiva

def obtener_nombre_archivo(url):
    """
    Obtiene el nombre del archivo a partir de su URL.

    Args:
        url (str): La URL del archivo.

    Returns:
        str: El nombre del archivo si la URL es válida, o 'Archivo no disponible'.
    """
    
    return url.split('/')[-1] if url else 'Archivo no disponible'

def ver_normas(request):
    """
    Vista que recupera y muestra una lista de normas en la plantilla correspondiente.

    Esta vista obtiene todas las instancias del modelo ArchNormativa, extrae el nombre del archivo
    asociado a cada norma y lo añade como un atributo adicional a cada objeto de norma. 
    Luego, renderiza la plantilla 'normativa/ver_normas.html' con la lista de normas.

    Args:
        request (HttpRequest): El objeto de solicitud HTTP.

    Returns:
        HttpResponse: La respuesta renderizada de la plantilla con las normas.
    """
    
    norma = ArchNoramtiva.objects.all()
    for lex in norma:
        try:
            lex.nombre_archivo = obtener_nombre_archivo(lex.archivo.url)
        except ValueError:
            lex.nombre_archivo = 'Archivo no disponible'
    print(norma)
    return render(request, 'normativa/ver_normas.html', {'norma': norma})