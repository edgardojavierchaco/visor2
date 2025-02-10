from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import cache_control
from django.db import connection
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from apps.uegp.forms import PersonalDocUegpForm, PersonalNoDocUegpForm
#from .mixins import ValidatePermissionRequiredMixin
from apps.uegp.models import PersonalDocUegp, PersonalNoDocUegp
from django.shortcuts import get_object_or_404
from apps.uegp.models import CargosCeicUegp
from apps.usuarios.models import UsuariosVisualizador

class UEGPListViewPersDocFuncionario(LoginRequiredMixin, ListView):
    """
    Vista para listar PersonalDocUEGP filtrados por la regional del usuario logueado.

    Atributos:
        model: El modelo PersonalDocUEGP.
        template_name: La plantilla utilizada para mostrar el listado.
        context_object_name: El nombre del contexto para el listado de PersonalDocUEGP.
    """
    model = PersonalDocUegp
    template_name = 'uegp/pers_doc_uegp/list_dirgral.html'
    #permission_required = 'apps.view_supervisor'
    
    def get_regional_usuario(self):
        """
        Obtiene el regional del usuario logueado consultando directamente la tabla cenpe.cueregional.

        Returns:
            str: El regional del usuario logueado o None si no se encuentra.
        """
        user = self.request.user
        query = """
            SELECT regional 
            FROM cenpe.cueregional 
            WHERE cueanexo = %s
            LIMIT 1
        """
        with connection.cursor() as cursor:
            cursor.execute(query, [user.username])
            row = cursor.fetchone()
        
        return row[0] if row else None

    def get_queryset(self):
        """
        Obtiene el queryset de PersonalDocUegp filtrado por el cueanexo del usuario logueado.

        Returns:
            QuerySet: Lista de PersonalDocUegp filtrada por el cueanexo del usuario autenticado.
        """
        usuario = self.request.user.username        
        return PersonalDocUegp.objects.all()       

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """
        Maneja solicitudes POST para buscar datos de PersonalDocUegp.
        """
        data = {}
        try:
            action = request.POST['action']
            if action == 'searchdata':
                data = []
                for i in self.get_queryset():
                    print(f"Procesando PersonalDocUegp: {i}")
                    data.append(i.toJSON())               
                    
            else:
                data['error'] = 'Ha ocurrido un error'
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data, safe=False)

    def get_context_data(self, **kwargs):
        """
        Agrega contexto adicional a la plantilla.

        Args:
            **kwargs: Contexto adicional.

        Returns:
            dict: Contexto actualizado con el título y otras configuraciones.
        """
        context = super().get_context_data(**kwargs)
        context['title'] = 'Listado de Personal Docente'
        #context['create_url'] = reverse_lazy('privada:uegp_create')
        context['list_url'] = reverse_lazy('privada:uegp_list_docdirgral')         
        context['entity'] = 'Personal Docente'
        return context


class UEGPListViewPersNoDocFuncionario(LoginRequiredMixin, ListView):
    """
    Vista para listar PersonalDocUEGP filtrados por la regional del usuario logueado.

    Atributos:
        model: El modelo PersonalDocUEGP.
        template_name: La plantilla utilizada para mostrar el listado.
        context_object_name: El nombre del contexto para el listado de PersonalDocUEGP.
    """
    model = PersonalNoDocUegp
    template_name = 'uegp/pers_no_doc_uegp/list_admin_dirgral.html'
    #permission_required = 'apps.view_supervisor'
    
    def get_regional_usuario(self):
        """
        Obtiene el regional del usuario logueado consultando directamente la tabla cenpe.cueregional.

        Returns:
            str: El regional del usuario logueado o None si no se encuentra.
        """
        user = self.request.user
        query = """
            SELECT regional 
            FROM cenpe.cueregional 
            WHERE cueanexo = %s
            LIMIT 1
        """
        with connection.cursor() as cursor:
            cursor.execute(query, [user.username])
            row = cursor.fetchone()
        
        return row[0] if row else None

    def get_queryset(self):
        """
        Obtiene el queryset de PersonalDocUegp filtrado por el cueanexo del usuario logueado.

        Returns:
            QuerySet: Lista de PersonalDocUegp filtrada por el cueanexo del usuario autenticado.
        """
        usuario = self.request.user.username        
        return PersonalNoDocUegp.objects.all()       

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """
        Maneja solicitudes POST para buscar datos de PersonalDocUegp.
        """
        data = {}
        try:
            action = request.POST['action']
            if action == 'searchdata':
                data = []
                for i in self.get_queryset():
                    print(f"Procesando PersonalDocUegp: {i}")
                    data.append(i.toJSON())               
                    
            else:
                data['error'] = 'Ha ocurrido un error'
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data, safe=False)

    def get_context_data(self, **kwargs):
        """
        Agrega contexto adicional a la plantilla.

        Args:
            **kwargs: Contexto adicional.

        Returns:
            dict: Contexto actualizado con el título y otras configuraciones.
        """
        context = super().get_context_data(**kwargs)
        context['title'] = 'Listado de Personal No Docente'
        #context['create_url'] = reverse_lazy('privada:uegp_create')
        context['list_url'] = reverse_lazy('privada:uegp_list_ndocdirgral')         
        context['entity'] = 'Personal No Docente'
        return context