from typing import Any
from django.db.models.base import Model as Model
from django.db.models.query import QuerySet
from django.http import HttpResponse, Http404
from django.shortcuts import render
from .models import CanalMensaje, CanalUsuario, Canal
from django.views.generic import DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied

class CanalDetailView(LoginRequiredMixin,DetailView):
    template_name='Dm/canal_detail.html'
    queryset=Canal.objects.all()
    
    """ def get_queryset(self):
        usuario = self.request.user
        username=usuario.username
        
        qs = Canal.objects.all().filtrar_por_username(username)
        return qs """
    
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        obj = context['object']
        print(obj)
        
        if self.request.user not in obj.usuario.all():
            raise PermissionDenied 
        return context
       


class DetailMs(LoginRequiredMixin,DetailView):       
    template_name='Dm/canal_detail.html'
    
    def get_object(self,*args,**kwargs):
        
        username=self.kwargs.get("username")        
        mi_usuario = self.request.user.username        
        canal, _ =Canal.objects.obtener_o_crear_canal_ms(mi_usuario,username)
        
        if username == mi_usuario:
            mi_canal, _ = Canal.objects.obtener_o_crear_canal_usuario_actual(self.request.user)
            
            return mi_canal
        
        if canal == None:
            raise Http404
    
        return canal
    
    
def mensajes_privados(request, username, *args, **kwargs):
    
    if not request.user.is_authenticated:
        return HttpResponse("Prohibido")
    
    mi_usuario=request.user.username
    
    
    canal, created =Canal.objects.obtener_o_crear_canal_ms(mi_usuario,username)    
    
    if created:
        print("sí, fue creado")   
    
    
    Usuarios_Canal=canal.canalusuario_set.all().values("usuario__username")
    print(Usuarios_Canal)
    mensaje_canal=canal.canalmensaje_set.all()
    print(mensaje_canal.values("texto"))
    
    return HttpResponse(f"Nuestro Id del Canal - {canal.id}")