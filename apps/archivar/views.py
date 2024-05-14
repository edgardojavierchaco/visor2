from django.shortcuts import render, redirect, get_object_or_404
from .forms import ArchRegisterForm
from .models import ArchRegister

from django.contrib import messages

def cargar_archivo(request):
    if request.method == 'POST':
        form = ArchRegisterForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                archivo = form.save(commit=False)
                archivo.ruta = archivo.archivo.url
                archivo.save()
                # Obtenemos la ruta del archivo
                ruta_archivo = archivo.ruta
                return render(request, 'archivos/cargar_archivo.html', {'form': form, 'ruta_archivo': ruta_archivo})
            except Exception as e:
                messages.error(request, f'Ocurrió un error al guardar el archivo: {e}')
                return render(request, 'archivos/cargar_archivo.html', {'form': form, 'error_alert': True})
    else:
        form = ArchRegisterForm()
    return render(request, 'archivos/cargar_archivo.html', {'form': form})



def archivos_lista(request):
    archivos = ArchRegister.objects.all()
    return render(request, 'archivos/archivos_lista.html', {'archivos': archivos})

def buscar_pdf(request):
    if request.method == 'POST':
        cueanexo = request.POST.get('cueanexo')
        asunto = request.POST.get('asunto')
        archivo = ArchRegister.objects.filter(cueanexo=cueanexo, asunto__asunto=asunto).first()
        if archivo:
            return render(request, 'archivos/ver_pdf.html', {'archivo': archivo})
        else:
            mensaje = "No se encontró ningún PDF con el cueanexo y asunto especificados."
            return render(request, 'archivos/buscar_pdf.html', {'mensaje': mensaje})
    else:
        return render(request, 'archivos/buscar_pdf.html')