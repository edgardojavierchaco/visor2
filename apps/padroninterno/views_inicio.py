from django.shortcuts import render

from .permisos import padron_interno_admin_o_gestor_required
from .views_fecha import get_contexto_fecha_padron


# Vista de entrada del modulo: arma solo el contexto comun y renderiza el inicio.
@padron_interno_admin_o_gestor_required
def inicio_view(request):
    """
    Inicio del módulo Padrón Interno.
    Solo Administrador o Gestor pueden ingresar.
    """
    context = {}
    # Agrega fecha de actualizacion y bandera de administrador al template.
    context.update(get_contexto_fecha_padron(request))
    return render(request, 'padroninterno/inicio.html', context)
