from ..models import ResponsableRegional



ROLES_ADMIN = {

    "Administrador",

    "Funcionario",

}


def es_admin(user):

    """
    Usuarios con acceso completo.
    """

    if user.is_superuser:

        return True


    return user.nivelacceso in ROLES_ADMIN







def get_responsable(user):

    return (

        ResponsableRegional.objects

        .filter(

            usuario=user,

            activo=True

        )

        .prefetch_related(
            "regiones"
        )

        .first()

    )








def assert_responsable(user):

    obj = get_responsable(user)


    if not obj:

        raise PermissionError(
            "No responsable asignado"
        )


    return obj







def can_access_region(
    responsable,
    region_id
):

    return (

        responsable

        .regiones

        .filter(
            pk=region_id
        )

        .exists()

    )








def get_regiones_usuario(user):

    """
    Devuelve las regiones permitidas.

    Admin:
        None = todas

    Regional:
        lista de IDs
    """



    if es_admin(user):

        return None





    responsable = get_responsable(user)



    if not responsable:

        return []





    return list(

        responsable

        .regiones

        .values_list(
            "id",
            flat=True
        )

    )








def puede_operar_region(
    user,
    region_id
):


    regiones = get_regiones_usuario(
        user
    )



    # acceso total

    if regiones is None:

        return True





    return region_id in regiones







def puede_ver_supervisores(user):


    if es_admin(user):

        return True




    return (

        ResponsableRegional.objects

        .filter(

            usuario=user,

            activo=True

        )

        .exists()

    )