from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView, CreateView
from apps.usuarios.models import UsuariosVisualizador
from django.views.generic import TemplateView
from apps.usuarios.forms import UserForm


class DashboardView(TemplateView):
    template_name = 'pof/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['panel'] = 'Panel de administrador'
        return context
    

class UserListView(LoginRequiredMixin, ListView):
    model = UsuariosVisualizador
    template_name = 'usuarios/user/list.html'

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = []
        try:
            action = request.POST.get('action', '')
            print(f"Action received: {action}")  # Registro para verificar la acción
            if action == 'searchdata':
                # Serializamos todos los objetos del modelo
                data = [user.toJSON() for user in UsuariosVisualizador.objects.all()]
            else:
                return JsonResponse({'error': 'Acción no válida'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
        return JsonResponse(data, safe=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Listado de Usuarios'
        context['create_url'] = reverse_lazy('usuarios:user_create') 
        context['list_url'] = reverse_lazy('usuarios:user_list')
        context['entity'] = 'Usuarios'
        return context


class UserCreateView(LoginRequiredMixin, CreateView):
    model = UsuariosVisualizador
    form_class = UserForm
    template_name = 'usuarios/user/create.html'
    success_url = reverse_lazy('usuarios:user_list')
    #permission_required = 'user.add_user'
    url_redirect = success_url

    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
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
        return JsonResponse(data, safe=False)
    
    def form_valid(self, form):
        form.save()  # Guarda el formulario si es válido
        return JsonResponse({"message": "Usuario creado exitosamente."}, status=200)

    def form_invalid(self, form):
        print(form.errors)  # Para depurar los errores del formulario
        return JsonResponse({"error": form.errors}, status=400)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Creación de un Usuario'
        context['entity'] = 'Usuarios'
        context['list_url'] = self.success_url
        context['action'] = 'add'
        return context