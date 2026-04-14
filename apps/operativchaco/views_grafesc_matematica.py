from urllib import response
from django.http import JsonResponse
from .models import EscuelasPrimariasMatematica, EscuelasSecundariasMatematica, ExamenMatematicaQuintoGrado, ExamenMatematicaSegundoAnio, AlumnosPrimariaQuinto, AlumnosSegundoSecundaria, RegistroAsistenciaMatematicaQuinto, RegistroAsistenciaMatematicaSegundoAnio
from django.views.decorators.http import require_GET
from django.db.models import Sum

def datos_quinto_por_region(request):
    region = request.GET.get('region')

    if region == "Todas":
        escuelas = EscuelasPrimariasMatematica.objects.all()
        exquinto= ExamenMatematicaQuintoGrado.objects.all()        
        alumnos= AlumnosPrimariaQuinto.objects.all()
        ausentes=RegistroAsistenciaMatematicaQuinto.objects.all()
    else:
        escuelas = EscuelasPrimariasMatematica.objects.filter(region_loc=region)
        exquinto= ExamenMatematicaQuintoGrado.objects.filter(region=region)        
        alumnos= AlumnosPrimariaQuinto.objects.filter(region=region)
        ausentes=RegistroAsistenciaMatematicaQuinto.objects.filter(region=region)

    total = escuelas.count()
    pendientes = escuelas.filter(quinto='PENDIENTE').count()
    cargadas = total - pendientes
    
    total_examenes = exquinto.count()    
    total_alumnos = alumnos.count()
    total_pendientes= total_alumnos - total_examenes
    total_ausentes = ausentes.aggregate(suma=Sum('ausentes'))['suma'] or 0
    total_sin_calificar= total_alumnos - (total_examenes + total_ausentes)
    
    print(total_alumnos)
    return JsonResponse({
        'labels': ['Pendientes', 'Cargadas','Examenes Cargados', 'Examenes Pendientes', 'Total Examenes', 'Ausentes', 'Sin Calificar'],
        'data': [pendientes, cargadas, total_examenes, total_pendientes, total_alumnos, total_ausentes, total_sin_calificar],
    }) 


def datos_segundosec_por_region(request):
    region = request.GET.get('region')

    if region == "Todas":
        escuelas = EscuelasSecundariasMatematica.objects.all()
        extercero= ExamenMatematicaSegundoAnio.objects.all()
        alumnos= AlumnosSegundoSecundaria.objects.all()
        ausentes=RegistroAsistenciaMatematicaSegundoAnio.objects.all()
    else:
        escuelas = EscuelasSecundariasMatematica.objects.filter(region_loc=region)
        extercero= ExamenMatematicaSegundoAnio.objects.filter(region=region)
        alumnos= AlumnosSegundoSecundaria.objects.filter(region=region)
        ausentes=RegistroAsistenciaMatematicaSegundoAnio.objects.filter(region=region)

    total = escuelas.count()
    pendientes = escuelas.filter(segundo='PENDIENTE').count()
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
def escuelas_pendientes_segundosec(request):
    region = request.GET.get('region')
    
    if region == "Todas":
        escuelas = EscuelasSecundariasMatematica.objects.filter(segundo='PENDIENTE')
    else:
        escuelas = EscuelasSecundariasMatematica.objects.filter(region_loc=region, segundo='PENDIENTE')

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
def escuelas_pendientes_quinto(request):
    region = request.GET.get('region')

    if region == "Todas":
        escuelas = EscuelasPrimariasMatematica.objects.filter(tercero='PENDIENTE')
    else:
        escuelas = EscuelasPrimariasMatematica.objects.filter(region_loc=region, quinto='PENDIENTE')

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
