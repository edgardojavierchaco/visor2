from django.shortcuts import render
from .models import TotalSecundarias, TotalPrimarias

def dashboard_secundarias(request):
    totales = TotalSecundarias.objects.first()  
    return render(request, 'operativchaco/dashboard/secundarias.html', {'totales': totales})

def dashboard_primarias_segundo(request):
    totales = TotalPrimarias.objects.first()  
    return render(request, 'operativchaco/dashboard/primarias_segundo.html', {'totales': totales})

def dashboard_primarias_segundo_regional(request):
    totales = TotalPrimarias.objects.first()  
    return render(request, 'operativchaco/dashboard/primarias_segundo_regional.html', {'totales': totales})

def dashboard_primarias_segundo_func(request):
    totales = TotalPrimarias.objects.first()  
    return render(request, 'operativchaco/dashboard/primarias_segundo_func.html', {'totales': totales})

def dashboard_primarias_tercero(request):
    totales = TotalPrimarias.objects.first()  
    return render(request, 'operativchaco/dashboard/primarias_tercero.html', {'totales': totales})

def dashboard_secundarias_superv(request):
    totales = TotalSecundarias.objects.first()  
    return render(request, 'operativchaco/dashboard/secundarias_superv.html', {'totales': totales})

def dashboard_resultados_final(request):    
    return render(request, 'operativchaco/dashboard/dashboard_reportes_final.html')

def dashboard_resultados_final_primaria(request):    
    return render(request, 'operativchaco/dashboard/dashboard_reportes_final_primaria.html')

def dashboard_resultados_final_primaria_regional(request):    
    return render(request, 'operativchaco/dashboard/dashboard_reportes_final_primaria_reg.html')

def dashboard_resultados_final_primaria_func(request):    
    return render(request, 'operativchaco/dashboard/dashboard_reportes_final_primaria_func.html')

# Resultados Evaluación Matemática Quinto Primaria y Segundo Secundaria
def dashboard_primarias_quinto(request):
    totalesprim = TotalPrimarias.objects.first()  
    totalessec = TotalSecundarias.objects.first()
    return render(request, 'operativchaco/dashboard/primarias_quinto.html', {'totalesprim': totalesprim, 'totalessec': totalessec})

def dashboard_resultados_final_primaria_quinto(request):    
    return render(request, 'operativchaco/dashboard/dashboard_reportes_final_primaria_quinto.html')

def dashboard_resultados_final_primaria_quinto_regional(request):    
    return render(request, 'operativchaco/dashboard/dashboard_reportes_final_primaria_quinto_reg.html')

def dashboard_resultados_final_primaria_quinto_func(request):    
    return render(request, 'operativchaco/dashboard/dashboard_reportes_final_primaria_quinto_func.html')

def dashboard_primarias_quinto_regional(request):
    totalesprim = TotalPrimarias.objects.first()  
    totalessec = TotalSecundarias.objects.first()
    return render(request, 'operativchaco/dashboard/primarias_quinto_regional.html', {'totalesprim': totalesprim, 'totalessec': totalessec})

def dashboard_primarias_quinto_func(request):
    totalesprim = TotalPrimarias.objects.first()  
    totalessec = TotalSecundarias.objects.first()
    return render(request, 'operativchaco/dashboard/primarias_quinto_func.html', {'totalesprim': totalesprim, 'totalessec': totalessec})



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


def dashboard_matematica_quinto_segundo(request):
    totalesprim = TotalPrimarias.objects.first()  
    totalessec = TotalSecundarias.objects.first()
    return render(request, 'operativchaco/dashboard/matematica_quinto_segundo.html', {'totalesprim': totalesprim, 'totalessec': totalessec})