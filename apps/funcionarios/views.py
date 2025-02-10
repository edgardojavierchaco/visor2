from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import CreateView, ListView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import urlencode
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import connection
from django.db.models import Q

@cache_control(no_cache=True, must_revalidate=True)
@login_required
def DepFuncionarioPortada(request):
    """
    Renderiza la plantilla de la portada de evaluación.

    Args:
        request: El objeto de solicitud HTTP.

    Returns:
        HttpResponse: La respuesta renderizada con la plantilla de portada.
    """
    
    return render(request, 'funcionarios/portadafuncionario.html')