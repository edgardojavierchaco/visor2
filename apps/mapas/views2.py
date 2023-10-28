from django.shortcuts import render

def mapapuntos(request):
    return render(request, 'mapa/mapa.html')

