from django.http import JsonResponse
from django.urls import reverse_lazy
from django.shortcuts import render, redirect
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from .models import ServicioReferenciaVirtual, GenerarInforme
from .forms import ServicioReferenciaVirtualForm
from django.views.generic import CreateView, UpdateView, ListView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin


# Cargar
class ServiciosRefVirtualCreateView(LoginRequiredMixin, CreateView):
    model = ServicioReferenciaVirtual
    form_class = ServicioReferenciaVirtualForm
    template_name = 'biblioteca/pem/servrefvirtual/create.html'
    success_url = reverse_lazy('bibliotecas:servrefvirtual_list')
    #permission_required = 'apps.add_client'
    url_redirect = success_url
    
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
                    # Extraer el primer error de 'total' (si existe) y devolver solo ese mensaje
                    total_error = form.errors.get('total', None)
                    if total_error:
                        data['error'] = total_error[0]  # Extrae solo el primer mensaje de error
                    else:
                        data['error'] = 'Corrige los errores antes de continuar.'  # Error general si no hay errores en 'total'
            else:
                data['error'] = 'Acción no válida.'
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data)    
    

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Carga Servicios de Referencia Virtual'
        context['entity'] = 'Servicios_Virtual'
        context['list_url'] = self.success_url
        context['action'] = 'add'
        context['cueanexo'] = self.request.user.username
        
        # Obtener el último mes y año del usuario logueado
        ultimo_informe = GenerarInforme.objects.filter(cueanexo=self.request.user.username).order_by('-annos', '-meses').first()

        if ultimo_informe:
            context['mes'] = ultimo_informe.meses
            context['anno'] = ultimo_informe.annos
        else:
            context['mes'] = None
            context['anno'] = None
            
        return context


#editar
class ServiciosRefVirtualUpdateView(LoginRequiredMixin, UpdateView):
    model = ServicioReferenciaVirtual
    form_class = ServicioReferenciaVirtualForm
    template_name = 'biblioteca/pem/servrefvirtual/create.html'
    success_url = reverse_lazy('bibliotecas:servrefvirtual_list')
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
                    data = {'message': 'Actualizado correctamente', 'instance': instance.toJSON()}
                else:
                        # Extraer el primer error de 'total' (si existe) y devolver solo ese mensaje
                        total_error = form.errors.get('total', None)
                        if total_error:
                            data['error'] = total_error[0]  # Extrae solo el primer mensaje de error
                        else:
                            data['error'] = 'Corrige los errores antes de continuar.'  # Error general si no hay errores en 'total'
            else:
                data['error'] = 'Acción no válida.'
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edición Servicios de Referencia Virtual'
        context['entity'] = 'Servicios_Referencia'
        context['list_url'] = self.success_url
        context['action'] = 'edit'
        context['cueanexo'] = self.request.user.username
        
        # Obtener el último mes y año del usuario logueado
        ultimo_informe = GenerarInforme.objects.filter(cueanexo=self.request.user.username).order_by('-annos', '-meses').first()

        if ultimo_informe:
            context['mes'] = ultimo_informe.meses
            context['anno'] = ultimo_informe.annos
        else:
            context['mes'] = None
            context['anno'] = None
            
        return context


#Eliminar
class ServiciosRefVirtualDeleteView(LoginRequiredMixin, DeleteView):
    model = ServicioReferenciaVirtual
    template_name = 'biblioteca/pem/servrefvirtual/delete.html'
    success_url = reverse_lazy('bibliotecas:servrefvirtual_list')
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
        context['title'] = 'Eliminación Servicios de Referencia Virtual'
        context['entity'] = 'Servicios_Virtual'
        context['list_url'] = self.success_url
        return context


#Listado
class ServiciosRefVirtualListView(LoginRequiredMixin, ListView):
    model = ServicioReferenciaVirtual
    template_name = 'biblioteca/pem/servrefvirtual/list_servrefvirtual.html'
    #permission_required = 'apps.view_supervisor'    
    
    def get_queryset(self):    
        serviciosref = ServicioReferenciaVirtual.objects.filter(cueanexo=self.request.user.username)
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
        context['title'] = 'Listado de Servicios de Referencia Virtual cargado'
        context['create_url'] = reverse_lazy('bibliotecas:servrefvirtual_create')
        context['list_url'] = reverse_lazy('bibliotecas:servrefvirtual_list')
        context['update_url'] = reverse_lazy('bibliotecas:servrefvirtual_update', args=[0]) 
        context['hide_lock_button'] = False   
        context['generar_pdf_button'] = True,     
        context['next_url'] = reverse_lazy('bibliotecas:servprestamo_create')
        context['entity'] = 'Servicios_Virtual'
        return context


