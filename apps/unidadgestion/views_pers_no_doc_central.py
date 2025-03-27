from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import cache_control
from django.db import connection
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from .forms import PersonalDocCentralForm, PersonalNoDocCentralForm
#from .mixins import ValidatePermissionRequiredMixin
from .models import PersonalDocCentral, PersonalNoDocCentral
from django.shortcuts import get_object_or_404


class UGListViewAdmin(LoginRequiredMixin, ListView):
    """
    Vista para listar PersonalNoDocCentral filtrados por la regional del usuario logueado.

    Atributos:
        model: El modelo PersonalNoDocCentral.
        template_name: La plantilla utilizada para mostrar el listado.
        context_object_name: El nombre del contexto para el listado de PersonalNoDocCentral.
    """
    model = PersonalNoDocCentral
    template_name = 'unidadgestion/pers_no_doc_central/list_admin.html'
    #permission_required = 'apps.view_supervisor'
    
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
        Obtiene el queryset de PersonalNoDocCentral filtrado por la regional del usuario logueado.

        Returns:
            QuerySet: Lista de PersonalNoDocCentral filtrados por la región correspondiente.
        """
        regional_usuario = self.get_regional_usuario()
        if regional_usuario:
            # Filtramos PersonalDocCentral por la región correspondiente
            return PersonalNoDocCentral.objects.filter(region__in=regional_usuario)
        return PersonalNoDocCentral.objects.none()

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """
        Maneja solicitudes POST para buscar datos de PersonalDocCentral.
        """
        data = {}
        try:
            action = request.POST['action']
            if action == 'searchdata':
                data = []
                for i in self.get_queryset():
                    print(f"Procesando PersonalNoDocCentral: {i}")
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
        context['create_url'] = reverse_lazy('unidadgestion:ug_create_admin')
        context['list_url'] = reverse_lazy('unidadgestion:ug_list_admin')         
        context['entity'] = 'Personal No Docente'
        return context


class UGCreateViewAdmin(LoginRequiredMixin, CreateView):
    model = PersonalNoDocCentral
    form_class = PersonalNoDocCentralForm
    template_name = 'unidadgestion/pers_no_doc_central/create_admin.html'
    success_url = reverse_lazy('unidadgestion:ug_list_admin')
    #permission_required = 'apps.add_client'
    url_redirect = success_url

    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        try:
            action = request.POST.get('action')
            if action == 'add':
                form = self.get_form()
                if form.is_valid():
                    form.save() 
                    return HttpResponseRedirect(self.success_url)
                else:
                    return self.form_invalid(form)
            else:
                return JsonResponse({'error': 'No ha ingresado a ninguna opción'})
        except Exception as e:
            return JsonResponse({'error': str(e)})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Agregar Personal No Docente Central'
        context['entity'] = 'Personal No Docente'
        context['list_url'] = self.success_url
        context['action'] = 'add'
        return context


class UGUpdateViewAdmin(LoginRequiredMixin, UpdateView):
    model = PersonalNoDocCentral
    form_class = PersonalNoDocCentralForm
    template_name = 'unidadgestion/pers_no_doc_central/create_admin.html'
    success_url = reverse_lazy('unidadgestion:ug_list_admin')
    #permission_required = 'apps.change_client'
    url_redirect = success_url

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        try:
            action = request.POST.get('action')
            if action == 'edit':
                form = self.get_form()
                if form.is_valid():
                    form.save()
                    return HttpResponseRedirect(self.success_url)
                else:
                    return self.form_invalid(form)
            else:
                return JsonResponse({'error': 'No ha ingresado a ninguna opción'})
        except Exception as e:
            return JsonResponse({'error': str(e)})


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edición de Personal No Docente'
        context['entity'] = 'Personal No Docente'
        context['list_url'] = self.success_url
        context['action'] = 'edit'
        return context


class UGDeleteViewAdmin(LoginRequiredMixin, DeleteView):
    model = PersonalNoDocCentral
    template_name = 'unidadgestion/pers_no_doc_central/delete_admin.html'
    success_url = reverse_lazy('unidadgestion:ug_list_admin')
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
        context['title'] = 'Eliminación de Personal No Docente'
        context['entity'] = 'Personal No Docente'
        context['list_url'] = self.success_url
        return context

