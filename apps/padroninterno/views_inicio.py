from django.shortcuts import render

from .permisos import padron_interno_admin_o_gestor_required


@padron_interno_admin_o_gestor_required
def inicio_view(request):
    """
    Inicio del módulo Padrón Interno.
    Solo Administrador o Gestor pueden ingresar.
    """
    return render(request, 'padroninterno/inicio.html')