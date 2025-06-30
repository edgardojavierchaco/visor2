from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from .models import BibliotecariosCue, GenerarInforme
from .forms import BibliotecariosCueForm
from django.views.generic import CreateView, UpdateView, DeleteView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin

class BibliotecariosCueCreateView(LoginRequiredMixin, CreateView):
    model = BibliotecariosCue
    form_class = BibliotecariosCueForm
    template_name = 'biblioteca/pem/personal/create.html'
    success_url = reverse_lazy('bibliotecas:bibliotecario_list')
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
                    data = instance.toJSON() 
            else:
                data['error'] = 'No ha ingresado a ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data)    
    

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Carga Personal Bibliotecario'
        context['entity'] = 'Personal_Bibliotecario'
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
        data = {}
        try:
            action = request.POST['action']
            if action == 'edit':
                form = self.get_form()
                if form.is_valid():
                    instance = form.save(commit=False)
                    instance.cueanexo = request.user.username  # 👈 Asigna el username como cueanexo
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
        context['title'] = 'Edición de Personal Bibliotecario'
        context['entity'] = 'Personal_Bibliotecario'
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
class BibliotecariosCueDeleteView(LoginRequiredMixin, DeleteView):
    model = BibliotecariosCue
    template_name = 'biblioteca/pem/personal/delete.html'
    success_url = reverse_lazy('bibliotecas:bibliotecario_list')
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
        context['title'] = 'Eliminación de Personal Bibliotecario'
        context['entity'] = 'Personal_Bibliotecario'
        context['list_url'] = self.success_url
        return context


#Listado
class BibliotecariosCueListView(LoginRequiredMixin, ListView):
    model = BibliotecariosCue
    template_name = 'biblioteca/pem/personal/list_bibliotecario.html'
    #permission_required = 'apps.view_supervisor'    
    
    def get_queryset(self):    
        personalbiblio = BibliotecariosCue.objects.filter(cueanexo=self.request.user.username)
        print('material:',personalbiblio)
        return personalbiblio
        

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

    def get(self, request, *args, **kwargs):
        context = {
            'create_url': reverse('bibliotecas:bibliotecario_create'),  # URL para el botón de nuevo registro
            'list_url': reverse('bibliotecas:bibliotecario_list'),
            'title': 'Bibliotecarios',
            'hide_lock_button': True, 
            'generar_pdf_button' : False,
            'entity': 'Bibliotecarios',
            'generar_pdf_url': reverse_lazy('bibliotecas:generar_pdf'), 
            
        }           
        return render(request, self.template_name, context)
        
    """ def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Listado de Personal Bibliotecario'
        context['create_url'] = reverse_lazy('bibliotecas:bibliotecario_create')
        context['list_url'] = reverse_lazy('bibliotecas:bibliotecario_list')
        context['update_url'] = reverse_lazy('bibliotecas:bibliotecario_update', args=[0])
        context['entity'] = 'Bibliotecarios'
        context['hide_lock_button'] = True     
        context['generar_pdf_button'] = False
        context['generar_pdf_url'] = reverse_lazy('bibliotecas:generar_pdf'),
        return context """