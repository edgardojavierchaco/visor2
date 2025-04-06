from django.http import JsonResponse
from django.shortcuts import render, redirect
from .forms import ExamenMatematicaAlumnoForm
from .models import AlumnosSecundariaDiagnostico
from django.contrib.auth.decorators import login_required
from apps.establecimientos.models import PadronOfertas

@login_required
def buscar_alumnom_por_dni(request):
    dni = request.GET.get('dni')
    try:
        alumno = AlumnosSecundariaDiagnostico.objects.get(dni=dni)
        data = {
            'encontrado': True,
            'apellidos': alumno.apellidos,
            'nombres': alumno.nombres,
            'cueanexo': alumno.cueanexo,
            'anio': alumno.anio,
            'division': alumno.division,
            'region': alumno.region
        }
    except AlumnosSecundariaDiagnostico.DoesNotExist:
        data = {'encontrado': False}
    return JsonResponse(data)


@login_required
def cargar_examen_matematica(request):
    region_data = PadronOfertas.objects.filter(cueanexo=request.user.username).values('region_loc').first()
    region = region_data['region_loc'] if region_data else None
    print('region:', region)
    
    if request.method == 'POST':
        form = ExamenMatematicaAlumnoForm(request.POST, user=request.user, region=region)
        if form.is_valid():
            examen = form.save(commit=False)
            examen.cueanexo = request.user.username
            examen.region = region
            
            # ✅ Verificamos si el alumno ya existe
            dni = form.cleaned_data.get('dni')
            if not AlumnosSecundariaDiagnostico.objects.filter(dni=dni).exists():
                AlumnosSecundariaDiagnostico.objects.create(
                    dni=dni,
                    apellidos=form.cleaned_data.get('apellidos'),
                    nombres=form.cleaned_data.get('nombres'),
                    cueanexo=request.user.username,
                    region=region,
                    anio=form.cleaned_data.get('anio'),
                    division=form.cleaned_data.get('division'),
                )
                
            form.save()
            return redirect('operativ:examen_matematica_listado')  
    else:
        form = ExamenMatematicaAlumnoForm(user=request.user, region=region)

    return render(request, 'operativchaco/matematica/examen_matematica_form.html', {'form': form})
