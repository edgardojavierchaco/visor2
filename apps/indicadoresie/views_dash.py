from django.views.generic import TemplateView
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

# IMPORTAMOS LOS MODELOS NECESARIOS
from .models import SIESegimiento, InformeSGE

# 1. FUNCIÓN AUXILIAR PARA FILTRAR POR USUARIO
def get_user_agents(request):
    """Devuelve la lista de agentes permitidos para el usuario logueado."""
    agente_user = request.user.username
    usuarios_exentos = ['24024606', '26521492', '225685230', '28122730', '43146847']
    
    if agente_user in usuarios_exentos:
        return SIESegimiento.objects.values_list('agente', flat=True).distinct()
    return SIESegimiento.objects.filter(dni_agente=agente_user).values_list('agente', flat=True).distinct()

# 2. LIMPIADOR INTELIGENTE DE REGIONES
def normalizar_region(region_raw):
    """Limpia los nombres sucios de la base de datos y los unifica."""
    if not region_raw or str(region_raw).strip() == '' or str(region_raw).lower() == 'nan':
        return None  # Elimina los "Sin Regional"
        
    r = str(region_raw).strip().upper()
    
    # Diccionario de equivalencias (corrige los errores de carga)
    mapa = {
        'REGION 1': 'R.E. 1', 'REGION 2': 'R.E. 2', 'REGION 3': 'R.E. 3',
        'REGION 4-A': 'R.E. 4-A', 'REGION 4 A': 'R.E. 4-A',
        'REGION 4-B': 'R.E. 4-B', 'REGION 4 B': 'R.E. 4-B',
        'REGION 5': 'R.E. 5', 'REGION 6': 'R.E. 6', 'REGION 7': 'R.E. 7',
        
        # Aquí corregimos el problema que mencionaste con la región 8
        'REGION 8': 'R.E. 8-A',  # Asumimos que los que cargaron "8" a secas van a 8-A (puedes cambiarlo si prefieres)
        '8': 'R.E. 8-A',
        'REGION 8-A': 'R.E. 8-A', 'REGION 8 A': 'R.E. 8-A',
        'REGION 8-B': 'R.E. 8-B', 'REGION 8 B': 'R.E. 8-B',
        
        'REGION 9': 'R.E. 9',
        
        # Correcciones para región 10
        'REGION 10': 'R.E. 10-A', 
        'REGION 10-A': 'R.E. 10-A', 'REGION 10 A': 'R.E. 10-A',
        'REGION 10-B': 'R.E. 10-B', 'REGION 10 B': 'R.E. 10-B',
        'REGION 10-C': 'R.E. 10-C', 'REGION 10 C': 'R.E. 10-C',
        
        'SUBSEDE 1 A': 'SUB. R.E. 1-A', 'SUBSEDE 1-A': 'SUB. R.E. 1-A',
        'SUBSEDE 1 B': 'SUB. R.E. 1-B', 'SUBSEDE 1-B': 'SUB. R.E. 1-B',
        'SUBSEDE 2': 'SUB. R.E. 2', 'SUBSEDE 3': 'SUB. R.E. 3', 'SUBSEDE 5': 'SUB. R.E. 5'
    }
    
    if r in mapa:
        return mapa[r]
        
    # Reglas generales por si aparece un texto nuevo
    if r.startswith('REGION '): return r.replace('REGION ', 'R.E. ')
    if r.startswith('SUBSEDE '): return r.replace('SUBSEDE ', 'SUB. R.E. ')
    
    return r

# 3. VISTA PARA CARGAR EL DASHBOARD (HTML y Filtros)
@method_decorator(login_required, name='dispatch')
class DashboardSeguimientoSIE2025View(TemplateView):
    template_name = 'indicadoresie/seguimiento/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Filtramos por el usuario
        agentes = get_user_agents(self.request)
        regiones_raw = InformeSGE.objects.filter(agente__in=agentes).values_list('regional', flat=True).distinct()
        
        # Limpiamos y normalizamos las regiones para el selector desplegable
        regiones_limpias = set()
        for r in regiones_raw:
            norm = normalizar_region(r)
            if norm: # Si no es None (vacío), lo agregamos
                regiones_limpias.add(norm)
        
        context['regions'] = sorted(list(regiones_limpias))
        return context

# 4. API PARA EL GRÁFICO POR REGIONALES
@login_required
def seguimiento_sie_json(request):     
    agentes = get_user_agents(request)
    escuelas = InformeSGE.objects.filter(agente__in=agentes)
        
    datos_agrupados = {}

    for esc in escuelas:
        # Pasamos la región cruda por el filtro limpiador
        region = normalizar_region(esc.regional)
        
        # Saltamos los "Sin Regional"
        if not region: 
            continue

        if region not in datos_agrupados:
            datos_agrupados[region] = {
                "region": region,
                "total_ant": 0,           # Meta: Insc 25
                "total_ciclo_actual": 0,  # Insc 26
                "total_act": 0            # Progreso: SGE 26
            }

        try: datos_agrupados[region]["total_ant"] += int(float(esc.inscriptos_2025))
        except (ValueError, TypeError): pass 

        try: datos_agrupados[region]["total_ciclo_actual"] += int(float(esc.inscriptos_2026))
        except (ValueError, TypeError): pass

        try: datos_agrupados[region]["total_act"] += int(float(esc.sge_2026))
        except (ValueError, TypeError): pass

    chart_data = []
    for data in datos_agrupados.values():
        meta_25 = data["total_ant"]
        progreso_26 = data["total_act"]

        pct_avance = round((progreso_26 / meta_25) * 100, 2) if meta_25 > 0 else 0
        pct_display = pct_avance if pct_avance <= 100 else 100
        pct_brecha = 100 - pct_display

        data["regulares"] = pct_display
        data["preinscriptos"] = pct_brecha
        chart_data.append(data)

    chart_data.sort(key=lambda x: x["region"])
    return JsonResponse({"data": chart_data}, safe=False)

# 5. API PARA EL GRÁFICO POR NIVELES
@login_required
def seguimiento_sie_niveles_json(request):
    requested_region = request.GET.get('region')
    if not requested_region:
        return JsonResponse({"error": "Debe proporcionar una regional."}, status=400)
    
    agentes = get_user_agents(request)
    escuelas = InformeSGE.objects.filter(agente__in=agentes)
    
    datos_agrupados = {}

    for esc in escuelas:
        # Aquí está la clave: Limpiamos la región de la BD antes de compararla
        # con la región limpia que envió el Dashboard por la URL.
        region_norm = normalizar_region(esc.regional)
        if region_norm != requested_region:
            continue

        nivel = getattr(esc, 'nivel', getattr(esc, 'tipo_oferta', "Sin Nivel"))
        if not nivel or str(nivel).strip() == '': 
            nivel = "Sin Nivel"

        if nivel not in datos_agrupados:
            datos_agrupados[nivel] = {
                "nivel": nivel,
                "total_ant": 0,
                "total_ciclo_actual": 0,
                "total_act": 0
            }

        try: datos_agrupados[nivel]["total_ant"] += int(float(esc.inscriptos_2025))
        except (ValueError, TypeError): pass

        try: datos_agrupados[nivel]["total_ciclo_actual"] += int(float(esc.inscriptos_2026))
        except (ValueError, TypeError): pass

        try: datos_agrupados[nivel]["total_act"] += int(float(esc.sge_2026))
        except (ValueError, TypeError): pass

    chart_data = []
    for data in datos_agrupados.values():
        meta_25 = data["total_ant"]
        progreso_26 = data["total_act"]

        pct_avance = round((progreso_26 / meta_25) * 100, 2) if meta_25 > 0 else 0
        pct_display = pct_avance if pct_avance <= 100 else 100
        pct_brecha = 100 - pct_display

        data["regulares"] = pct_display
        data["preinscriptos"] = pct_brecha
        chart_data.append(data)

    chart_data.sort(key=lambda x: x["nivel"])
    return JsonResponse({"niveles": chart_data}, safe=False)