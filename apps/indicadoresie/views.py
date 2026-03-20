from django.views.generic import ListView
from django.db.models import Count, F, Value, Q
from django.db.models.functions import Concat, Coalesce
from .models import SeguimientoSIE2025, SIESegimiento, InformeSGE
from django.shortcuts import render

class SeguimientoSIE2025ListView(ListView):
    model = SeguimientoSIE2025
    template_name = 'indicadoresie/seguimiento/list_sge.html'

    def get_queryset(self):
        agente_user = self.request.user.username

        # Obtener los agentes únicos asociados al usuario desde SIESegimiento
        agantes_distintos = SIESegimiento.objects.filter(dni_agente=agente_user).values_list('agente', flat=True).distinct()

        # Filtrar los registros de SeguimientoSIE2025 (Tabla de alumnos original)
        queryset = (
            SeguimientoSIE2025.objects
            .filter(agente__in=list(agantes_distintos))
            .values(
                'agente',
                'region',
                'nivel',
                'cue',
                'anexo',
                'grado',
                'seccion',
                'estado_inscripcion'
                # Se eliminaron sge_2026 e inscriptos_2026 para evitar el FieldError
            )
            .annotate(
                cueanexo=Concat(
                    Coalesce(F('cue'), Value('')), 
                    Coalesce(F('anexo'), Value(''))
                ),
                total_preinscriptos=Count('cue', filter=Q(estado_inscripcion='preinscripto')),
                total_regulares=Count('cue', filter=Q(estado_inscripcion='regular')),
                total_cue=Count('cue')
            )
        )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['seguimientos'] = self.get_queryset()
        return context

# --- Vistas de Dashboard (Sin cambios) ---

def dashboard_prueba(request):
    return render(request, "indicadoresie/dashboard_prueba.html")

def dashboard_prueba_superv(request):
    return render(request, "indicadoresie/dashboard_prueba_superv.html")

def dashboard_prueba_func(request):
    return render(request, "indicadoresie/dashboard_prueba_func.html")

def dashboard_prueba_regional(request):
    return render(request, "indicadoresie/dashboard_prueba_regional.html")

def dashboard_prueba_fluidez(request):
    return render(request, "indicadoresie/dashboard_prueba_fluidez_segter.html")

def dashboard_prueba_fluidez_regional(request):
    return render(request, "indicadoresie/dashboard_prueba_fluidez_segter_reg.html")

def dashboard_prueba_fluidez_func(request):
    return render(request, "indicadoresie/dashboard_prueba_fluidez_segter_func.html")

def dashboard_prueba_matematica(request):
    return render(request, "indicadoresie/dashboard_prueba_matematica_quinseg.html")

def dashboard_prueba_matematica_regional(request):
    return render(request, "indicadoresie/dashboard_prueba_matematica_quinseg_reg.html")

def dashboard_prueba_matematica_func(request):
    return render(request, "indicadoresie/dashboard_prueba_matematica_quinseg_func.html")

# --- Vista para el nuevo Modelo InformeSGE (Nueva implementación corregida) ---

class InformeSGEListView(ListView):
    model = InformeSGE
    template_name = 'indicadoresie/seguimiento/list_sge.html' 

    def get_queryset(self):
        # 1. Identificamos al usuario
        agente_user = self.request.user.username
        print(f"Usuario autenticado: {agente_user}")
        
        # 2. Devolvemos SOLO las filas de InformeSGE que le corresponden a ese usuario
        return InformeSGE.objects.filter(agente=agente_user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = "Informe SGE 2025-2026"
        
        # 4. Extraemos dinámicamente las regiones de los datos que este usuario PUEDE ver
        queryset_usuario = self.get_queryset()
        regiones_crudas = queryset_usuario.values_list('regional', flat=True).distinct()
        
        # Limpiamos los vacíos y pasamos la variable 'regiones' al HTML
        context['regiones'] = sorted([r for r in list(regiones_crudas) if r and r.strip()])
        
        return context