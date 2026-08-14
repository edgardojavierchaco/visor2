#services/expediente_service.py
from ..models import (
    SupervisorRegional,
    SupervisorRegionalNivel,
    SupervisorRegionalOferta,
    SupervisorSituacionRevista,
)


def clean_date(value):
    return value or None


def get_situacion(pk):
    return SupervisorSituacionRevista.objects.select_related("supervisor", "situacion_revista").get(pk=pk)


def get_nivel(pk):
    return SupervisorRegionalNivel.objects.select_related("supervisor_regional", "nivel").get(pk=pk)


def get_oferta(pk):
    return SupervisorRegionalOferta.objects.select_related("supervisor_regional").get(pk=pk)


def add_situacion(supervisor, data):
    return SupervisorSituacionRevista.objects.create(
        supervisor=supervisor,
        situacion_revista_id=data["situacion_id"],
        fecha_desde=data["fecha_desde"],
        fecha_hasta=clean_date(data.get("fecha_hasta")),
        activo=True,
    )


def update_situacion(obj, data):
    obj.situacion_revista_id = data["situacion_id"]
    obj.fecha_desde = data["fecha_desde"]
    obj.fecha_hasta = clean_date(data.get("fecha_hasta"))
    obj.save(update_fields=["situacion_revista", "fecha_desde", "fecha_hasta"])
    return obj


def delete_situacion(obj):
    obj.activo = False
    obj.save(update_fields=["activo"])
    return obj


def add_regional(supervisor, region, responsable=None):
    obj, created = SupervisorRegional.objects.get_or_create(
        supervisor=supervisor,
        region=region,
        defaults={"responsable_alta": responsable, "activo": True},
    )
    if not created and not obj.activo:
        obj.activo = True
        obj.responsable_alta = responsable
        obj.save(update_fields=["activo", "responsable_alta"])
    return obj


def delete_regional(obj):
    obj.activo = False
    obj.save(update_fields=["activo"])
    return obj


def add_nivel(sr, nivel_id):
    obj, created = SupervisorRegionalNivel.objects.get_or_create(
        supervisor_regional=sr,
        nivel_id=nivel_id,
        defaults={"activo": True},
    )
    if not created and not obj.activo:
        obj.activo = True
        obj.save(update_fields=["activo"])
    return obj


def delete_nivel(obj):
    obj.activo = False
    obj.save(update_fields=["activo"])
    return obj


def update_nivel(obj, data):
    obj.nivel_id = data["nivel_id"]
    obj.save(update_fields=["nivel"])
    return obj


def add_oferta(sr, data):
    obj, created = SupervisorRegionalOferta.objects.get_or_create(
        supervisor_regional=sr,
        cueanexo=data["cueanexo"],
        oferta=data["oferta"],
        defaults={
            "nom_est": data.get("nom_est") or "",
            "acronimo": data.get("acronimo") or None,
            "activo": True,
        },
    )
    if not created and not obj.activo:
        obj.activo = True
        obj.nom_est = data.get("nom_est") or obj.nom_est
        obj.acronimo = data.get("acronimo") or None
        obj.save(update_fields=["activo", "nom_est", "acronimo"])
    return obj


def delete_oferta(obj):
    obj.activo = False
    obj.save(update_fields=["activo"])
    return obj


def update_oferta(obj, data):
    obj.cueanexo = data["cueanexo"]
    obj.nom_est = data["nom_est"]
    obj.oferta = data["oferta"]
    obj.acronimo = data.get("acronimo") or None
    obj.save(update_fields=["cueanexo", "nom_est", "oferta", "acronimo"])
    return obj
