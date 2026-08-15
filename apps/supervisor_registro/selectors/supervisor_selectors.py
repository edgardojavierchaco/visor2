#selectors/supervisor_selectors.py
from django.shortcuts import get_object_or_404

from ..models import ABMSupervisores, SupervisorRegional


def get_supervisor(supervisor_id):
    return get_object_or_404(
        ABMSupervisores.objects.select_related("usuario"),
        pk=supervisor_id,
    )


def get_supervisor_regional(pk):
    return get_object_or_404(
        SupervisorRegional.objects.select_related("region", "supervisor"),
        pk=pk,
    )


def get_supervisores_by_responsable(responsable):
    return (
        ABMSupervisores.objects
        .filter(
            asignaciones_regionales__region__in=responsable.regiones.all(),
            asignaciones_regionales__activo=True,
            activo=True,
        )
        .select_related("usuario")
        .distinct()
    )
