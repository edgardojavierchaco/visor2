def get_rol(user):
    return getattr(getattr(user, "perfil", None), "rol", None)


def get_categoria(user):
    rol = get_rol(user)
    return getattr(rol, "categoria_acceso", None)