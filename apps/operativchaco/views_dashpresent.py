from django.shortcuts import render
from .models import TotalSecundarias

def dashboard_secundarias(request):
    totales = TotalSecundarias.objects.first()  
    return render(request, 'operativchaco/dashboard/secundarias.html', {'totales': totales})


def dashboard_secundarias_superv(request):
    totales = TotalSecundarias.objects.first()  
    return render(request, 'operativchaco/dashboard/secundarias_superv.html', {'totales': totales})

def dashboard_resultados_final(request):    
    return render(request, 'operativchaco/dashboard/dashboard_reportes_final.html')

def dashboard_resultados_final_superv(request):    
    return render(request, 'operativchaco/dashboard/dashboard_reportes_final_superv.html')

def dashboard_secundarias_func(request):
    totales = TotalSecundarias.objects.first()  
    return render(request, 'operativchaco/dashboard/secundarias_func.html', {'totales': totales})

def dashboard_resultados_final_func(request):    
    return render(request, 'operativchaco/dashboard/dashboard_reportes_final_func.html')

def dashboard_secundarias_regional(request):
    totales = TotalSecundarias.objects.first()  
    return render(request, 'operativchaco/dashboard/secundarias_regional.html', {'totales': totales})

def dashboard_resultados_final_regional(request):    
    return render(request, 'operativchaco/dashboard/dashboard_reportes_final_regional.html')