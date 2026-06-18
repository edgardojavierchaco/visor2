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


def create(usuario, telefono=None, email=None):
    return ABMSupervisores.objects.create(
        usuario=usuario,
        telefono=telefono,
        email=email
    )


def update(obj, telefono=None, email=None):
    if telefono is not None:
        obj.telefono = telefono
    if email is not None:
        obj.email = email
    obj.save()
    return obj


def delete(obj):
    obj.activo = False
    obj.save(update_fields=["activo"])
    return obj


def toggle(obj):
    obj.activo = not obj.activo
    obj.save(update_fields=["activo"])
    return obj