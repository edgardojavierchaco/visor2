from urllib import response
from django.http import JsonResponse
from .models import EscuelasPrimarias, ExamenFluidezSegundo, ExamenFluidezTercero, AlumnosPrimariaFluidez, RegistroAsistenciaFluidezSegundo, RegistroAsistenciaFluidezTercero
from django.views.decorators.http import require_GET
from django.db.models import Sum

def datos_segundo_por_region(request):
    region = request.GET.get('region')

    if region == "Todas":
        escuelas = EscuelasPrimarias.objects.all()
        exsegundo= ExamenFluidezSegundo.objects.all()        
        alumnos= AlumnosPrimariaFluidez.objects.all()
        ausentes=RegistroAsistenciaFluidezSegundo.objects.all()
    else:
        escuelas = EscuelasPrimarias.objects.filter(region_loc=region)
        exsegundo= ExamenFluidezSegundo.objects.filter(region=region)        
        alumnos= AlumnosPrimariaFluidez.objects.filter(region=region)
        ausentes=RegistroAsistenciaFluidezSegundo.objects.filter(region=region)

    total = escuelas.count()
    pendientes = escuelas.filter(segundo='PENDIENTE').count()
    cargadas = total - pendientes
    
    total_examenes = exsegundo.count()    
    total_alumnos = alumnos.count()
    total_pendientes= total_alumnos - total_examenes
    total_ausentes = ausentes.aggregate(suma=Sum('ausentes'))['suma'] or 0
    total_sin_calificar= total_alumnos - (total_examenes + total_ausentes)
    
    print(total_alumnos)
    return JsonResponse({
        'labels': ['Pendientes', 'Cargadas','Examenes Cargados', 'Examenes Pendientes', 'Total Examenes', 'Ausentes', 'Sin Calificar'],
        'data': [pendientes, cargadas, total_examenes, total_pendientes, total_alumnos, total_ausentes, total_sin_calificar],
    }) 


def datos_tercero_por_region(request):
    region = request.GET.get('region')

    if region == "Todas":
        escuelas = EscuelasPrimarias.objects.all()
        extercero= ExamenFluidezTercero.objects.all()
        alumnos= AlumnosPrimariaFluidez.objects.all()
        ausentes=RegistroAsistenciaFluidezSegundo.objects.all()
    else:
        escuelas = EscuelasPrimarias.objects.filter(region_loc=region)
        extercero= ExamenFluidezTercero.objects.filter(region=region)
        alumnos= AlumnosPrimariaFluidez.objects.filter(region=region)
        ausentes=RegistroAsistenciaFluidezTercero.objects.filter(region=region)

    total = escuelas.count()
    pendientes = escuelas.filter(tercero='PENDIENTE').count()
    cargadas = total - pendientes
    
    total_examenes = extercero.count()
    total_alumnos = alumnos.count()
    total_pendientes= total_alumnos- total_examenes
    total_ausentes = ausentes.aggregate(suma=Sum('ausentes'))['suma'] or 0
    total_sin_calificar= total_alumnos - (total_examenes + total_ausentes)

    return JsonResponse({
        'labels': ['Pendientes', 'Cargadas', 'Examenes Cargados', 'Examenes Pendientes', 'Total Examenes', 'Ausentes', 'Sin Calificar'],
        'data': [pendientes, cargadas, total_examenes, total_pendientes, total_alumnos, total_ausentes, total_sin_calificar],
    }) 


@require_GET
def escuelas_pendientes_segundo(request):
    region = request.GET.get('region')
    
    if region == "Todas":
        escuelas = EscuelasPrimarias.objects.filter(segundo='PENDIENTE')
    else:
        escuelas = EscuelasPrimarias.objects.filter(region_loc=region, segundo='PENDIENTE')

    data = [
        {
            'cue': e.cueanexo,
            'nombre': e.nom_est,
            'region': e.region_loc,
            'estado': 'Pendiente'
        }
        for e in escuelas
    ]

    response_data = {
        'total': escuelas.count(),
        'region': region,
        'escuelas': data
    }
    print(response_data)
    return JsonResponse(response_data)


@require_GET
def escuelas_pendientes_tercero(request):
    region = request.GET.get('region')

    if region == "Todas":
        escuelas = EscuelasPrimarias.objects.filter(tercero='PENDIENTE')
    else:
        escuelas = EscuelasPrimarias.objects.filter(region_loc=region, tercero='PENDIENTE')

    data = [
        {
            'cue': e.cueanexo,
            'nombre': e.nom_est,
            'region': e.region_loc,
            'estado': 'Pendiente'
        }
        for e in escuelas
    ]    
    
    response_data={
        'total': escuelas.count(),
        'region': region,
        'escuelas': data
    }
    
    print(response_data)
    return JsonResponse(response_data)
