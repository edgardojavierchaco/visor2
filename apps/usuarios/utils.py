# apps/usuarios/utils.py

def get_user_rol(user):
    if hasattr(user, 'perfil') and user.perfil.rol:
        return user.perfil.rol.nombre
    return None


def get_user_categoria(user):
    if hasattr(user, 'perfil') and user.perfil.rol:
        return user.perfil.rol.categoria_acceso
    return None


