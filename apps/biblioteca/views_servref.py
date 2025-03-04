from django.http import JsonResponse
from django.urls import reverse_lazy
from django.shortcuts import render, redirect
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from .models import ServicioReferencia, GenerarInforme
from .forms import ServicioReferenciaForm
from django.views.generic import CreateView, UpdateView, ListView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin


# Cargar
class ServiciosReferenciaCreateView(LoginRequiredMixin, CreateView):
    model = ServicioReferencia
    form_class = ServicioReferenciaForm
    template_name = 'biblioteca/pem/servref/create.html'
    success_url = reverse_lazy('bibliotecas:servref_list')
    
    def form_valid(self, form):
        form.instance.cueanexo = self.request.user.username
        return super().form_valid(form)

    def post(self, request, *args, **kwargs):
        """Manejo de AJAX para agregar servicio de referencia."""
        data = {}

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':  # Detecta si es una solicitud AJAX
            try:
                action = request.POST.get('action', None)  # Evita KeyError
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

        # Si no es AJAX, manejamos el formulario normalmente
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        else:
            # En caso de que el formulario no sea válido, volvemos a renderizar el template con los errores.
            return self.render_to_response(self.get_context_data(form=form)) 

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cueanexo']= self.request.user.username
        context['title'] = 'Carga Servicios de Referencia'
        context['entity'] = 'Servicios_Referencia'
        context['list_url'] = self.success_url
        context['action'] = 'add'
        
        # Obtener el último mes y año del usuario logueado
        ultimo_informe = GenerarInforme.objects.filter(cueanexo=self.request.user.username).order_by('-annos', '-meses').first()

        context['mes'] = ultimo_informe.meses if ultimo_informe else None
        context['anno'] = ultimo_informe.annos if ultimo_informe else None

        return context



#editar
class ServiciosReferenciaUpdateView(LoginRequiredMixin, UpdateView):
    model = ServicioReferencia
    form_class = ServicioReferenciaForm
    template_name = 'biblioteca/pem/servref/create.html'
    success_url = reverse_lazy('bibliotecas:servref_list')
    #permission_required = 'apps.change_client'
    url_redirect = success_url

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """Manejo de AJAX para editar servicio de referencia."""
        data = {}

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':  # Detecta si es una solicitud AJAX
            try:
                action = request.POST.get('action', None)  # Evita KeyError
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

        # Si no es AJAX, manejamos el formulario normalmente
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        else:
            # En caso de que el formulario no sea válido, volvemos a renderizar el template con los errores.
            return self.render_to_response(self.get_context_data(form=form))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edición Servicios de Referencia'
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
class ServiciosReferenciaDeleteView(LoginRequiredMixin, DeleteView):
    model = ServicioReferencia
    template_name = 'biblioteca/pem/servref/delete.html'
    success_url = reverse_lazy('bibliotecas:servref_list')
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
        context['title'] = 'Eliminación Servicios de Referencia'
        context['entity'] = 'Servicios_Referencia'
        context['list_url'] = self.success_url
        return context


#Listado
class ServiciosReferenciaListView(LoginRequiredMixin, ListView):
    model = ServicioReferencia
    template_name = 'biblioteca/pem/servref/list_servref.html'
    #permission_required = 'apps.view_supervisor'    
    
    def get_queryset(self):    
        serviciosref = ServicioReferencia.objects.filter(cueanexo=self.request.user.username)
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
        context['title'] = 'Listado de Servicios de Referencia cargado'
        context['create_url'] = reverse_lazy('bibliotecas:servref_create')
        context['list_url'] = reverse_lazy('bibliotecas:servref_list')
        context['update_url'] = reverse_lazy('bibliotecas:servref_update', args=[0])
        context['hide_lock_button'] = False      
        context['generar_pdf_button'] = True,   
        context['next_url'] = reverse_lazy('bibliotecas:servrefvirtual_create')
        context['entity'] = 'Servicios_Referencia'
        return context
        


