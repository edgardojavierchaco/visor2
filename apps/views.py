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
            'titulo': 'Carga de Relevamiento Anual 2025',
            'url':'https://youtu.be/ZxVp6hDHybY?si=J2iZSQ7Dq3cYCAy4',
        },
        {
            'titulo': 'SiNIDE - SGE',
            'url':'https://youtu.be/x60jrnhJFNQ?si=QXcqEwLl6WXs2nWu',
        },
        {
            'titulo': 'SGE - Primeros Pasos',
            'url':'https://youtu.be/11lXVxLXu2Q?si=-5bSutfjDGXeBETZ',
        },
        {
            'titulo': 'ReNPE - Primeros Pasos',
            'url':'https://www.canva.com/design/DAGxLefxMWg/xsHOarBHXMmxdGe3bkjwSg/view?utm_content=DAGxLefxMWg&utm_campaign=designshare&utm_medium=link2&utm_source=uniquelinks&utlId=h3264040a97#20',
        },
        
    ]
    
    contexto={'videos':videos}
    return render(request, 'videoteca/videoteca.html',contexto)