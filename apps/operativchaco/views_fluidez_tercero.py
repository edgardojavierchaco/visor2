from django.http import JsonResponse
from django.shortcuts import render, redirect
from .forms import ExamenFluidezTerceroForm
from .models import AlumnosPrimariaFluidez, ExamenFluidezTercero
from django.contrib.auth.decorators import login_required
from apps.establecimientos.models import PadronOfertas

@login_required
def buscar_alumno_por_dni_fluidezt(request):
    dni = request.GET.get('dni')
    try:
        alumno = AlumnosPrimariaFluidez.objects.get(dni=dni)
        data = {
            'encontrado': True,
            'apellidos': alumno.apellidos,
            'nombres': alumno.nombres,
            'cueanexo': alumno.cueanexo,
            'anio': alumno.grado,
            'division': alumno.division,
            'region': alumno.region
        }
    except AlumnosPrimariaFluidez.DoesNotExist:
        data = {'encontrado': False}
    return JsonResponse(data)


@login_required
def cargar_examen_fluidez_tercero(request):
    region_data = PadronOfertas.objects.filter(cueanexo=request.user.username).values('region_loc').first()
    region = region_data['region_loc'] if region_data else None
    print('region:', region)
    
    if request.method == 'POST':
        form = ExamenFluidezTerceroForm(request.POST, user=request.user, region=region)
        if form.is_valid():
            examen = form.save(commit=False)
            examen.cueanexo = request.user.username
            examen.region = region
            
            # ✅ Verificamos si el alumno ya existe
            dni = form.cleaned_data.get('dni')
            if not AlumnosPrimariaFluidez.objects.filter(dni=dni).exists():
                AlumnosPrimariaFluidez.objects.create(
                    dni=dni,
                    apellidos=form.cleaned_data.get('apellidos'),
                    nombres=form.cleaned_data.get('nombres'),
                    cueanexo=request.user.username,
                    region=region,
                    grado=form.cleaned_data.get('grado'),
                    division=form.cleaned_data.get('division'),
                )
                
            form.save()
            return redirect('operativ:examen_tercero_listado')  
    else:
        form = ExamenFluidezTerceroForm(user=request.user, region=region)

    return render(request, 'operativchaco/fluidez/tercero/examen_tercero_form.html', {'form': form})
