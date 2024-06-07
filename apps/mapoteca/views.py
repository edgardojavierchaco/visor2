from django.shortcuts import render
from .models import ArchMapas

def obtener_nombre_mapa(url):
    return url.split('/')[-1]

def ver_mapas(request):
    mapas = ArchMapas.objects.all()
    for map in mapas:
        map.nombre_archivo = obtener_nombre_mapa(map.archivo.url)
    print(mapas)
    return render(request, 'mapoteca/ver_mapas.html', {'mapas':mapas})