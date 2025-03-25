from django.urls import path
from django.views.generic import TemplateView
from django.db.models import Count, Q, Sum, F
from django.http import JsonResponse
from .models import SeguimientoSIE2025, SIESegimiento
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator


@method_decorator(login_required, name='dispatch')
class DashboardSeguimientoSIE2025View(TemplateView):
    template_name = 'indicadoresie/seguimiento/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Lista de usuarios exentos de filtrado
        usuarios_exentos = ['24024606', '26521492', '225685230', '28122730', '43146847']  # Agrega los usuarios que no deben ser filtrados
        
        agente_user = self.request.user.username
        
        # Si el usuario está en la lista de usuarios exentos, omitir el filtrado por agente
        if agente_user in usuarios_exentos:
            agentes_distintos = SIESegimiento.objects.values_list('agente', flat=True).distinct()  
        else:
            agentes_distintos = SIESegimiento.objects.filter(dni_agente=agente_user).values_list('agente', flat=True).distinct()
        
        # Filtrando las regiones según los agentes disponibles
        regiones = (
            SeguimientoSIE2025.objects
            .filter(agente__in=agentes_distintos)
            .values_list('region', flat=True)
            .distinct()
        )
        
        context['regions'] = list(regiones)
        return context


@login_required
def seguimiento_sie_json(request):     
    
    agente_user = request.user.username
    
    # Lista de usuarios exentos de filtrado
    usuarios_exentos = ['24024606', '26521492', '225685230','28122730', '43146847']  # Agrega los usuarios que no deben ser filtrados
        
    agente_user = request.user.username
        
    # Si el usuario está en la lista de usuarios exentos, omitir el filtrado por agente
    if agente_user in usuarios_exentos:
        agentes_distintos = SIESegimiento.objects.values_list('agente', flat=True).distinct()  
    else:
        agentes_distintos = SIESegimiento.objects.filter(dni_agente=agente_user).values_list('agente', flat=True).distinct()
        

    
    data = (
        SeguimientoSIE2025.objects
        .filter(agente__in=agentes_distintos)
        .values('region')
        .annotate(
            total_preinscriptos=Count('id', filter=Q(estado_inscripcion='Preinscripto')),
            total_regulares=Count('id', filter=Q(estado_inscripcion='Regular')),
            total_ciclo_actual=F('total_preinscriptos')+F('total_regulares'),
            total_cue=Count('id')
        )
    )
    
    data_ant = (
        SIESegimiento.objects
        .filter(agente__in=agentes_distintos)
        .values('region')
        .annotate(    
            total_reg=Sum('sieant'))
    )
    
    print('dataant', data_ant)
    
    # Crear un diccionario con la región como clave y total_reg como valor
    data_ant_dict = {item['region']: item['total_reg'] for item in data_ant}

    chart_data = [
        {
            'region': item['region'],
            'preinscriptos': round((item['total_preinscriptos'] / item['total_cue']) * 100, 2) if item['total_cue'] else 0,
            'regulares': round((item['total_regulares'] / item['total_cue']) * 100, 2) if item['total_cue'] else 0,
            'total_ant': data_ant_dict.get(item['region'], 0),
            'total_ciclo_actual': item['total_ciclo_actual'],
            'total_act': item['total_regulares']
        }
        for item in data
    ]
    print(chart_data)
    
    return JsonResponse({"data": chart_data}, safe=False)

@login_required
def seguimiento_sie_niveles_json(request):
    region = request.GET.get('region')
    if not region:
        return JsonResponse({"error": "Debe proporcionar una regional."}, status=400)
    
    data = (
        SeguimientoSIE2025.objects
        .filter(region=region)
        .values('nivel')
        .annotate(
            total_preinscriptos=Count('id', filter=Q(estado_inscripcion='Preinscripto')),
            total_regulares=Count('id', filter=Q(estado_inscripcion='Regular')),
            total_ciclo_actual=F('total_preinscriptos')+F('total_regulares'),
            total_cue=Count('id')
        )
    )
    
    data_ant = (
        SIESegimiento.objects
        .filter(region=region)
        .values('nivel')
        .annotate(    
            total_reg=Sum('sieant'))
    )
    
    print('dataant', data_ant)
    
    # Crear un diccionario con la región como clave y total_reg como valor
    data_ant_dict = {item['nivel']: item['total_reg'] for item in data_ant}
    print('ver',data_ant_dict)

    chart_data = [
        {
            'nivel': item['nivel'],
            'preinscriptos': round((item['total_preinscriptos'] / item['total_cue']) * 100, 2) if item['total_cue'] else 0,
            'regulares': round((item['total_regulares'] / item['total_cue']) * 100, 2) if item['total_cue'] else 0,
            'total_ant': data_ant_dict.get(item['nivel'], 0),
            'total_ciclo_actual': item['total_ciclo_actual'],
            'total_act': item['total_regulares']
        }
        for item in data
    ]

    return JsonResponse({"niveles": chart_data}, safe=False)    