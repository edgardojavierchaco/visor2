from django.shortcuts import render
from .models import ArchNoramtiva

def obtener_nombre_archivo(url):
    return url.split('/')[-1]

def ver_normas(request):
    norma = ArchNoramtiva.objects.all()
    for lex in norma:
        lex.nombre_archivo = obtener_nombre_archivo(lex.archivo.url)
    return render(request, 'normativa/ver_normas.html', {'norma': norma})