from django.db.models import Model as BaseModel
from django.db.models.query import QuerySet
from django.http import HttpResponse, Http404, JsonResponse
from django.shortcuts import render, redirect
from .models import CanalMensaje, CanalUsuario, Canal
from django.views.generic import DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from .forms import FormMensajes
from django.views.generic.edit import FormMixin
from django.views import View
from .forms import CanalEleccionForm
from django.views.generic import TemplateView

class ChatView(LoginRequiredMixin, TemplateView):
    template_name = 'Dm/canal_detail.html'  
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        canal_id = self.kwargs.get('canal_id')
        canal = Canal.objects.get(id=canal_id)

        context['canal'] = canal
        context['usuarios_conectados'] = CanalUsuario.objects.filter(canal=canal)  
        print(context)
        return context  # Añadido para devolver el contexto

class Inbox(View):
    def get(self, request):
        inbox = Canal.objects.filter(canalusuario__usuario=request.user)
        
        context = {
            'inbox': inbox
        }
        
        return render(request, 'Dm/inbox.html', context)

class CanalFormMixin(FormMixin):
    form_class = FormMensajes
    
    def get_success_url(self):
        return self.request.path

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise PermissionDenied
        
        form = self.get_form()
        if form.is_valid():
            canal = self.get_object()
            usuario = request.user
            mensaje = form.cleaned_data.get('mensaje')
            
            canal_obj = CanalMensaje.objects.create(canal=canal, usuario=usuario, texto=mensaje)
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'mensaje': canal_obj.texto,
                    'username': canal_obj.usuario.username,
                    'tiempo': canal_obj.tiempo  # Añadido para devolver el tiempo
                }, status=201)
            
            return super().form_valid(form)
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'error': form.errors}, status=400)
        
        return super().form_invalid(form)
    
class CanalDetailView(LoginRequiredMixin, CanalFormMixin, DetailView):
    template_name = 'Dm/canal_detail.html'
    queryset = Canal.objects.all()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = context['object']
        
        context['si_canal_miembro'] = self.request.user in obj.usuario.all()
        context['canal'] = obj
        return context
    
    def get_mensajes(self, request, *args, **kwargs):
        canal_id = self.kwargs.get('canal_id')
        canal = Canal.objects.get(id=canal_id)
        mensajes = canal.canalmensaje_set.all().values('usuario__username', 'texto', 'tiempo')

        return JsonResponse({'mensajes': list(mensajes)})
    
class DetailMs(LoginRequiredMixin, CanalFormMixin, DetailView):       
    template_name = 'Dm/canal_detail.html'
    
    def get_object(self, **kwargs):
        username = self.kwargs.get("username")        
        mi_usuario = self.request.user.username        
        canal, _ = Canal.objects.obtener_o_crear_canal_ms(mi_usuario, username)
        
        if username == mi_usuario:
            mi_canal, _ = Canal.objects.obtener_o_crear_canal_usuario_actual(self.request.user)
            return mi_canal
        
        if canal is None:
            raise Http404
    
        return canal    
    
    
def mensajes_privados(request, username, *args, **kwargs):
    if not request.user.is_authenticated:
        return HttpResponse("Prohibido")
    
    mi_usuario = request.user.username
    canal, created = Canal.objects.obtener_o_crear_canal_ms(mi_usuario, username)    
    
    return HttpResponse(f"Nuestro Id del Canal - {canal.id}")

def unirse_canal(request, canal_nombre):
    if not request.user.is_authenticated:
        raise PermissionDenied

    canal, creado = Canal.objects.obtener_o_crear_canal_usuario(request.user, canal_nombre)

    if canal:
        return HttpResponse(f"Te has unido al canal {canal.nombre}.")
    else:
        return HttpResponse("Error al unirse al canal.")

def elegir_canal(request):
    if not request.user.is_authenticated:
        raise PermissionDenied

    if request.method == 'POST':
        form = CanalEleccionForm(request.POST)
        if form.is_valid():
            canal_nombre = form.cleaned_data.get('canal')
            canal, creado = Canal.objects.obtener_o_crear_canal_usuario(request.user, canal_nombre)
            if canal:
                return redirect('dm:chat', canal_id=canal.id)
            else:
                return HttpResponse("Hubo un error al unirse al canal.")
    else:
        form = CanalEleccionForm()

    return render(request, 'Dm/elegir_canal.html', {'form': form})

def obtener_mensajes(request, canal_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'No autorizado'}, status=403)

    mensajes = CanalMensaje.objects.filter(canal__id=canal_id).values('usuario__username', 'texto', 'tiempo')
    return JsonResponse(list(mensajes), safe=False)