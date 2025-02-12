import json
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from .forms import AsignacionForm
#from .mixins import ValidatePermissionRequiredMixin
from django.views.generic import CreateView, ListView, DeleteView, UpdateView
from django.db import transaction
from django.db import connection
from .models import Asignacion, DetalleAsignacion, EscuelasSupervisadas, Supervisor


class AsignacionCreateView(LoginRequiredMixin, CreateView):
    model = Asignacion
    form_class = AsignacionForm
    template_name = 'superv/asignacion/create.html'
    success_url = reverse_lazy('superescuela:asign_create')
    #permission_required = 'apps.add_asignacion'
    url_redirect = success_url

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)
    
    def get_regional_usuario(self):
        """
        Obtiene el regional del usuario logueado consultando directamente la tabla cenpe.cueregional.

        Returns:
            str: El regional del usuario logueado o None si no se encuentra.
        """
        user = self.request.user
        query = """
            SELECT region_reg 
            FROM public."public.director_regional" 
            WHERE dni_reg = %s
            
        """
        with connection.cursor() as cursor:
            cursor.execute(query, [user.username])
            rows = cursor.fetchall()
        
        regiones = [row[0] for row in rows] if rows else []
        print(regiones)
        return regiones

    def get_queryset(self):
        """
        Obtiene el queryset de PersonalDocCentral filtrado por la regional del usuario logueado.

        Returns:
            QuerySet: Lista de PersonalDocCentral filtrados por la región correspondiente.
        """
        regional_usuario = self.get_regional_usuario()
        if regional_usuario:
            # Filtramos PersonalDocCentral por la región correspondiente
            return Supervisor.objects.filter(region__in=regional_usuario)
        return Supervisor.objects.none()

    def get_form(self, *args, **kwargs):
        """
        Personaliza el formulario para filtrar supervisores según la región del usuario logueado.
        """
        form = super().get_form(*args, **kwargs)
        regional_usuario = self.get_regional_usuario()
        if regional_usuario:
            form.fields['supervisor'].queryset = Supervisor.objects.filter(region__in=regional_usuario)
        else:
            form.fields['supervisor'].queryset = Supervisor.objects.none()
        return form
    
    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST['action']
            if action == 'search_schools':
                data = []
                prods=EscuelasSupervisadas.objects.filter(cueanexo__icontains=request.POST['term'])[0:10]
                for i in prods:
                    item = i.toJSON()
                    item['value'] = f"{i.cueanexo} {i.nom_est} - {i.oferta}"
                    data.append(item)
            elif action == 'add':
                with transaction.atomic():
                    asigna = json.loads(request.POST['asignado'])
                    
                    asignacion = Asignacion()
                    asignacion.supervisor_id=asigna['supervisor']
                    asignacion.total=asigna['total']
                    asignacion.save()
                    
                    for i in asigna['detescuelas']:
                        det = DetalleAsignacion()
                        det.asignacion_id=asignacion.id
                        det.escuela = EscuelasSupervisadas.objects.get(id=i['id'])
                        det.save()
    
            else:
                data['error'] = 'No ha ingresado a ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data, safe=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Asignación de Unidades de Servicios a Supervisor'
        context['entity'] = 'Asignación'
        context['list_url'] = self.success_url
        context['action'] = 'add'
        context['det']=[]
        return context


class AsignacionListView(LoginRequiredMixin, ListView):
    model = Asignacion
    template_name = 'superv/asignacion/list.html'

    def get_regional_usuario(self):
        """
        Obtiene el regional del usuario logueado consultando directamente la tabla cenpe.cueregional.
        """
        user = self.request.user
        query = """
            SELECT region_reg
            FROM public."public.director_regional"
            WHERE dni_reg = %s
            
        """
        with connection.cursor() as cursor:
            cursor.execute(query, [user.username])
            rows = cursor.fetchall()
        
        regiones = [row[0] for row in rows] if rows else []
        print(regiones)
        return regiones

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
                data = [i.toJSON() for i in Asignacion.objects.filter(supervisor__region__in=regional_usuario)]
            elif action == 'search_details_asign':
                data = []
                for i in DetalleAsignacion.objects.filter(asignacion_id=request.POST['id'],
                    asignacion__supervisor__region__in=regional_usuario):
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


class AsignacionDeleteView(LoginRequiredMixin, DeleteView):
    model = Asignacion
    template_name = 'superv/asignacion/delete.html'
    success_url = reverse_lazy('superescuela:asign_list')    
    url_redirect = success_url

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            self.object.delete()
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Eliminación de Asignación'
        context['entity'] = 'Asignacion'
        context['list_url'] = self.success_url
        return context


class AsignacionUpdateView(LoginRequiredMixin, UpdateView):
    model = Asignacion
    form_class = AsignacionForm
    template_name = 'superv/asignacion/create.html'
    success_url = reverse_lazy('superescuela:asign_list')
    url_redirect = success_url

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST['action']
            if action == 'search_schools':
                data = []
                prods = EscuelasSupervisadas.objects.filter(cueanexo__icontains=request.POST['term'])[0:10]
                for i in prods:
                    item = i.toJSON()
                    item['value'] = f"{i.cueanexo} {i.nom_est} - {i.oferta}"
                    data.append(item)
            elif action == 'edit':
                with transaction.atomic():
                    asigna = json.loads(request.POST['asignado'])
                    
                    asignacion = self.get_object()
                    asignacion.supervisor_id = asigna['supervisor']
                    asignacion.total = asigna['total']
                    asignacion.save()
                    # Usar detalleasignacion_set
                    asignacion.detalleasignacion_set.all().delete()
                    for i in asigna['detescuelas']:
                        det = DetalleAsignacion()
                        det.asignacion_id = asignacion.id
                        det.escuela = EscuelasSupervisadas.objects.get(id=i['id'])
                        det.save()
            else:
                data['error'] = 'No ha ingresado a ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data, safe=False)
    
    def get_details_escuelas(self):
        data = []
        try:
            for i in DetalleAsignacion.objects.filter(asignacion_id=self.get_object().id):
                item = i.escuela.toJSON()
                data.append(item)
        except:
            pass
        return data
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edición de Asignación'
        context['entity'] = 'Asignación'
        context['list_url'] = self.success_url
        context['action'] = 'edit'
        context['det'] = self.get_details_escuelas()
        return context