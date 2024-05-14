from django.shortcuts import render
from django.views.generic import ListView

from apps.usuarios.models import UsuariosVisualizador

class listado_usuarios(ListView):
    model=UsuariosVisualizador        
    template_name='usuarios/listado.html' 
    context_object_name='usuarios'   
    print(context_object_name)
    
    def get_context_data(self, **kwargs):
        context=super().get_context_data(**kwargs)
        context['title']='Listado de Usuarios'
        return context
