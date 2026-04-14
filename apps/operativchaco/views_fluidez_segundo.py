from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from .forms import ExamenFluidezSegundoForm
from .models import AlumnosPrimariaFluidez, ExamenFluidezSegundo
from django.contrib.auth.decorators import login_required
from apps.establecimientos.models import PadronOfertas
from django.views.generic import UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect

@login_required
def buscar_alumno_por_dni_fluidez(request):
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
def cargar_examen_fluidez_segundo(request):
    region_data = PadronOfertas.objects.filter(cueanexo=request.user.username).values('region_loc').first()
    region = region_data['region_loc'] if region_data else None
    print('region:', region)
    
    if request.method == 'POST':
        form = ExamenFluidezSegundoForm(request.POST, user=request.user, region=region)
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
            return redirect('operativ:examen_segundo_listado')  
    else:
        form = ExamenFluidezSegundoForm(user=request.user, region=region)

    return render(request, 'operativchaco/fluidez/segundo/examen_segundo_form.html', {'form': form})


class EditarEvaluacionSegundoView(LoginRequiredMixin, UpdateView):
    model = ExamenFluidezSegundo
    form_class = ExamenFluidezSegundoForm
    template_name = 'operativchaco/fluidez/segundo/examen_segundo_form.html'
    success_url = reverse_lazy('operativ:examen_segundo_listado')  # Cambiá esta URL por la que necesites

    def get_queryset(self):
        """
        Opcional: restringe la edición según el cueanexo del usuario logueado.
        """
        qs = super().get_queryset()
        if self.request.user.is_authenticated:
            return qs.filter(cueanexo=self.request.user.username)
        return qs