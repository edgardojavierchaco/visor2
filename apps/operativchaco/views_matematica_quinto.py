from django.http import JsonResponse
from django.shortcuts import render, redirect
from .forms import ExamenMatematicaQuintoGradoForm
from .models import AlumnosPrimariaQuinto, ExamenMatematicaQuintoGrado
from django.contrib.auth.decorators import login_required
from apps.establecimientos.models import PadronOfertas
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect
from django.views.generic import UpdateView, DeleteView


@login_required
def buscar_alumno_por_dni_matematica_quinto(request):
    dni = request.GET.get('dni')
    try:
        alumno = AlumnosPrimariaQuinto.objects.get(dni=dni)
        data = {
            'encontrado': True,
            'apellidos': alumno.apellidos,
            'nombres': alumno.nombres,
            'cueanexo': alumno.cueanexo,
            'anio': alumno.grado,
            'division': alumno.division,
            'region': alumno.region
        }
    except AlumnosPrimariaQuinto.DoesNotExist:
        data = {'encontrado': False}
    return JsonResponse(data)


@login_required
def cargar_examen_matematica_quinto(request):
    region_data = PadronOfertas.objects.filter(cueanexo=request.user.username).values('region_loc').first()
    region = region_data['region_loc'] if region_data else None
    print('region:', region)
    
    if request.method == 'POST':
        form = ExamenMatematicaQuintoGradoForm(request.POST, user=request.user, region=region)
        if form.is_valid():
            examen = form.save(commit=False)
            examen.cueanexo = request.user.username
            examen.region = region
            
            # ✅ Verificamos si el alumno ya existe
            dni = form.cleaned_data.get('dni')
            if not AlumnosPrimariaQuinto.objects.filter(dni=dni).exists():
                AlumnosPrimariaQuinto.objects.create(
                    dni=dni,
                    apellidos=form.cleaned_data.get('apellidos'),
                    nombres=form.cleaned_data.get('nombres'),
                    cueanexo=request.user.username,
                    region=region,
                    grado=form.cleaned_data.get('grado'),
                    division=form.cleaned_data.get('division'),
                )
                
            form.save()
            return redirect('operativ:examen_matematica_quinto_listado')  
    else:
        form = ExamenMatematicaQuintoGradoForm(user=request.user, region=region)

    return render(request, 'operativchaco/matematica/quinto/examen_quinto_form.html', {'form': form})


class EditarEvaluacionMatematicaQuintoView(LoginRequiredMixin, UpdateView):
    model = ExamenMatematicaQuintoGrado
    form_class = ExamenMatematicaQuintoGradoForm
    template_name = 'operativchaco/matematica/quinto/examen_quinto_form.html'
    success_url = reverse_lazy('operativ:examen_matematica_quinto_listado')  

    def get_queryset(self):
        """
        Opcional: restringe la edición según el cueanexo del usuario logueado.
        """
        qs = super().get_queryset()
        if self.request.user.is_authenticated:
            return qs.filter(cueanexo=self.request.user.username)
        return qs


class EliminarEvaluacionMatematicaQuintoView(LoginRequiredMixin, DeleteView):
    model = ExamenMatematicaQuintoGrado
    template_name = 'operativchaco/matematica/quinto/examen_quinto_confirm_delete.html'
    success_url = reverse_lazy('operativ:examen_matematica_quinto_listado')

    def get_queryset(self):
        """
        Restringe la eliminación según el cueanexo del usuario logueado.
        """
        qs = super().get_queryset()
        if self.request.user.is_authenticated:
            return qs.filter(cueanexo=self.request.user.username)
        return qs.none()