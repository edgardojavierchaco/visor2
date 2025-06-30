from django.http import JsonResponse
from django.shortcuts import render, redirect
from .forms import ExamenMatematicaQuintoGradoForm, ExamenMatematicaSegundoAnioForm
from .models import AlumnosSegundoSecundaria, ExamenMatematicaSegundoAnio
from django.contrib.auth.decorators import login_required
from apps.establecimientos.models import PadronOfertas
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect
from django.views.generic import UpdateView, DeleteView


@login_required
def buscar_alumno_por_dni_matematica_segundo_anio(request):
    dni = request.GET.get('dni')
    try:
        alumno = AlumnosSegundoSecundaria.objects.get(dni=dni)
        data = {
            'encontrado': True,
            'apellidos': alumno.apellidos,
            'nombres': alumno.nombres,
            'cueanexo': alumno.cueanexo,
            'anio': alumno.grado,
            'division': alumno.division,
            'region': alumno.region
        }
    except AlumnosSegundoSecundaria.DoesNotExist:
        data = {'encontrado': False}
    return JsonResponse(data)


@login_required
def cargar_examen_matematica_segundo_anio(request):
    region_data = PadronOfertas.objects.filter(cueanexo=request.user.username).values('region_loc').first()
    region = region_data['region_loc'] if region_data else None
    print('region:', region)
    
    if request.method == 'POST':
        form = ExamenMatematicaSegundoAnioForm(request.POST, user=request.user, region=region)
        if form.is_valid():
            examen = form.save(commit=False)
            examen.cueanexo = request.user.username
            examen.region = region
            
            # ✅ Verificamos si el alumno ya existe
            dni = form.cleaned_data.get('dni')
            if not AlumnosSegundoSecundaria.objects.filter(dni=dni).exists():
                AlumnosSegundoSecundaria.objects.create(
                    dni=dni,
                    apellidos=form.cleaned_data.get('apellidos'),
                    nombres=form.cleaned_data.get('nombres'),
                    cueanexo=request.user.username,
                    region=region,
                    grado=form.cleaned_data.get('grado'),
                    division=form.cleaned_data.get('division'),
                )
                
            form.save()
            return redirect('operativ:examen_matematica_segundo_anio_listado')  
    else:
        form = ExamenMatematicaSegundoAnioForm(user=request.user, region=region)

    return render(request, 'operativchaco/matematica/segundo/examen_segundo_form.html', {'form': form})


class EditarEvaluacionMatematicaSegundoAnioView(LoginRequiredMixin, UpdateView):
    model = ExamenMatematicaSegundoAnio
    form_class = ExamenMatematicaSegundoAnioForm
    template_name = 'operativchaco/matematica/segundo/examen_segundo_form.html'
    success_url = reverse_lazy('operativ:examen_matematica_segundo_listado')  

    def get_queryset(self):
        """
        Opcional: restringe la edición según el cueanexo del usuario logueado.
        """
        qs = super().get_queryset()
        if self.request.user.is_authenticated:
            return qs.filter(cueanexo=self.request.user.username)
        return qs


class EliminarEvaluacionMatematicaSegundoAnioView(LoginRequiredMixin, DeleteView):
    model = ExamenMatematicaSegundoAnio
    template_name = 'operativchaco/matematica/segundo/examen_segundoanio_confirm_delete.html'
    success_url = reverse_lazy('operativ:examen_matematica_segundo_anio_listado')

    def get_queryset(self):
        """
        Restringe la eliminación según el cueanexo del usuario logueado.
        """
        qs = super().get_queryset()
        if self.request.user.is_authenticated:
            return qs.filter(cueanexo=self.request.user.username)
        return qs.none()