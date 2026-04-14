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
from .models import Asignacion, DetalleAsignacion, EscuelasRepresentadas, RepresentantesLegales


class AsignacionCreateView(LoginRequiredMixin, CreateView):
    model = Asignacion
    form_class = AsignacionForm
    template_name = 'replegales/asignacion/create.html'
    success_url = reverse_lazy('representantes:asign_create')
    #permission_required = 'apps.add_asignacion'
    url_redirect = success_url

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)
    
    
    def get_queryset(self):
        """
        Obtiene el queryset de los Representantes Legales sin filtrar por región.

        Returns:
            QuerySet: Lista de Representantes Legales.
        """
        
        return RepresentantesLegales.objects.all()


    def get_form(self, *args, **kwargs):
        """
        Personaliza el formulario para mostrar todos los Representantes Legales.
        """
        form = super().get_form(*args, **kwargs)
        form = super().get_form(*args, **kwargs)
        # Aquí eliminamos el filtro por región
        form.fields['replegales'].queryset = RepresentantesLegales.objects.all()
        return form
    
    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST['action']
            if action == 'search_schools':
                data = []
                prods=EscuelasRepresentadas.objects.filter(cueanexo__icontains=request.POST['term'])[0:10]
                for i in prods:
                    item = i.toJSON()
                    item['value'] = f"{i.cueanexo} {i.nom_est} - {i.oferta}"
                    data.append(item)
            elif action == 'add':
                with transaction.atomic():
                    asigna = json.loads(request.POST['asignado'])
                    
                    asignacion = Asignacion()
                    asignacion.replegales_id=asigna['replegales']
                    asignacion.total=asigna['total']
                    asignacion.save()
                    
                    for i in asigna['detescuelas']:
                        det = DetalleAsignacion()
                        det.asignacion_id=asignacion.id
                        det.escuela = EscuelasRepresentadas.objects.get(id=i['id'])
                        det.save()
    
            else:
                data['error'] = 'No ha ingresado a ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data, safe=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Asignación de Unidades de Servicios a Representantes Legales'
        context['entity'] = 'Asignación'
        context['list_url'] = self.success_url
        context['action'] = 'add'
        context['det']=[]
        return context


class AsignacionListView(LoginRequiredMixin, ListView):
    model = Asignacion
    template_name = 'replegales/asignacion/list.html'

    def get_queryset(self):
        """
        Obtiene todas las asignaciones sin filtrar por región.
        """
        return Asignacion.objects.all()
        
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST['action']

            if action == 'searchdata':
                # No se aplica ningún filtro, trae todas las asignaciones
                data = [i.toJSON() for i in Asignacion.objects.all()]
            elif action == 'search_details_asign':
                data = []
                # No se aplica ningún filtro, trae todos los detalles de asignación
                for i in DetalleAsignacion.objects.filter(asignacion_id=request.POST['id']):
                    data.append(i.toJSON())
            else:
                data['error'] = 'Ha ocurrido un error'
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data, safe=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Listado de Representantes Legales con Asignaciones'
        context['create_url'] = reverse_lazy('representantes:asign_create')
        context['list_url'] = reverse_lazy('representantes:asign_list')
        context['entity'] = 'Listado'
        return context



class AsignacionDeleteView(LoginRequiredMixin, DeleteView):
    model = Asignacion
    template_name = 'replegales/asignacion/delete.html'
    success_url = reverse_lazy('representantes:asign_list')    
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
    template_name = 'replegales/asignacion/create.html'
    success_url = reverse_lazy('representantes:asign_list')
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
                prods = EscuelasRepresentadas.objects.filter(cueanexo__icontains=request.POST['term'])[0:10]
                for i in prods:
                    item = i.toJSON()
                    item['value'] = f"{i.cueanexo} {i.nom_est} - {i.oferta}"
                    data.append(item)
            elif action == 'edit':
                with transaction.atomic():
                    asigna = json.loads(request.POST['asignado'])
                    
                    asignacion = self.get_object()
                    asignacion.replegales_id = asigna['replegales']
                    asignacion.total = asigna['total']
                    asignacion.save()
                    # Usar detalleasignacion_set
                    asignacion.detalleasignacion_set.all().delete()
                    for i in asigna['detescuelas']:
                        det = DetalleAsignacion()
                        det.asignacion_id = asignacion.id
                        det.escuela = EscuelasRepresentadas.objects.get(id=i['id'])
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