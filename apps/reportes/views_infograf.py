from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

# Vista para mostrar infografía matrícula, cargos y horas
def infografiaview(request):
    return render(request, 'reportes/infografia.html')


def infografiaview2(request):
    return render(request, 'reportes/infografia2.html')