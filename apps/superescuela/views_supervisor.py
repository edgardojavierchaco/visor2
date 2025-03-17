from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.db import connection
from .forms import SupervisorForm
#from .mixins import ValidatePermissionRequiredMixin
from .models import Supervisor


class SupervisoresListView(LoginRequiredMixin, ListView):
    model = Supervisor
    template_name = 'superv/supervisor/list.html'
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
            LIMIT 1
        """
        with connection.cursor() as cursor:
            cursor.execute(query, [user.username])
            row = cursor.fetchone()
        
            print(row)
        return row[0] if row else None

    def get_queryset(self):
        """
        Obtiene el queryset de PersonalDocCentral filtrado por la regional del usuario logueado.

        Returns:
            QuerySet: Lista de PersonalDocCentral filtrados por la región correspondiente.
        """
        regional_usuario = self.get_regional_usuario()
        print("regional del usuario:",regional_usuario)
        if regional_usuario:
            # Filtramos PersonalDocCentral por la región correspondiente
            return Supervisor.objects.filter(region=regional_usuario)
        return Supervisor.objects.none()

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        print(f"📌 Método dispatch ejecutado con {request.method}")
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        print("📌 Método POST ejecutado")
        data = {}
        try:
            action = request.POST['action']
            print(f"📌 Acción recibida: {action}") 
            if action == 'searchdata':
                data = []
                queryset = self.get_queryset()
                print("Supervisores encontrados:", queryset.count())
                for i in self.get_queryset():
                    print("Supervisor:", i.toJSON())
                    data.append(i.toJSON())
                print("Supervisor:", i.toJSON())
            else:
                data['error'] = 'Ha ocurrido un error'
        except Exception as e:
            data['error'] = str(e)
            print("Error en post:", str(e))
        return JsonResponse(data, safe=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Listado de Supervisores'
        context['create_url'] = reverse_lazy('superescuela:super_create')
        context['list_url'] = reverse_lazy('superescuela:super_list')
        context['update_url'] = reverse_lazy('superescuela:super_update', args=[0]) 
        context['entity'] = 'Supervisor'
        return context


class SupervisorCreateView(LoginRequiredMixin, CreateView):
    model = Supervisor
    form_class = SupervisorForm
    template_name = 'superv/supervisor/create.html'
    success_url = reverse_lazy('superescuela:super_list')
    #permission_required = 'apps.add_client'
    url_redirect = success_url

    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        print("📌 Método POST ejecutado")
        data = {}
        try:
            action = request.POST['action']
            if action == 'add':
                form = self.get_form()
                data = form.save()
            else:
                data['error'] = 'No ha ingresado a ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Creación un Supervisor'
        context['entity'] = 'Supervisor'
        context['list_url'] = self.success_url
        context['action'] = 'add'
        return context


class SupervisorUpdateView(LoginRequiredMixin, UpdateView):
    model = Supervisor
    form_class = SupervisorForm
    template_name = 'superv/supervisor/create.html'
    success_url = reverse_lazy('superescuela:super_list')
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
                data = form.save()
            else:
                data['error'] = 'No ha ingresado a ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edición un Supervisor'
        context['entity'] = 'Supervisor'
        context['list_url'] = self.success_url
        context['action'] = 'edit'
        return context


class SupervisorDeleteView(LoginRequiredMixin, DeleteView):
    model = Supervisor
    template_name = 'superv/supervisor/delete.html'
    success_url = reverse_lazy('superescuela:super_list')
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
        context['title'] = 'Eliminación de un Supervisor'
        context['entity'] = 'Supervisor'
        context['list_url'] = self.success_url
        return context

@method_decorator(csrf_exempt, name='dispatch')
class SupervisoresListViewGestor(LoginRequiredMixin, ListView):
    model = Supervisor
    template_name = 'superv/supervisor/list_gestor.html'
    
    def get_queryset(self):
        return Supervisor.objects.all()  

    
    def post(self, request, *args, **kwargs):  
        data = {}
        try:
            action = request.POST.get('action', '')  
            if action == 'searchdata':
                data = [i.toJSON() for i in self.get_queryset()]  
            else:
                data['error'] = 'Acción no válida'
        except Exception as e:
            data['error'] = str(e)  # ✅ Convertimos el error en string
        return JsonResponse(data, safe=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': 'Listado de Supervisores',
            'list_url': reverse_lazy('superescuela:super_list_gestor'),
            'entity': 'Supervisor'
        })
        print('Listado supervisores:',context)
        return context