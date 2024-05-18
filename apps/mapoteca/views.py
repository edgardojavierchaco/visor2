from django.shortcuts import render
from .models import ArchMapas

def ver_mapas(request):
    mapas=ArchMapas.objects.all()
    return render(request, 'mapoteca/ver_mapas.html', {'mapas':mapas})
