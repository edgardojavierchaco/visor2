from django.urls import reverse_lazy
from django.views import View
from django.views.generic.edit import FormView
from django.http import JsonResponse
from django.shortcuts import redirect, render
from .models import DatosEscuela, Localidad, VCapaUnicaOfertasCuiCuof, Departamento
from .forms import DatosEscuelaForm
from django.views.generic import CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.usuarios.models import UsuariosVisualizador

class DatosEscuelaCreateView(LoginRequiredMixin, CreateView):
    model=DatosEscuela
    form_class = DatosEscuelaForm
    template_name = 'infra/datosescuela/datos_escuela_form.html'        
    success_url = reverse_lazy('infraestructura:dominio_escuela')  # Redirigir a una página de éxito

    def form_valid(self, form):
        form.instance.cueanexo = self.request.user.username
        return super().form_valid(form)

    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST['action']
            if action == 'add':
                form = self.get_form()
                if form.is_valid():
                    instance = form.save()
                    data = {'message': 'Guardado correctamente', 'instance': instance.toJSON()} 
                else:
                    data['error'] = 'Corrige los errores antes de continuar.'
                    data['form_errors'] = form.errors
            else:
                data['error'] = 'Acción no válida.'
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data)

    def get_context_data(self, **kwargs):
        # Llamamos al contexto sin necesidad de 'instance'
        context = super().get_context_data(**kwargs)
        context['title'] = 'Actualización Datos Escuela'
        context['entity'] = 'Instituciones'        
        context['action'] = 'add'
        context['list_url'] = self.success_url
        
        # Obtener el registro con el usuario logueado
        registro_cue = VCapaUnicaOfertasCuiCuof.objects.filter(cueanexo=self.request.user.username).first()
        
        if registro_cue:
            context['cueanexo'] = registro_cue.cueanexo
            context['nom_est'] = registro_cue.nom_est
            context['calle'] = registro_cue.calle
            context['nro'] = registro_cue.numero
            context['localidad'] = registro_cue.localidad
            context['departamento'] = registro_cue.departamento
        else:
            context['cueanexo'] = None
            context['nom_est'] = None
            context['nro'] = None
            context['localidad'] = None
            context['departamento'] = None
        return context


class autocompletar_departamento(View):
    def get(self, request, *args, **kwargs):
        departamento_parcial = request.GET.get('departamentos', None) 
        print(f"Departamento recibido: {departamento_parcial}")
        if departamento_parcial:
            departamentos = Departamento.objects.filter(descripcion_dpto__icontains=departamento_parcial)[:5]
            print(f"Departamentos encontrados: {departamentos}")
            results = [{'label': departamento.descripcion_dpto, 'value': departamento.descripcion_dpto} for departamento in departamentos]
            
            return JsonResponse(results, safe=False)
        else:
            print("No se encontró parámetro de departamento")
            return JsonResponse([], safe=False)


class autocompletar_localidad(View):
    def get(self, request, *args, **kwargs):
        localidad_parcial = request.GET.get('localidades', None) 
        departamento = request.GET.get('departamento', None)
        print(f"Localidad recibida: {localidad_parcial}")
        if localidad_parcial and departamento:
            # Se cambia 'departamento__descripcion_dpto' por 'c_departamento__descripcion_dpto'
            localidades = Localidad.objects.filter(
                descripcion_loc__icontains=localidad_parcial,
                c_departamento__descripcion_dpto=departamento  # Corregir nombre del campo
            )[:5]
            print(f"Localidades encontradas: {localidades}")
            results = [{'label': localidad.descripcion_loc, 'value': localidad.descripcion_loc} for localidad in localidades]
            
            return JsonResponse(results, safe=False)
        else:
            print("No se encontró parámetro de localidad o departamento")
            return JsonResponse([], safe=False)

def listado(request):
    return render(request, 'infra/prueba.html')