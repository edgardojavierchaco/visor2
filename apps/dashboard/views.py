from django.shortcuts import render

def dash(request):
    if request.user.is_authenticated:
        nivel_acceso = request.user.nivelacceso
    else:
        nivel_acceso = None  # O cualquier valor por defecto que desees
    return render(request, 'dashboard/body.html', {'nivelAcceso': nivel_acceso})

def portada(request):
    if request.user.is_authenticated:
        nivel_acceso = request.user.nivelacceso
        print(nivel_acceso)
    else:
        nivel_acceso = None  # O cualquier valor por defecto que desees
    return render(request, 'dashboard/portada.html', {'nivelAcceso': nivel_acceso})
