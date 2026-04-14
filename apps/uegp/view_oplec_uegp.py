from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import CreateView, ListView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from apps.oplectura.models import RegAplicador, RegDocporSeccion, RegEvaluacionFluidezLectora
from apps.oplectura.forms import RegDocporSeccionEdicionForm, RegDocporSeccionForm, RegEvaluacionFluidezLectoraForm, FiltroEvaluacionForm, RegAlumnosFluidezLectoraForm, RegEvaluacionFluidezLectoraDirectoresForm
from apps.oplectura.forms import RegAlumnosFluidezLectoraDirectorForm
from apps.oplectura.forms import RegAplicadorporSeccionEdicionForm
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import urlencode
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import connection
from django.db.models import Q

#@cache_control(no_cache=True, must_revalidate=True)
#login_required
def directoresregistrados(request):    
    # consulta para obtener la región
    query2 = """
        SELECT username, apellido, nombres, region_loc, localidad
        FROM cenpe.v_usuarios_oplectura_privados
    """
    
    with connection.cursor() as cursor:
        cursor.execute(query2)
        columns = [col[0] for col in cursor.description]  # Obtener los nombres de columnas
        rows = cursor.fetchall()

    # Convertir las filas en una lista de diccionarios
    directores = [dict(zip(columns, row)) for row in rows]

    return directores if directores else None


# Vista para mostrar los datos en el template
#cache_control(no_cache=True, must_revalidate=True)
#login_required
def mostrar_directores(request):
    # Obtener el username del usuario logueado
    username = request.user.username
    
    # Obtener datos de los directores a partir del username
    directores = directoresregistrados(request)
    
    # Verificar si no hay directores para pasar al template
    if not directores:
        directores = []

    # Renderizar el template y pasar los datos de los directores
    return render(request, 'uegp/directoresregistradosuegp.html', {'directores': directores})
