from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control
from django.utils.decorators import method_decorator
from django.views.generic import CreateView, ListView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from .models import RegAplicador, RegDocporSeccion, RegEvaluacionFluidezLectora
from .forms import RegDocporSeccionEdicionForm, RegDocporSeccionForm, RegEvaluacionFluidezLectoraForm, FiltroEvaluacionForm, RegAlumnosFluidezLectoraForm, RegEvaluacionFluidezLectoraDirectoresForm
from .forms import RegAlumnosFluidezLectoraDirectorForm
from .forms import RegAplicadorporSeccionEdicionForm
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import urlencode
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import connection
from django.db.models import Q

# listado de aplicadores para directores
@method_decorator([login_required, cache_control(no_cache=True, must_revalidate=True)], name='dispatch')
class ListadoAplicadoresDirView(LoginRequiredMixin,ListView):
    """
    Vista para listar los aplicadores registrados.

    Atributos:
        model: El modelo Reg.
        template_name: La plantilla utilizada para mostrar el listado.
        context_object_name: El nombre del contexto para los docentes.
    """
    
    model=RegAplicador
    template_name='oplectura/listadoaplicadir.html'
    context_object_name='aplicadoresporseccion'  
    
        
    def get_queryset(self):
        """
        Obtiene la consulta de los aplicadores filtrada por el regional del usuario logueado.
        
        Returns:
            QuerySet: Lista de RegAplicador filtrados por la región correspondiente.
        """
        print("Ejecutando get_queryset")
        director_usuario = self.request.user
        print("Usuario logueado:", director_usuario)
        
        queryset= RegAplicador.objects.filter(cueanexo=director_usuario.username)
        print("QuerySet filtrado:", queryset)
        print("Registros filtrados para el usuario:", director_usuario)         
        
        return queryset
    
    def get_context_data(self, **kwargs):
        """
        Agrega contexto adicional a la plantilla.

        Args:
            **kwargs: Contexto adicional.

        Returns:
            dict: Contexto actualizado con el título.
        """
        print("Ejecutando get_context_data")
        context=super().get_context_data(**kwargs)
        context['title']='Listado de Aplicadores'
        return context

#edición de aplicadores para directores
@method_decorator([login_required, cache_control(no_cache=True, must_revalidate=True)], name='dispatch')
class EditarAplicadorDirView(UpdateView):
    """
    Vista para editar un registro de aplicadores

    Atributos:
        model: El modelo RegAplicador.
        form_class: El formulario RegAplicadorporSeccionEdicionForm.
        template_name: La plantilla utilizada para editar.
        success_url: La URL a la que se redirige tras el éxito.
    """
    
    model = RegAplicador
    form_class = RegAplicadorporSeccionEdicionForm
    template_name = 'oplectura/editaraplicdir.html'
    success_url = reverse_lazy('oplectura:listaplicdir')

    def get_object(self):
        """
        Obtiene el objeto a editar.

        Returns:
            RegDocporSeccion: El objeto correspondiente al ID proporcionado.
        """
        
        user_id = self.request.GET.get('id')
        return get_object_or_404(RegAplicador, id=user_id)

    def get_context_data(self, **kwargs):
        """
        Agrega contexto adicional a la plantilla.

        Args:
            **kwargs: Contexto adicional.

        Returns:
            dict: Contexto actualizado con el título.
        """
        
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Validación'
        return context

    def form_valid(self, form):
        """
        Procesa el formulario cuando es válido.

        Args:
            form: El formulario válido.

        Returns:
            HttpResponse: Redirige a la URL de éxito tras la actualización.
        """
        
        return super().form_valid(form)