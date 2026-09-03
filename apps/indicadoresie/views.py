import datetime
import json
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import ListView, TemplateView
from django.db.models import Count, F, Value, Q
from django.db.models.functions import Concat, Coalesce
from django.shortcuts import render
from django.utils import timezone

# Importamos modelos
from .models import (
    SeguimientoSIE2025, SIESegimiento, InformeSGE, 
    FechaActualizacionSGE, UsuarioPerfil
)

# Importamos las funciones de lógica que creamos en el paso anterior
from .views_dash import (
    filtrar_queryset_sge,
    obtener_cargo_usuario,
    resolver_contexto_sge,
)

# =====================================================================
# VISTAS DE SEGUIMIENTO
# =====================================================================

class InicioSGEView(TemplateView):
    template_name = 'indicadoresie/seguimiento/inicio_sge.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sge_context'] = resolver_contexto_sge(self.request)
        context['active_menu'] = 'inicio'
        return context

class SeguimientoSIE2025ListView(ListView):
    """
    Esta vista mantiene la lógica para Agentes específicos, 
    pero ahora reconoce al Administrador por Rol.
    """
    model = SeguimientoSIE2025
    template_name = 'indicadoresie/seguimiento/list_sge.html'

    def get_queryset(self):
        user = self.request.user
        cargo = obtener_cargo_usuario(user)
        
        base_queryset = (
            SeguimientoSIE2025.objects.values(
                'agente', 'region', 'nivel', 'cue', 'anexo', 'grado', 'seccion', 'estado_inscripcion'
            ).annotate(
                cueanexo=Concat(Coalesce(F('cue'), Value('')), Coalesce(F('anexo'), Value(''))),
                total_preinscriptos=Count('cue', filter=Q(estado_inscripcion='preinscripto')),
                total_regulares=Count('cue', filter=Q(estado_inscripcion='regular')),
                total_cue=Count('cue')
            )
        )
        
        # Si es Administrador, ve todo el universo
        if cargo == "Administrador": 
            return base_queryset
        
        # Si no, filtramos por su DNI de agente (lógica original)
        agantes_distintos = SIESegimiento.objects.filter(dni_agente=user.username).values_list('agente', flat=True).distinct()
        return base_queryset.filter(agente__in=list(agantes_distintos))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['seguimientos'] = self.get_queryset()
        # Pasamos el cargo al contexto por las dudas
        context['cargo_usuario'] = obtener_cargo_usuario(self.request.user) 
        context['active_menu'] = 'listado'
        return context


class InformeSGEListView(ListView):
    """
    VISTA PRINCIPAL: aplica el contexto territorial SGE compartido
    y valida el 'lapicito' de edición.
    """
    model = InformeSGE
    template_name = 'indicadoresie/seguimiento/list_sge.html' 

    def get_queryset(self):
        contexto_sge = resolver_contexto_sge(self.request)
        return filtrar_queryset_sge(
            InformeSGE.objects.all(),
            contexto_sge,
            campo_region="regional",
            campo_cueanexo="cueanexo",
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contexto_sge = resolver_contexto_sge(self.request)
        cargo = contexto_sge['cargo']
        
        context['titulo'] = "Informe SGE 2025-2026"
        context['sge_context'] = contexto_sge
        
        # ACA ESTÁ LA MAGIA: Le enviamos el cargo al HTML para que lo imprima y filtre
        context['cargo_usuario'] = cargo
        
        # EL LAPICITO: Solo habilitado si el nombre del rol es exactamente 'Administrador'
        context['is_admin'] = (cargo == "Administrador")
        
        # Fecha de actualización
        obj_fecha = FechaActualizacionSGE.objects.filter(id=1).first()
        context['ultima_fecha'] = obj_fecha.fecha if obj_fecha else None
        
        # Regiones para el selector de filtros (basado en lo que puede ver)
        queryset_usuario = context['object_list']

        def valores_filtro(campo):
            valores = queryset_usuario.order_by().values_list(campo, flat=True).distinct()
            return sorted(
                {str(valor).strip() for valor in valores if valor and str(valor).strip()},
                key=str.casefold,
            )

        context['regiones'] = valores_filtro('regional')
        context['ofertas'] = valores_filtro('tipo_oferta')
        context['ambitos'] = valores_filtro('ambito')
        context['sectores'] = valores_filtro('sector')
        context['active_menu'] = 'listado'
        
        return context

# =====================================================================
# VISTA PARA ACTUALIZAR FECHA (AJAX)
# =====================================================================

@login_required
def actualizar_fecha_sge(request):
    """
    Seguridad reforzada: Valida que el ROL sea Administrador antes de procesar.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Método no permitido.'}, status=405)

    # Verificamos ROL en lugar de CUIL hardcodeado
    cargo = obtener_cargo_usuario(request.user)
    if cargo != "Administrador":
        return JsonResponse({'status': 'error', 'message': 'No tiene permisos de administrador.'}, status=403)

    try:
        data = json.loads(request.body)
        nueva_fecha_str = data.get('fecha')
        if not nueva_fecha_str:
            return JsonResponse({'status': 'error', 'message': 'Fecha no proporcionada.'}, status=400)

        # Convertir string a objeto datetime
        nueva_fecha = timezone.make_aware(
            datetime.datetime.strptime(nueva_fecha_str, '%Y-%m-%dT%H:%M')
        )

        # Actualizar o Crear el registro único (id=1)
        obj, created = FechaActualizacionSGE.objects.update_or_create(
            id=1, 
            defaults={'fecha': nueva_fecha}
        )

        return JsonResponse({'status': 'success', 'message': 'Fecha actualizada correctamente.'})

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

# DASHBOARDS DE PRUEBA (Mantenidos)
def dashboard_prueba(request): return render(request, "indicadoresie/dashboard_prueba.html")
def dashboard_prueba_superv(request): return render(request, "indicadoresie/dashboard_prueba_superv.html")
def dashboard_prueba_func(request): return render(request, "indicadoresie/dashboard_prueba_func.html")
def dashboard_prueba_regional(request): return render(request, "indicadoresie/dashboard_prueba_regional.html")
def dashboard_prueba_fluidez(request): return render(request, "indicadoresie/dashboard_prueba_fluidez_segter.html")
def dashboard_prueba_fluidez_regional(request): return render(request, "indicadoresie/dashboard_prueba_fluidez_segter_reg.html")
def dashboard_prueba_fluidez_func(request): return render(request, "indicadoresie/dashboard_prueba_fluidez_segter_func.html")
def dashboard_prueba_matematica(request): return render(request, "indicadoresie/dashboard_prueba_matematica_quinseg.html")
def dashboard_prueba_matematica_regional(request): return render(request, "indicadoresie/dashboard_prueba_matematica_quinseg_reg.html")
def dashboard_prueba_matematica_func(request): return render(request, "indicadoresie/dashboard_prueba_matematica_quinseg_func.html")
