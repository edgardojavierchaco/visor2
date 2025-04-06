from django.shortcuts import render
from .models import TotalSecundarias

def dashboard_secundarias(request):
    totales = TotalSecundarias.objects.first()  
    return render(request, 'operativchaco/dashboard/secundarias.html', {'totales': totales})
