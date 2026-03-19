# apps/usuarios/services.py

# -----------------------------------
# 🧠 OBTENER DATOS DEL USUARIO
# -----------------------------------

def get_user_data(user):
    if not user.is_authenticated:
        return {"rol": None, "categoria": None}

    perfil = getattr(user, 'perfil', None)

    if not perfil or not perfil.rol:
        return {"rol": None, "categoria": None}

    return {
        "rol": perfil.rol.nombre,
        "categoria": perfil.rol.categoria_acceso
    }


# -----------------------------------
# 🔹 HELPERS
# -----------------------------------

def get_user_rol(user):
    return get_user_data(user)["rol"]


def get_user_categoria(user):
    return get_user_data(user)["categoria"]


def user_has_rol(user, roles):
    rol = get_user_rol(user)
    return rol in roles if rol else False


def user_has_categoria(user, categorias):
    categoria = get_user_categoria(user)
    return categoria in categorias if categoria else False


# -----------------------------------
# 🎯 REDIRECCIÓN CENTRALIZADA
# -----------------------------------

def get_redirect_url(user):
    data = get_user_data(user)
    rol = data["rol"]
    categoria = data["categoria"]

    if not rol:
        return None

    # PRIORIDAD: ROL
    if rol in ['Administrador', 'Gestor']:
        return 'archivos:portada_gestor'

    elif rol in ['Ministro', 'Subsecretario', 'Director General']:
        return 'funcionario:portada_func'

    elif rol == 'Director':
        return 'directores:institucional'

    # FALLBACK: CATEGORÍA
    elif categoria == 'regional':
        return 'oplectura:portada_regional'

    elif categoria == 'nivel':
        return 'funcionario:portada_func'

    elif categoria == 'propio':
        return 'directores:institucional'

    return None