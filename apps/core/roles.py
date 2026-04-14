def user_roles(user):
    """
    Devuelve todos los roles del usuario como set.
    """

    if not user.is_authenticated:
        return set()

    return set(user.groups.values_list("name", flat=True))


def is_director(user):
    return "Director" in user_roles(user)


def is_evaluacion(user):
    return "Evaluacion" in user_roles(user)


def is_aplicador(user):
    return "Aplicador" in user_roles(user)