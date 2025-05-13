from django.views.generic import ListView
from django.db.models import Count, F, Value, Q
from django.db.models.functions import Concat, Coalesce
from .models import SeguimientoSIE2025, SIESegimiento
from django.shortcuts import render

class SeguimientoSIE2025ListView(ListView):
    model = SeguimientoSIE2025
    template_name = 'indicadoresie/seguimiento/list.html'

    def get_queryset(self):
        agente_user = self.request.user.username

        # Obtener los agentes únicos asociados al usuario
        agentes_distintos = SIESegimiento.objects.filter(dni_agente=agente_user).values_list('agente', flat=True).distinct()

        # Filtrar los registros de SeguimientoSIE2025
        queryset = (
            SeguimientoSIE2025.objects
            .filter(agente__in=list(agentes_distintos))
            .values(
                'agente',
                'region',
                'nivel',
                'cue',
                'anexo',
                'grado',
                'seccion',
                'estado_inscripcion'
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
        """
        Agregar el queryset al contexto para usarlo en el template.
        """
        context = super().get_context_data(**kwargs)
        context['seguimientos'] = self.get_queryset()
        return context

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

