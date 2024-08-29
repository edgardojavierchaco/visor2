from django.urls import reverse_lazy
from django.views.generic.edit import CreateView
from .models import Datos_Personal_Cenpe, Academica_Cenpe
from .forms import DatosPersonalCenpeForm, DatosAcademicosCenpeForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from .models import localidad_tipo, provincia_tipo


class DatosPersonalCenpeCreateView(LoginRequiredMixin, CreateView):
    model = Datos_Personal_Cenpe
    form_class = DatosPersonalCenpeForm
    template_name = 'cenpe/crear_datos_personales.html'
    success_url = reverse_lazy('home')
    
    def get_initial(self):
        initial = super().get_initial()
        initial['usuario'] = self.request.user.username  # Establecer el username del usuario logueado
        return initial

    def form_valid(self, form):
        form.instance.usuario = self.request.user.username
        return super().form_valid(form)

def cargar_localidades(request):
    # Obtener el id de la provincia seleccionada desde la solicitud AJAX
    provincia_id = request.GET.get('provincia_id')
    # Obtener las localidades que corresponden a la provincia seleccionada
    localidades = localidad_tipo.objects.filter(c_provincia=provincia_id).order_by('descripcion_loc')
    # Preparar la lista de localidades como JSON
    localidades_json = [{"id": loc.c_localidad, "descripcion": loc.descripcion_loc} for loc in localidades]
    # Devolver la lista en formato JSON
    print(localidades_json)  # Depuración
    return JsonResponse(localidades_json, safe=False)


class DatosAcademicosCenpeCreateView(LoginRequiredMixin, CreateView):
    model = Academica_Cenpe
    form_class = DatosAcademicosCenpeForm
    template_name = 'cenpe/crear_datos_academicos.html'
    success_url = reverse_lazy('home')
    
    def get_initial(self):
        initial = super().get_initial()
        initial['usuario'] = self.request.user.username  # Establecer el username del usuario logueado
        return initial

    def form_valid(self, form):
        form.instance.usuario = self.request.user.username
        return super().form_valid(form)
