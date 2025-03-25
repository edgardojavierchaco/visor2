from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import cache_control
from django.db import connection
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from .forms import PersonalDocUegpForm, PersonalNoDocUegpForm
#from .mixins import ValidatePermissionRequiredMixin
from .models import PersonalDocUegp, PersonalNoDocUegp
from django.shortcuts import get_object_or_404
from apps.usuarios.models import UsuariosVisualizador

class UEGPListViewAdmin(LoginRequiredMixin, ListView):
    """
    Vista para listar PersonalNoDocUegp filtrados por la regional del usuario logueado.

    Atributos:
        model: El modelo PersonalNoDocUegp.
        template_name: La plantilla utilizada para mostrar el listado.
        context_object_name: El nombre del contexto para el listado de PersonalNoDocUegp.
    """
    model = PersonalNoDocUegp
    template_name = 'uegp/pers_no_doc_uegp/list_admin.html'
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
        Obtiene el queryset de PersonalNoDocUegp filtrado por el cueanexo del usuario logueado.

        Returns:
            QuerySet: Lista de PersonalNoDocUegp filtrada por el cueanexo del usuario autenticado.
        """
        usuario = self.request.user.username        
        return PersonalNoDocUegp.objects.filter(cueanexo=usuario)  

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """
        Maneja solicitudes POST para buscar datos de PersonalNoDocUegp.
        """
        data = {}
        try:
            action = request.POST['action']
            if action == 'searchdata':
                data = []
                for i in self.get_queryset():
                    print(f"Procesando PersonalNoDocUegp: {i}")
                    item_json = i.toJSON()  # Asegúrate de que toJSON devuelva un diccionario
                    print(f"Item JSON: {item_json}")
                    data.append(item_json)             
                    
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
        context['create_url'] = reverse_lazy('privada:uegp_create_admin')
        context['list_url'] = reverse_lazy('privada:uegp_list_admin')         
        context['entity'] = 'Personal No Docente'
        return context


class UEGPCreateViewAdmin(LoginRequiredMixin, CreateView):
    model = PersonalNoDocUegp
    form_class = PersonalNoDocUegpForm
    template_name = 'uegp/pers_no_doc_uegp/create_admin.html'
    success_url = reverse_lazy('privada:uegp_list_admin')
    #permission_required = 'apps.add_client'
    url_redirect = success_url

    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        try:
            action = request.POST.get('action')
            print("📌 Método POST ejecutado")
            if action == 'add':
                form = self.get_form()
                if form.is_valid():
                    # Obtener el username del UsuarioVisualizador relacionado
                    usuario_visualizador = UsuariosVisualizador.objects.get(username=request.user.username)
                    print(f"✅ Usuario Visualizador encontrado: {usuario_visualizador.username}")
                    form.instance.cueanexo = usuario_visualizador.username
                    form.instance.subvencionado = self.request.POST.get('subvencionado') == 'on'
                    form.save() 
                    print("✅ Registro guardado con éxito")  
                    return HttpResponseRedirect(self.success_url)
                else:
                    print("Errores del formulario:", form.errors.as_json()) 
                    return self.form_invalid(form)
            else:
                return JsonResponse({'error': 'No ha ingresado a ninguna opción'})
        except Exception as e:
            print("Error en post:", str(e))
            return JsonResponse({'error': str(e)})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Agregar Personal No Docente UEGP'
        context['entity'] = 'Personal No Docente'
        context['list_url'] = self.success_url
        context['action'] = 'add'
        return context


class UEGPUpdateViewAdmin(LoginRequiredMixin, UpdateView):
    model = PersonalNoDocUegp
    form_class = PersonalNoDocUegpForm
    template_name = 'uegp/pers_no_doc_uegp/create_admin.html'
    success_url = reverse_lazy('privada:uegp_list_admin')
    #permission_required = 'apps.change_client'
    url_redirect = success_url

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
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
        context['title'] = 'Edición de Personal No Docente'
        context['entity'] = 'Personal No Docente'
        context['list_url'] = self.success_url
        context['action'] = 'edit'
        return context


class UEGPDeleteViewAdmin(LoginRequiredMixin, DeleteView):
    model = PersonalNoDocUegp
    template_name = 'uegp/pers_no_doc_uegp/delete_admin.html'
    success_url = reverse_lazy('privada:uegp_list_admin')
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

