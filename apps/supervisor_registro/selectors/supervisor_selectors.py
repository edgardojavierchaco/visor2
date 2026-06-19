from ..models import (
    ABMSupervisores,
    SupervisorRegional
)


def get_supervisor(supervisor_id):
    return ABMSupervisores.objects.select_related("usuario").get(pk=supervisor_id)


def get_supervisor_regional(pk):
    return SupervisorRegional.objects.select_related("region").get(pk=pk)


def get_supervisores_by_responsable(responsable):
    return ABMSupervisores.objects.filter(
        supervisorregional__region__in=responsable.regiones.all(),
        supervisorregional__activo=True
    ).distinct()