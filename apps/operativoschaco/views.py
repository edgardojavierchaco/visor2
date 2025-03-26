from django.http import JsonResponse
from .models import Alumno
from django.shortcuts import render, redirect
from .forms import RespuestaForm
from django.contrib.auth.decorators import login_required

@login_required
def respuesta_create(request):
    if request.method == 'POST':
        form = RespuestaForm(request.POST)
        if form.is_valid():
            # Guardar el formulario en la base de datos si es válido
            form.save()
            # Redirigir a otra página o mostrar un mensaje de éxito
            return redirect('respuesta_success')  # Cambia a la URL que quieras
    else:
        form = RespuestaForm()

    # Pasar el formulario al contexto del template
    return render(request, 'operativoschaco/lengua.html', {'form': form})

def alumno_autocomplete(request):
    if 'term' in request.GET:
        term = request.GET['term']
        # Obtener el username del usuario logueado
        username = request.user.username
        # Filtrar los alumnos que coinciden con el cueanexo del usuario logueado y el DNI
        alumnos = Alumno.objects.filter(cueanexo=username, dni__icontains=term)[:10]
        results = []
        for alumno in alumnos:
            alumno_dict = {
                'id': alumno.dni,
                'label': f"{alumno.dni} - {alumno.apellido}, {alumno.nombre}",
                'value': alumno.dni,
                'apellido': alumno.apellido,
                'nombre': alumno.nombre
            }
            results.append(alumno_dict)
        return JsonResponse(results, safe=False)
    return JsonResponse([], safe=False)

