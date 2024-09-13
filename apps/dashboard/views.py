from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.contrib.auth.models import Group

def dash(request):
    if request.user.is_authenticated:
        nivel_acceso = request.user.nivelacceso
    else:
        nivel_acceso = None  # O cualquier valor por defecto que desees
    return render(request, 'dashboard/body.html', {'nivelAcceso': nivel_acceso})

""" def portada(request):
    if request.user.is_authenticated:
        nivel_acceso = request.user.nivelacceso
        print(nivel_acceso)
    else:
        nivel_acceso = None  # O cualquier valor por defecto que desees
    return render(request, 'dashboard/portada.html', {'nivelAcceso': nivel_acceso}) """
    

def portada(request):
    user=request.user
    if request.user.is_authenticated:
        if user.groups.filter(name='Director').exists():
            return redirect('directores:institucional')  
        elif user.groups.filter(name='Evaluacion').exists():
            return redirect('oplectura:portal_eval')  
        elif user.groups.filter(name='Aplicador').exists():
            return redirect('oplectura:evaluacion')  
        else:            
            return render(request, 'dashboard/portada.html')
    else:
        return render(request, 'dashboard/portada.html')

def directores(request):    
    return render(request, 'directores/institucional.html')

def evaluacion(request):
    return render(request, 'dashboard/portadaevaluacion.html')