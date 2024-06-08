from django.shortcuts import render
from .models import RegistroAcceso

def mostrar_registros(request):
    registros = RegistroAcceso.objects.all()
    print(registros)
    return render(request, 'regacceso/mostrar_accesos.html', {'registros': registros})
