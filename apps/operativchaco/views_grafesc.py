from urllib import response
from django.http import JsonResponse
from .models import EscuelasSecundarias, ExamenLenguaAlumno, ExamenMatematicaAlumno, AlumnosSecundariaDiagnostico, RegistroAsistenciaLengua, RegistroAsistenciaMatematica
from django.views.decorators.http import require_GET
from django.db.models import Sum

def datos_lengua_por_region(request):
    region = request.GET.get('region')

    if region == "Todas":
        escuelas = EscuelasSecundarias.objects.all()
        exlengua= ExamenLenguaAlumno.objects.all()        
        alumnos= AlumnosSecundariaDiagnostico.objects.all()
        ausentes=RegistroAsistenciaLengua.objects.all()
    else:
        escuelas = EscuelasSecundarias.objects.filter(region_loc=region)
        exlengua= ExamenLenguaAlumno.objects.filter(region=region)        
        alumnos= AlumnosSecundariaDiagnostico.objects.filter(region=region)
        ausentes=RegistroAsistenciaLengua.objects.filter(region=region)

    total = escuelas.count()
    pendientes = escuelas.filter(lengua='PENDIENTE').count()
    cargadas = total - pendientes
    
    total_examenes = exlengua.count()    
    total_alumnos = alumnos.count()
    total_pendientes= total_alumnos- total_examenes
    total_ausentes = ausentes.aggregate(suma=Sum('total_registros'))['suma'] or 0
    total_sin_calificar= total_alumnos - (total_examenes + total_ausentes)
    

    return JsonResponse({
        'labels': ['Pendientes', 'Cargadas','Examenes Cargados', 'Examenes Pendientes', 'Total Examenes', 'Ausentes', 'Sin Calificar'],
        'data': [pendientes, cargadas, total_examenes, total_pendientes, total_alumnos, total_ausentes, total_sin_calificar],
    }) 


def datos_matematica_por_region(request):
    region = request.GET.get('region')

    if region == "Todas":
        escuelas = EscuelasSecundarias.objects.all()
        exmatematica= ExamenMatematicaAlumno.objects.all()
        alumnos= AlumnosSecundariaDiagnostico.objects.all()
        ausentes=RegistroAsistenciaMatematica.objects.all()
    else:
        escuelas = EscuelasSecundarias.objects.filter(region_loc=region)
        exmatematica= ExamenMatematicaAlumno.objects.filter(egion=region)
        alumnos= AlumnosSecundariaDiagnostico.objects.filter(region=region)
        ausentes=RegistroAsistenciaMatematica.objects.filter(region=region)

    total = escuelas.count()
    pendientes = escuelas.filter(matematica='PENDIENTE').count()
    cargadas = total - pendientes
    
    total_examenes = exmatematica.count()
    total_alumnos = alumnos.count()
    total_pendientes= total_alumnos- total_examenes
    total_ausentes = ausentes.aggregate(suma=Sum('total_registros'))['suma'] or 0
    total_sin_calificar= total_alumnos - (total_examenes + total_ausentes)

    return JsonResponse({
        'labels': ['Pendientes', 'Cargadas', 'Examenes Cargados', 'Examenes Pendientes', 'Total Examenes', 'Ausentes', 'Sin Calificar'],
        'data': [pendientes, cargadas, total_examenes, total_pendientes, total_alumnos, total_ausentes, total_sin_calificar],
    }) 


@require_GET
def escuelas_pendientes_lengua(request):
    region = request.GET.get('region')
    
    if region == "Todas":
        escuelas = EscuelasSecundarias.objects.filter(lengua='PENDIENTE')
    else:
        escuelas = EscuelasSecundarias.objects.filter(region_loc=region, lengua='PENDIENTE')

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
def escuelas_pendientes_matematica(request):
    region = request.GET.get('region')

    if region == "Todas":
        escuelas = EscuelasSecundarias.objects.filter(matematica='PENDIENTE')
    else:
        escuelas = EscuelasSecundarias.objects.filter(region_loc=region, matematica='PENDIENTE')

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
