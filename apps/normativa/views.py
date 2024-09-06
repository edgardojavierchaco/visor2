from django.shortcuts import render
from .models import ArchNoramtiva

def obtener_nombre_archivo(url):
    return url.split('/')[-1] if url else 'Archivo no disponible'

def ver_normas(request):
    norma = ArchNoramtiva.objects.all()
    for lex in norma:
        try:
            lex.nombre_archivo = obtener_nombre_archivo(lex.archivo.url)
        except ValueError:
            lex.nombre_archivo = 'Archivo no disponible'
    print(norma)
    return render(request, 'normativa/ver_normas.html', {'norma': norma})