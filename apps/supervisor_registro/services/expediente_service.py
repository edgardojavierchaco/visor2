from ..models import *

def clean_date(value):
    if not value:
        return None
    return value


# =========================
# GETTERS (centralizados)
# =========================

def get_situacion(pk):
    return SupervisorSituacionRevista.objects.get(pk=pk)


def get_nivel(pk):
    return SupervisorRegionalNivel.objects.get(pk=pk)


def get_oferta(pk):
    return SupervisorRegionalOferta.objects.get(pk=pk)


# =========================
# SITUACION
# =========================

def add_situacion(supervisor, data):
    return SupervisorSituacionRevista.objects.create(
        supervisor=supervisor,
        situacion_revista_id=data["situacion_id"],
        fecha_desde=data["fecha_desde"],
        fecha_hasta=data.get("fecha_hasta"),
        activo=True
    )


def update_situacion(obj, data):

    obj.situacion_revista_id = data["situacion_id"]

    obj.fecha_desde = clean_date(data.get("fecha_desde"))
    obj.fecha_hasta = clean_date(data.get("fecha_hasta"))

    obj.save()
    return obj


def delete_situacion(obj):
    obj.activo = False
    obj.save(update_fields=["activo"])
    return obj


# =========================
# REGIONAL
# =========================

def add_regional(supervisor, region, responsable):
    obj, created = SupervisorRegional.objects.get_or_create(
        supervisor=supervisor,
        region=region,
        defaults={
            "responsable_alta": responsable,
            "activo": True
        }
    )
    
    if not created and not obj.activo:

        obj.activo = True
        obj.responsable_alta = responsable
        obj.save(
            update_fields=[
                "activo",
                "responsable_alta"
            ]
        )
        
    return obj


def delete_regional(obj):
    obj.activo = False
    obj.save(update_fields=["activo"])
    return obj


# =========================
# NIVEL
# =========================

def add_nivel(sr, nivel_id):
    obj, created = SupervisorRegionalNivel.objects.get_or_create(
        supervisor_regional=sr,
        nivel_id=nivel_id,
        defaults={"activo": True}
    )    
    
    if not created and not obj.activo:

        obj.activo = True
        obj.save(
            update_fields=["activo"]
        )
        
    return obj


def delete_nivel(obj):
    obj.activo = False
    obj.save(update_fields=["activo"])
    return obj


def update_nivel(obj, data):

    obj.nivel_id = data["nivel_id"]

    obj.save(
        update_fields=[
            "nivel"
        ]
    )

    return obj


# =========================
# OFERTA
# =========================

def add_oferta(sr, data):
    obj, created = SupervisorRegionalOferta.objects.get_or_create(
        supervisor_regional=sr,
        cueanexo=data["cueanexo"],
        oferta=data["oferta"],
        defaults={
            "nom_est": data.get("nom_est"),
            "acronimo": data.get("acronimo"),
            "activo": True
        }
    )
    
    if not created and not obj.activo:

        obj.activo = True
        obj.nom_est = data.get("nom_est")
        obj.acronimo = data.get("acronimo")

        obj.save()
    
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
    obj.save()
    return obj