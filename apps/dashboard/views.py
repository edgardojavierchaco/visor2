from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.contrib.auth.models import Group

def dash(request):
    """
    Renderiza la vista del dashboard para el usuario autenticado.

    Si el usuario está autenticado, se obtiene su nivel de acceso. 
    De lo contrario, se establece un valor por defecto (None).

    Args:
        request: El objeto HttpRequest que contiene la información sobre la 
                 solicitud realizada por el usuario.

    Returns:
        HttpResponse: Renderiza el template 'dashboard/body.html' con el 
                       contexto que incluye el nivel de acceso del usuario.
    """
    if request.user.is_authenticated:
        nivel_acceso = request.user.nivelacceso
    else:
        nivel_acceso = None  # O cualquier valor por defecto que desees
    return render(request, 'dashboard/body.html', {'nivelAcceso': nivel_acceso})
    

def portada(request):
    """
    Redirige a los usuarios autenticados a la vista correspondiente 
    según su grupo, o renderiza la portada si no pertenecen a ningún grupo.

    Si el usuario está autenticado y pertenece a un grupo específico 
    ('Director', 'Evaluacion', 'Aplicador'), se redirige a la URL 
    correspondiente. Si no pertenece a ninguno de esos grupos, se 
    renderiza la portada.

    Args:
        request: El objeto HttpRequest que contiene la información sobre la 
                 solicitud realizada por el usuario.

    Returns:
        HttpResponse: Redirige a la URL correspondiente según el grupo del 
                       usuario o renderiza el template 'dashboard/portada.html'.
    """
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

@login_required
def directores(request):    
    """
    Renderiza la vista institucional para directores.

    Esta función renderiza el template 'directores/institucional.html',
    donde se presenta la información relevante para los directores.

    Args:
        request: El objeto HttpRequest que contiene la información sobre la 
                 solicitud realizada por el usuario.

    Returns:
        HttpResponse: Renderiza el template 'directores/institucional.html'.
    """
    return render(request, 'directores/institucional.html')

@login_required
def evaluacion(request):
    """
    Renderiza la vista de evaluación.

    Esta función renderiza el template 'dashboard/portadaevaluacion.html',
    donde se presenta la información relevante para la evaluación.

    Args:
        request: El objeto HttpRequest que contiene la información sobre la 
                 solicitud realizada por el usuario.

    Returns:
        HttpResponse: Renderiza el template 'dashboard/portadaevaluacion.html'.
    """
    return render(request, 'dashboard/portadaevaluacion.html')