from django.urls import reverse_lazy
from django.views import View
from django.views.generic.edit import FormView
from django.http import JsonResponse
from django.shortcuts import redirect, render
from .models import EspaciosPedagogicos, VCapaUnicaOfertasCuiCuof
from .forms import EspaciosPedagogicosForm
from django.views.generic import CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.usuarios.models import UsuariosVisualizador

class EspacioPedagogicoCreateView(LoginRequiredMixin, CreateView):
    model=EspaciosPedagogicos
    form_class = EspaciosPedagogicosForm
    template_name = 'infra/espaped/espacio_pedagogico_form.html'        
    success_url = reverse_lazy('infraestructura:sanitarios')  # Redirigir a una página de éxito

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
        context['title'] = 'Carga datos Espacios Pedagógicos'
        context['entity'] = 'Espacio Pedagógico'        
        context['action'] = 'add'
        context['list_url'] = self.success_url
        context['cueanexo'] = self.request.user.username
        return context
        
        