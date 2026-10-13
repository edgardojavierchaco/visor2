from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import ListView, TemplateView
from django.db.models import Count, F, Value, Q
from django.db.models.functions import Concat, Coalesce, Trim
from django.shortcuts import render

# Importamos modelos
from .models import (
    SeguimientoSIE2025, SIESegimiento, InformeSGE, 
    FechaActualizacionComparativaSgeRa, UsuarioPerfil
)

# Importamos las funciones de lógica que creamos en el paso anterior
from .views_dash import (
    completar_indicadores_sge_2026,
    filtrar_queryset_sge,
    obtener_cargo_usuario,
    resolver_contexto_sge,
)

TIPOS_OFERTA_LISTADO_SGE = {
    "Inicial - Común",
    "Primario - Común",
    "Secundario - Común",
    "Primario - Adultos",
    "Secundario - Adultos",
    "Inicial - Especial",
    "Primario - Especial",
}


def _tipo_oferta_listado_desde_oferta_supervisor(oferta):
    texto = " ".join(str(oferta or "").strip().split()).casefold()
    if not texto:
        return ""

    if texto.startswith("común -"):
        modalidad = "Común"
    elif texto.startswith("adultos -"):
        modalidad = "Adultos"
    elif texto.startswith("especial -"):
        modalidad = "Especial"
    else:
        return ""

    if (
        "jardín de infantes" in texto
        or "jardín maternal" in texto
        or "nivel inicial" in texto
    ):
        nivel = "Inicial"
    elif "primaria" in texto or "nivel primario" in texto:
        nivel = "Primario"
    elif "secundaria" in texto:
        nivel = "Secundario"
    else:
        return ""

    tipo_oferta = f"{nivel} - {modalidad}"
    return tipo_oferta if tipo_oferta in TIPOS_OFERTA_LISTADO_SGE else ""


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
    y muestra la fecha compartida con Comparativa en modo solo lectura.
    """
    model = InformeSGE
    template_name = 'indicadoresie/seguimiento/list_sge.html' 

    def get_queryset(self):
        contexto_sge = resolver_contexto_sge(self.request)
        queryset = filtrar_queryset_sge(
            InformeSGE.objects.using('sge_nacion').all(),
            contexto_sge,
            campo_region="regional",
            campo_cueanexo="cueanexo",
        )

        if contexto_sge["cargo"] != "Supervisor":
            return queryset

        filtro_ofertas = Q()
        tiene_ofertas_permitidas = False
        for opcion in contexto_sge.get("cueanexo_opciones") or []:
            cueanexo = str(opcion.get("cueanexo") or "").strip()
            tipos_oferta = sorted({
                tipo_oferta
                for tipo_oferta in (
                    _tipo_oferta_listado_desde_oferta_supervisor(oferta)
                    for oferta in opcion.get("ofertas", [])
                )
                if tipo_oferta
            })
            if not cueanexo or not tipos_oferta:
                continue
            tiene_ofertas_permitidas = True
            filtro_ofertas |= Q(
                cueanexo=cueanexo,
                tipo_oferta_normalizada__in=tipos_oferta,
            )

        if not tiene_ofertas_permitidas:
            return queryset.none()

        return queryset.annotate(
            tipo_oferta_normalizada=Trim("tipo_oferta")
        ).filter(filtro_ofertas)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contexto_sge = resolver_contexto_sge(self.request)
        cargo = contexto_sge['cargo']
        
        context['titulo'] = "Informe SGE 2025-2026"
        context['sge_context'] = contexto_sge
        
        # ACA ESTÁ LA MAGIA: Le enviamos el cargo al HTML para que lo imprima y filtre
        context['cargo_usuario'] = cargo
        
        # Rol de administrador disponible para el contexto de la pantalla
        context['is_admin'] = (cargo == "Administrador")
        
        # Fecha compartida con Comparativa; lectura mediante el mismo router.
        obj_fecha = FechaActualizacionComparativaSgeRa.objects.filter(id=1).first()
        context['ultima_fecha'] = obj_fecha.fecha if obj_fecha else None
        
        # Autorizar primero; filtros y tabla comparten los valores enriquecidos.
        queryset_usuario = context['object_list']
        registros = completar_indicadores_sge_2026(queryset_usuario)

        def valores_filtro(campo):
            valores = (getattr(registro, campo) for registro in registros)
            return sorted(
                {str(valor).strip() for valor in valores if valor and str(valor).strip()},
                key=str.casefold,
            )

        context['regiones'] = valores_filtro('regional')
        context['ofertas'] = valores_filtro('tipo_oferta')
        context['ambitos'] = valores_filtro('ambito')
        context['sectores'] = valores_filtro('sector')
        context['object_list'] = registros
        context_object_name = self.get_context_object_name(queryset_usuario)
        if context_object_name:
            context[context_object_name] = registros
        context['active_menu'] = 'listado'
        
        return context

# =====================================================================
# ENDPOINT OBSOLETO DE FECHA (COMPATIBILIDAD)
# =====================================================================

@login_required
def actualizar_fecha_sge(request):
    """La fecha del Listado se administra exclusivamente desde Comparativa."""
    return JsonResponse(
        {'status': 'error', 'message': 'Endpoint obsoleto. La fecha se actualiza desde Comparativa RA-SGE.'},
        status=410,
    )

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
