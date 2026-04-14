from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, UpdateView, DeleteView, ListView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import F, Func, Value
import re

from .models import BibliotecariosCue, GenerarInforme
from .forms import BibliotecariosCueForm
from apps.consultasge.models_padron import CapaUnicaOfertas
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator


# =========================================================
# CREATE
# =========================================================
class BibliotecariosCueCreateView(LoginRequiredMixin, CreateView):
    model = BibliotecariosCue
    form_class = BibliotecariosCueForm
    template_name = 'biblioteca/pem/personal/create.html'
    success_url = reverse_lazy('bibliotecas:bibliotecario_list')

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
        
        form.instance.cueanexo = cueanexos[0] if cueanexos else None  # Asignar el primer cueanexo encontrado o None si no hay
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
        
        cueanexo = cueanexo_qs.first() if cueanexo_qs.exists() else None
        
        context['cueanexo']= cueanexo
        context['title'] = 'Carga Servicios de Referencia'
        context['entity'] = 'Servicios_Referencia'
        context['list_url'] = self.success_url
        context['action'] = 'add'
        
        # Obtener el último mes y año del usuario logueado
        ultimo_informe=None
        if cueanexo:
            ultimo_informe = GenerarInforme.objects.filter(
                cueanexo=cueanexo
            ).order_by('-annos', '-meses').first()

        context['mes'] = ultimo_informe.meses if ultimo_informe else None
        context['anno'] = ultimo_informe.annos if ultimo_informe else None
        

        return context


# =========================================================
# UPDATE
# =========================================================
class BibliotecariosCueUpdateView(LoginRequiredMixin, UpdateView):
    model = BibliotecariosCue
    form_class = BibliotecariosCueForm
    template_name = 'biblioteca/pem/personal/create.html'
    success_url = reverse_lazy('bibliotecas:bibliotecario_list')
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
    
        context['title'] = 'Editar Bibliotecario'
        context['entity'] = 'Personal'
        context['list_url'] = self.success_url
        context['action'] = 'edit'
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


# =========================================================
# DELETE
# =========================================================
class BibliotecariosCueDeleteView(LoginRequiredMixin, DeleteView):
    model = BibliotecariosCue
    template_name = 'biblioteca/pem/personal/delete.html'
    success_url = reverse_lazy('bibliotecas:bibliotecario_list')
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
        context['title'] = 'Eliminación Personal'
        context['entity'] = 'Personal'
        context['list_url'] = self.success_url
        return context


# =========================================================
# LIST (HTML)
# =========================================================
class BibliotecariosCueListView(LoginRequiredMixin, ListView):
    model = BibliotecariosCue
    template_name = 'biblioteca/pem/personal/list_bibliotecario.html'    

    def get_queryset(self):    
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
        
        personal=BibliotecariosCue.objects.filter(cueanexo=cueanexos[0] if cueanexos else None)  # Filtrar por el primer cueanexo encontrado o None si no hay
        print('material:',personal)
        return personal


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
        context['title'] = 'Listado de Personal Bibliotecario'
        context['create_url'] = reverse_lazy('bibliotecas:bibliotecario_create')
        context['list_url'] = reverse_lazy('bibliotecas:bibliotecario_list')
        context['update_url'] = reverse_lazy('bibliotecas:bibliotecario_update', args=[0])
        context['hide_lock_button'] = False      
        context['generar_pdf_button'] = False
        context['entity'] = 'Personal'
        return context
        


