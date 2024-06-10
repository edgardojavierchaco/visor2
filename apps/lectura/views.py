import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
import base64  # Importar base64 para usarlo más adelante
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.http import JsonResponse, HttpResponse
from django.core.exceptions import PermissionDenied
from django.views.generic import CreateView, ListView, TemplateView, UpdateView, DeleteView
from django.views import View
from .models import DocenteGradoSeccion, oplecturaabril
from .forms import CargarDocenteGradoSeccion

class DocenteCreateView(LoginRequiredMixin, CreateView):
    model = DocenteGradoSeccion
    form_class = CargarDocenteGradoSeccion
    template_name = 'lectura/cargar_docente.html'
    success_url = reverse_lazy('lectura:listado')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Cargar Docente'
        return context

class DocentesListView(LoginRequiredMixin, ListView):
    model = DocenteGradoSeccion
    template_name = 'lectura/listado.html'
    context_object_name = 'docentes'

    def get_queryset(self):
        # Obtener el usuario logueado
        user = self.request.user
        
        # Obtener el nombre de usuario del usuario logueado
        username = user.get_username()
        
        # Filtrar los docentes por el usuario logueado
        queryset = super().get_queryset().filter(cueanexo=username)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Listado de Docentes'
        return context

class DocentesUpdateView(LoginRequiredMixin, UpdateView):
    model = DocenteGradoSeccion
    form_class = CargarDocenteGradoSeccion
    template_name = 'lectura/editar.html'
    success_url = reverse_lazy('lectura:listado')

    def get_object(self):
        user_id = self.request.GET.get('id')
        return get_object_or_404(DocenteGradoSeccion, id=user_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Archivo'
        return context

class DocentesDeleteView(LoginRequiredMixin, DeleteView):
    def get(self, request):
        user_id = request.GET.get('id')
        user = get_object_or_404(DocenteGradoSeccion, id=user_id)
        user.delete()
        return redirect('lectura:listado')

def mostrar_grafico(request):
    if not request.user.is_authenticated:
        # Si el usuario no está autenticado, lanzar excepción 403
        raise PermissionDenied("No tiene permiso para ver esta página")

    # Obtener el cueanexo del usuario autenticado
    cueanexo_usuario = request.user.username

    # Filtrar los datos para el cueanexo del usuario
    datos_usuario = oplecturaabril.objects.filter(cueanexo=cueanexo_usuario)

    # Convertir los datos a una lista de diccionarios y crear un DataFrame
    datos_usuario_list = list(datos_usuario.values('desempeño', 'puntaje', 'escuela'))
    if not datos_usuario_list:
        return HttpResponse("No hay datos disponibles para esta región")

    df = pd.DataFrame(datos_usuario_list)

    # Verificar si las columnas 'desempeño' y 'puntaje' existen
    if 'desempeño' not in df.columns or 'puntaje' not in df.columns:
        return HttpResponse("Error en los datos: columnas 'desempeño' o 'puntaje' no encontradas.")

    # Calcular el total de alumnos evaluados
    total_alumnos = df.shape[0]
    
    # Agrupar y contar por categoría de desempeño
    conteo_desempeño = df['desempeño'].value_counts()

    # Calcular los porcentajes
    porcentajes = (conteo_desempeño / conteo_desempeño.sum()) * 100

    # Calcular el promedio de puntaje
    promedio_puntaje = round(df['puntaje'].mean(), 2)

    # Obtener el nombre de la escuela 
    escuela = df['escuela'].iloc[0]

    # Crear el gráfico de torta
    fig, ax = plt.subplots(figsize=(10, 6))  # Ajustar tamaño del gráfico
    wedges, texts, autotexts = ax.pie(porcentajes, labels=porcentajes.index, autopct='%1.1f%%', startangle=90, textprops=dict(color="black"))  # type: ignore

    # Mejorar el diseño del texto en el gráfico
    for text in texts:
        text.set_fontsize(8)  # Ajustar tamaño del texto de las etiquetas
    for autotext in autotexts:
        autotext.set_fontsize(8)  # Ajustar tamaño del texto de los porcentajes

    ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.

    # Guardar el gráfico en un objeto BytesIO
    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)

    # Convertir la imagen a base64 para incrustarla en la plantilla
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

    # Renderizar la plantilla y pasar el gráfico y el promedio de puntaje
    return render(request, 'lectura/grafico.html', {
        'grafico': image_base64,
        'promedio_puntaje': promedio_puntaje,
        'total_alumnos': total_alumnos,
        'escuela': escuela,
    })

def mostrar_grafico_reg(request):
    # Obtener los valores seleccionados del checkbox
    regiones_seleccionadas = request.GET.getlist('region')
    
    mostrar_todo = '0' in regiones_seleccionadas  # Verifica si se selecciona "Mostrar Todo"

    if mostrar_todo:
        # Si se selecciona "Mostrar Todo", mostrar todos los datos
        datos_usuario = oplecturaabril.objects.all()
    else:
        # Filtrar los datos para las regiones seleccionadas
        datos_usuario = oplecturaabril.objects.filter(reg__in=regiones_seleccionadas)     
    
    # Convertir los datos a una lista de diccionarios y crear un DataFrame
    datos_usuario_list = list(datos_usuario.values('desempeño', 'puntaje', 'reg'))
    if not datos_usuario_list:
        return render(request, 'lectura/graficoreg.html', {
            'datos_disponibles': False
        })
    
    df = pd.DataFrame(datos_usuario_list)
    
    # Verificar si las columnas 'desempeño' y 'puntaje' existen
    if 'desempeño' not in df.columns or 'puntaje' not in df.columns:
        return HttpResponse("Error en los datos: columnas 'desempeño' o 'puntaje' no encontradas.")
    
    # Calcular el total de alumnos evaluados
    total_alumnos = df.shape[0]
    
    # Agrupar y contar por categoría de desempeño
    conteo_desempeño = df['desempeño'].value_counts()
    
    # Calcular los porcentajes
    porcentajes = (conteo_desempeño / conteo_desempeño.sum()) * 100
    
    # Calcular el promedio de puntaje
    promedio_puntaje = round(df['puntaje'].mean(), 2)
    
    # Obtener el nombre de la regional o mostrar "Chaco"
    regional = 'Chaco' if mostrar_todo else ', '.join(df['reg'].unique())
    
    # Crear el gráfico de torta
    fig, ax = plt.subplots()
    ax.pie(porcentajes, labels=porcentajes.index, autopct='%1.1f%%', startangle=90) 
    ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    
    # Guardar el gráfico en un objeto BytesIO
    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    
    # Convertir la imagen a base64 para incrustarla en la plantilla
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    # Renderizar la plantilla y pasar el gráfico y el promedio de puntaje
    return render(request, 'lectura/graficoreg.html', {
        'grafico': image_base64,
        'promedio_puntaje': promedio_puntaje,
        'total_alumnos': total_alumnos,
        'regional': regional,
        'datos_disponibles': True
    })

def cargar_grafico_reg(request):    
    return render(request, 'lectura/graficoreg.html', {
        'datos_disponibles': False
    })
