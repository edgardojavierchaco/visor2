#services/supervisor_service.py
from django.db import IntegrityError, transaction

from ..models import ABMSupervisores


def build(obj):
    return {
        "id": obj.id,
        "cuil": obj.usuario.username,
        "apellido": obj.usuario.apellido,
        "nombres": obj.usuario.nombres,
        "email": obj.email,
        "telefono": obj.telefono,
        "activo": obj.activo,
    }


@transaction.atomic
def create(usuario, telefono=None, email=None):
    try:
        return ABMSupervisores.objects.create(
            usuario=usuario,
            telefono=telefono or None,
            email=email or None,
        )
    except IntegrityError:
        raise


@transaction.atomic
def update(obj, telefono=None, email=None):
    obj.telefono = telefono or None
    obj.email = email or None
    obj.save(update_fields=["telefono", "email", "fecha_modificacion"])
    return obj


@transaction.atomic
def delete(obj):
    obj.activo = False
    obj.save(update_fields=["activo", "fecha_modificacion"])
    return obj


@transaction.atomic
def toggle(obj):
    obj.activo = not obj.activo
    obj.save(update_fields=["activo", "fecha_modificacion"])
    return obj
