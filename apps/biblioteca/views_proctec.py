from django.http import JsonResponse
from django.urls import reverse_lazy
from django.shortcuts import render, redirect
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from .models import ProcesosTecnicos, GenerarInforme
from .forms import ProcesosTecnicosForm
from django.views.generic import CreateView, UpdateView, ListView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.consultasge.models import CapaUnicaOfertas
from django.db.models import Func, F, Value 
import re


# Cargar
class ProcTecCreateView(LoginRequiredMixin, CreateView):
    model = ProcesosTecnicos
    form_class = ProcesosTecnicosForm
    template_name = 'biblioteca/pem/proctec/create.html'
    success_url = reverse_lazy('bibliotecas:proctec_list')
    #permission_required = 'apps.add_client'
    url_redirect = success_url
    
    def form_valid(self, form):
        # 🔹 Obtener usuario logueado correctamente
        usuario_logueado = self.request.user.username  
        usuario_limpio = re.sub(r'\D', '', usuario_logueado)
        print("Usuario logueado:", usuario_logueado)  # Debug: Verificar el usuario logueado
        
        # 🔹 Obtener todos los cueanexos que cumplan la condición
        cueanexos_qs = CapaUnicaOfertas.objects.annotate(
            cuit_limpio=Func(
                F('resploc_cuitcuil'),
                Value('-'),
                Value(''),
                function='REPLACE'
            )
        ).filter(
            cuit_limpio=usuario_limpio,
            oferta='Común - Servicios complementarios ',
            acronimo='BI'
        ).values_list('cueanexo', flat=True)
        
        cueanexos = list(cueanexos_qs)
        
        form.instance.cueanexo = cueanexos[0] if cueanexos else None
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
                    data = instance.toJSON() 
            else:
                data['error'] = 'No ha ingresado a ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data)    
    

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        usuario_logueado = self.request.user.username

        # Limpiar caracteres no numéricos del CUIT/CUIL
        usuario_limpio = re.sub(r'\D', '', usuario_logueado)

        # Obtener primer cueanexo del usuario
        cueanexo_qs = CapaUnicaOfertas.objects.annotate(
            cuit_limpio=Func(
                F('resploc_cuitcuil'),
                Value('-'),
                Value(''),
                function='REPLACE'
            )
        ).filter(
            cuit_limpio=usuario_limpio,
            oferta='Común - Servicios complementarios ',
            acronimo='BI'
        ).values_list('cueanexo', flat=True)       
        
        context['title'] = 'Carga de Procesos Técnicos'
        context['entity'] = 'Procesos_Técnicos'
        context['list_url'] = self.success_url
        context['action'] = 'add'
        context['cueanexo'] = cueanexo_qs.first() if cueanexo_qs.exists() else None
        
        # Obtener el último mes y año del usuario logueado
        ultimo_informe = GenerarInforme.objects.filter(cueanexo=context['cueanexo']).order_by('-annos', '-meses').first()

        if ultimo_informe:
            context['mes'] = ultimo_informe.meses
            context['anno'] = ultimo_informe.annos
        else:
            context['mes'] = None
            context['anno'] = None
            
        return context


#editar
class ProcTecUpdateView(LoginRequiredMixin, UpdateView):
    model = ProcesosTecnicos
    form_class = ProcesosTecnicosForm
    template_name = 'biblioteca/pem/proctec/create.html'
    success_url = reverse_lazy('bibliotecas:proctec_list')
    #permission_required = 'apps.change_client'
    url_redirect = success_url

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST['action']
            if action == 'edit':
                form = self.get_form()
                if form.is_valid():
                    instance = form.save()
                    data = instance.toJSON() 
            else:
                data['error'] = 'No ha ingresado a ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        usuario_logueado = self.request.user.username

        # Limpiar caracteres no numéricos del CUIT/CUIL
        usuario_limpio = re.sub(r'\D', '', usuario_logueado)

        # Obtener primer cueanexo del usuario
        cueanexo_qs = CapaUnicaOfertas.objects.annotate(
            cuit_limpio=Func(
                F('resploc_cuitcuil'),
                Value('-'),
                Value(''),
                function='REPLACE'
            )
        ).filter(
            cuit_limpio=usuario_limpio,
            oferta='Común - Servicios complementarios ',
            acronimo='BI'
        ).values_list('cueanexo', flat=True)       
        
        context['title'] = 'Edición de Procesos Técnicos'
        context['entity'] = 'Procesos_Técnicos'
        context['list_url'] = self.success_url
        context['action'] = 'edit'
        context['cueanexo'] = cueanexo_qs.first() if cueanexo_qs.exists() else None
        return context


#Eliminar
class ProcTecDeleteView(LoginRequiredMixin, DeleteView):
    model = ProcesosTecnicos
    template_name = 'biblioteca/pem/proctec/delete.html'
    success_url = reverse_lazy('bibliotecas:proctec_list')
    #permission_required = 'apps.delete_client'
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
        context['title'] = 'Eliminación de Procesos Técnicos'
        context['entity'] = 'Procesos_Técnicos'
        context['list_url'] = self.success_url
        return context


#Listado
class ProcTecListView(LoginRequiredMixin, ListView):
    model = ProcesosTecnicos
    template_name = 'biblioteca/pem/proctec/list_proctec.html'
    #permission_required = 'apps.view_supervisor'    
    
    def get_queryset(self):    
        usuario_logueado = self.request.user.username

        # Limpiar caracteres no numéricos del CUIT/CUIL
        usuario_limpio = re.sub(r'\D', '', usuario_logueado)

        # Obtener primer cueanexo del usuario
        cueanexo_qs = CapaUnicaOfertas.objects.annotate(
            cuit_limpio=Func(
                F('resploc_cuitcuil'),
                Value('-'),
                Value(''),
                function='REPLACE'
            )
        ).filter(
            cuit_limpio=usuario_limpio,
            oferta='Común - Servicios complementarios ',
            acronimo='BI'
        ).values_list('cueanexo', flat=True)       
        
        serviciosref = ProcesosTecnicos.objects.filter(cueanexo=cueanexo_qs.first() if cueanexo_qs.exists() else None)
        print('material:',serviciosref)
        return serviciosref
        

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
        context['title'] = 'Listado de Procesos Técnicos'
        context['create_url'] = reverse_lazy('bibliotecas:proctec_create')
        context['list_url'] = reverse_lazy('bibliotecas:proctec_list')
        context['update_url'] = reverse_lazy('bibliotecas:proctec_update', args=[0]) 
        context['hide_lock_button'] = False    
        context['generar_pdf_button'] = True,  
        context['next_url'] = reverse_lazy('bibliotecas:aguapey_create')
        context['entity'] = 'Asistencia'
        return context


