from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.db import connection
from apps.supervisores.forms import SupervisorForm
#from .mixins import ValidatePermissionRequiredMixin
from apps.supervisores.models import Supervisor
from apps.superescuela.models import Asignacion


class SupervisoresListViewFunc(LoginRequiredMixin, ListView):
    model = Supervisor
    template_name = 'superv/supervisor/list_func.html'
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
        Obtiene el queryset de PersonalDocCentral filtrado por la regional del usuario logueado.

        Returns:
            QuerySet: Lista de PersonalDocCentral filtrados por la región correspondiente.
        """
        regional_usuario = self.get_regional_usuario()
        if regional_usuario:
            # Filtramos PersonalDocCentral por la región correspondiente
            return Supervisor.objects.all()
        return Supervisor.objects.none()

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST['action']
            if action == 'searchdata':
                data = []
                for i in self.get_queryset():
                    data.append(i.toJSON())
            else:
                data['error'] = 'Ha ocurrido un error'
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data, safe=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Listado de Supervisores'
        context['create_url'] = reverse_lazy('superescuela:super_create')
        context['list_url'] = reverse_lazy('funcionario:super_list')
        context['update_url'] = reverse_lazy('supervi:super_update', args=[0]) 
        context['entity'] = 'Supervisor'
        return context


class AsignacionListViewFunc(LoginRequiredMixin, ListView):
    model = Asignacion
    template_name = 'superv/asignacion/list_func.html'

    def get_regional_usuario(self):
        """
        Obtiene el regional del usuario logueado consultando directamente la tabla cenpe.cueregional.
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
        Filtra las asignaciones según la región del supervisor y del usuario logueado.
        """
        regional_usuario = self.get_regional_usuario()
        if regional_usuario:
            # Filtrar asignaciones por la región del supervisor
            return Asignacion.objects.filter(supervisor__region=regional_usuario)
        return Asignacion.objects.none()
    
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST['action']  
            regional_usuario = self.get_regional_usuario()          
            if action == 'searchdata':
                data = [i.toJSON() for i in Asignacion.objects.filter(supervisor__region=regional_usuario)]
            elif action == 'search_details_asign':
                data = []
                for i in DetalleAsignacion.objects.filter(asignacion_id=request.POST['id'],
                    asignacion__supervisor__region=regional_usuario):
                    data.append(i.toJSON())
            else:
                data['error'] = 'Ha ocurrido un error'
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data, safe=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Listado de Supervisores con Asignaciones'
        context['create_url'] = reverse_lazy('superescuela:asign_create')
        context['list_url'] = reverse_lazy('superescuela:asign_list')
        context['entity'] = 'Listado'
        return context
