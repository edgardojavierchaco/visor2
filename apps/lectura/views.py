import pandas as pd
import plotly.express as px
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.http import HttpResponse
from django.views.generic import CreateView, ListView, UpdateView, DeleteView
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
        user = self.request.user
        username = user.get_username()
        return super().get_queryset().filter(cueanexo=username)

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

@login_required
def mostrar_grafico(request):
    cueanexo_usuario = request.user.username
    datos_usuario = oplecturaabril.objects.filter(cueanexo=cueanexo_usuario)

    datos_usuario_list = list(datos_usuario.values('desempeño', 'puntaje', 'escuela'))
    if not datos_usuario_list:
        return HttpResponse("No hay datos disponibles para esta región")

    df = pd.DataFrame(datos_usuario_list)

    if 'desempeño' not in df.columns or 'puntaje' not in df.columns:
        return HttpResponse("Error en los datos: columnas 'desempeño' o 'puntaje' no encontradas.")

    total_alumnos = df.shape[0]
    conteo_desempeño = df['desempeño'].value_counts()
    porcentajes = (conteo_desempeño / conteo_desempeño.sum()) * 100
    promedio_puntaje = round(df['puntaje'].mean(), 2)
    escuela = df['escuela'].iloc[0]

    fig = px.pie(names=conteo_desempeño.index, values=porcentajes, title="Desempeño de Alumnos", width=800, height=600)
    graph_html = fig.to_html(full_html=False)

    return render(request, 'lectura/grafico.html', {
        'grafico': graph_html,
        'promedio_puntaje': promedio_puntaje,
        'total_alumnos': total_alumnos,
        'escuela': escuela,
    })

@login_required
def mostrar_grafico_reg(request):
    regiones_seleccionadas = request.GET.getlist('region')
    mostrar_todo = '0' in regiones_seleccionadas

    if mostrar_todo:
        datos_usuario = oplecturaabril.objects.all()
    else:
        datos_usuario = oplecturaabril.objects.filter(reg__in=regiones_seleccionadas)

    datos_usuario_list = list(datos_usuario.values('desempeño', 'puntaje', 'reg'))
    if not datos_usuario_list:
        return render(request, 'lectura/graficoreg.html', {'datos_disponibles': False})

    df = pd.DataFrame(datos_usuario_list)

    if 'desempeño' not in df.columns or 'puntaje' not in df.columns:
        return HttpResponse("Error en los datos: columnas 'desempeño' o 'puntaje' no encontradas.")

    total_alumnos = df.shape[0]
    conteo_desempeño = df['desempeño'].value_counts()
    porcentajes = (conteo_desempeño / conteo_desempeño.sum()) * 100
    promedio_puntaje = round(df['puntaje'].mean(), 2)
    regional = 'Chaco' if mostrar_todo else ', '.join(df['reg'].unique())

    fig = px.pie(names=conteo_desempeño.index, values=porcentajes, title="Desempeño de Alumnos por Región", width=800, height=600)
    graph_html = fig.to_html(full_html=False)

    return render(request, 'lectura/graficoreg.html', {
        'grafico': graph_html,
        'promedio_puntaje': promedio_puntaje,
        'total_alumnos': total_alumnos,
        'regional': regional,
        'datos_disponibles': True
    })

@login_required
def cargar_grafico_reg(request):
    return render(request, 'lectura/graficoreg.html', {'datos_disponibles': False})
