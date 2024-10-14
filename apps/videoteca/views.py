from django.shortcuts import render

def videoteca(request):
    """
    Renderiza la página de la videoteca con una lista de videos educativos.

    Esta vista proporciona un contexto que incluye un conjunto de videos, cada uno
    con un título y una URL, que se mostrarán en la plantilla correspondiente.

    Args:
        request (HttpRequest): La solicitud HTTP enviada por el navegador.

    Returns:
        HttpResponse: La respuesta renderizada que contiene la plantilla
        'videoteca/videoteca.html' con el contexto de los videos.
    """
    
    videos=[
        {
            'titulo': 'Estadísticas Educativas',
            'url':'https://youtu.be/m5r-nDNGhnI?si=4Td51_DC7PY9Emnp',
        },
        {
            'titulo': 'Administración de Personal',
            'url':'https://youtu.be/VcDAPC2lSfU?si=uUzDn0IT7K2D7njy',
        },
        {
            'titulo': 'Asistencia',
            'url':'https://youtu.be/W7agb4AN4Cc?si=EcDPQZS4QnzWy7Wx',
        },
        {
            'titulo': 'Calificación',
            'url':'https://youtu.be/PBD-zeI8nkM?si=OluVS00C6E7KDsxY',
        },
        {
            'titulo': 'Control de Secciones',
            'url':'https://youtu.be/m8CCsNWD9F4?si=eL8Hw46wFNG-4KES',
        },        
    ]
    
    contexto={'videos':videos}
    return render(request, 'videoteca/videoteca.html',contexto)