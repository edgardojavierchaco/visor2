from django.shortcuts import render
from .models import ArchMapas

def obtener_nombre_mapa(url):
    return url.split('/')[-1] if url else 'Archivo no disponible'

def ver_mapas(request):
    mapas = ArchMapas.objects.all()
    for mapa in mapas:
        try:
            mapa.nombre_archivo = obtener_nombre_mapa(mapa.archivo.url)
        except ValueError:
            mapa.nombre_archivo = 'Archivo no disponible'
    print(mapas)
    return render(request, 'mapoteca/ver_mapas.html', {'mapas':mapas})