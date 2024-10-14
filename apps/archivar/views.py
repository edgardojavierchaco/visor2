from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.views.generic import CreateView, ListView, TemplateView, UpdateView, DeleteView
from .forms import ArchRegisterForm
from .models import ArchRegister
from .mixins import GroupRequiredMixin, ReadOnlyAccessMixin

class ArchivoCreateView(GroupRequiredMixin,CreateView):
    """
    Vista para crear un nuevo archivo normativo.

    Hereda de GroupRequiredMixin para asegurar que solo los usuarios
    con el grupo adecuado pueden acceder a esta vista.

    Attributes:
        model (ArchRegister): Modelo de datos para el registro de archivos.
        form_class (ArchRegisterForm): Formulario utilizado para crear un archivo.
        template_name (str): Nombre del template a renderizar.
        success_url (str): URL a la que se redirige al usuario después de una creación exitosa.

    Methods:
        get_context_data: Añade contexto adicional al template, como el título de la página.
    """
    model = ArchRegister
    form_class = ArchRegisterForm
    template_name = 'archivos/cargar_archivo.html'
    success_url = reverse_lazy('archivos:listar')

    def get_context_data(self, **kwargs):
        context=super().get_context_data(**kwargs)
        context['title']='Cargar Archivo'
        return context

class ArchivosListView(ReadOnlyAccessMixin,ListView):
    """
    Vista para listar todos los archivos normativos.

    Hereda de ReadOnlyAccessMixin para permitir el acceso solo de lectura
    a los usuarios autorizados.

    Attributes:
        model (ArchRegister): Modelo de datos para el registro de archivos.
        template_name (str): Nombre del template a renderizar.
        context_object_name (str): Nombre del contexto que contiene la lista de archivos.

    Methods:
        get_context_data: Añade contexto adicional al template, como el título de la página.
    """
    model=ArchRegister
    template_name='archivos/archivos_lista.html'
    context_object_name='archivos' 
    
    def get_context_data(self, **kwargs):
        context=super().get_context_data(**kwargs)
        context['title']='Listado de Archivos'
        return context
    

class BuscarPDFView(TemplateView):   
    """
    Vista para buscar un archivo PDF basado en cueanexo y asunto.

    Methods:
        post: Maneja las solicitudes POST para buscar el archivo y devolver su URL.
    """
    def post(self, request, *args, **kwargs):
        cueanexo = request.POST.get('cueanexo')
        asunto = request.POST.get('asunto')
        archivo = ArchRegister.objects.filter(cueanexo=cueanexo, asunto__asunto=asunto).first()
        if archivo and archivo.archivo:
            return JsonResponse({'ruta_pdf': archivo.archivo.url})
        else:
            return JsonResponse({'error': 'No se encontró ningún PDF con el cueanexo y asunto especificados.'})

class editar_archivos(GroupRequiredMixin,UpdateView):
    """
    Vista para editar un archivo normativo existente.

    Hereda de GroupRequiredMixin para asegurar que solo los usuarios
    con el grupo adecuado pueden acceder a esta vista.

    Attributes:
        model (ArchRegister): Modelo de datos para el registro de archivos.
        form_class (ArchRegisterForm): Formulario utilizado para editar el archivo.
        template_name (str): Nombre del template a renderizar.
        success_url (str): URL a la que se redirige al usuario después de una edición exitosa.

    Methods:
        get_object: Obtiene el objeto ArchRegister que se va a editar.
        get_context_data: Añade contexto adicional al template, como el título de la página.
    """
    model = ArchRegister
    form_class = ArchRegisterForm
    template_name = 'archivos/editar.html'
    success_url = reverse_lazy('archivos:listar')

    def get_object(self):
        user_id = self.request.GET.get('id')
        return get_object_or_404(ArchRegister, id=user_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Archivo'
        return context

class EliminarArchivosView(GroupRequiredMixin,DeleteView):
    """
    Vista para eliminar un archivo normativo.

    Hereda de GroupRequiredMixin para asegurar que solo los usuarios
    con el grupo adecuado pueden acceder a esta vista.

    Methods:
        get: Maneja las solicitudes GET para eliminar el archivo y redirigir al usuario.
    """
    def get(self, request):
        user_id = request.GET.get('id')
        user = get_object_or_404(ArchRegister, id=user_id)
        user.delete()
        return redirect('archivos:listar') 