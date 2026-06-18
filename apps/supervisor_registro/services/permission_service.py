from ..models import ResponsableRegional


def get_responsable(user):
    return ResponsableRegional.objects.filter(
        usuario=user,
        activo=True
    ).prefetch_related("regiones").first()


def assert_responsable(user):
    obj = get_responsable(user)
    if not obj:
        raise PermissionError("No responsable asignado")
    return obj


def can_access_region(responsable, region_id):
    return responsable.regiones.filter(pk=region_id).exists()


def get_regiones_usuario(user):

    try:
        responsable = ResponsableRegional.objects.get(
            usuario=user,
            activo=True
        )

        return responsable.regiones.values_list(
            "id",
            flat=True
        )

    except ResponsableRegional.DoesNotExist:
        return []


def puede_operar_region(user, region_id):

    return region_id in get_regiones_usuario(user)