import json
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
#from .mixins import ValidatePermissionRequiredMixin
from django.views.generic import CreateView, ListView, DeleteView, UpdateView
from django.db import transaction

from apps.pof.forms import AsignacionPofForm

from .models import AsignacionPof, CargosHoras, DetalleAsignacionPof, UnidadServicio


class AsignacionPofCreateView(LoginRequiredMixin, CreateView):
    model = AsignacionPof
    form_class = AsignacionPofForm
    template_name = 'pof/asignacion/create.html'
    success_url = reverse_lazy('pof:cargoshoras_create')
    #permission_required = 'apps.add_asignacion'
    url_redirect = success_url

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST['action']
            if action == 'search_cargoshoras':
                data = []
                prods=CargosHoras.objects.filter(ceic__exact=request.POST['term'])[0:10]
                for i in prods:
                    item = i.toJSON()
                    item['value'] = i.denom_cargoshoras
                    data.append(item)
            elif action == 'add':
                with transaction.atomic():
                    asigna = json.loads(request.POST['asignado'])
                    
                    asignacion = AsignacionPof()
                    asignacion.unidad_id=asigna['unidad']
                    asignacion.cant_cargos=asigna['cant_cargos']
                    asignacion.cant_horas=asigna['cant_horas']
                    asignacion.save()
                    
                    for i in asigna['detcargoshoras']:
                        det = DetalleAsignacionPof()
                        det.asignacion_id=asignacion.id
                        det.cargos = CargosHoras.objects.get(id=i['id'])
                        det.cant_car=asignacion.cant_cargos
                        det.cant_hs=asignacion.cant_horas
                        
                        det.save()    
            else:
                data['error'] = 'No ha ingresado a ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data, safe=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Asignación de Cargos-Horas a Unidades Servicio'
        context['entity'] = 'Asignación_POF'
        context['list_url'] = self.success_url
        context['action'] = 'add'
        context['det']=[]
        return context


""" class AsignacionListView(LoginRequiredMixin, ListView):
    model = Asignacion
    template_name = 'superv/asignacion/list.html'

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST['action']
            if action == 'searchdata':
                data = [i.toJSON() for i in Asignacion.objects.all()]
            elif action == 'search_details_asign':
                data = []
                for i in DetalleAsignacion.objects.filter(asignacion_id=request.POST['id']):
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
                    item['value'] = i.nom_est
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
        return context """