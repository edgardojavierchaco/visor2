from django.utils import timezone
from django.shortcuts import render
from functools import wraps
from apps.cuenta_regresiva.models import FechaEvento 

def habilitado_despues_de_evento(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        ahora = timezone.now()
        evento = FechaEvento.objects.filter(nombre='Relevamiento').first()

        if evento and ahora < evento.fecha_evento:
            return render(request, 'operativchaco/cuentas_regresivas/esperando.html', {'evento': evento})

        return view_func(request, *args, **kwargs)

    return _wrapped_view

