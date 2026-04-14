# -----------------------------------
# 🧠 CONTEXTO DE USUARIO (PRO)
# -----------------------------------

class UserContext:
    def __init__(self, user):
        self.user = user
        self._data = None

    @property
    def data(self):
        if self._data:
            return self._data

        if not self.user.is_authenticated:
            self._data = {"rol": None, "categoria": None}
            return self._data

        perfil = getattr(self.user, 'perfil', None)

        if not perfil or not perfil.rol:
            self._data = {"rol": None, "categoria": None}
        else:
            self._data = {
                "rol": perfil.rol.nombre,
                "categoria": perfil.rol.categoria_acceso
            }

        return self._data

    @property
    def rol(self):
        return self.data["rol"]

    @property
    def categoria(self):
        return self.data["categoria"]

    def has_rol(self, roles):
        return self.rol in roles if self.rol else False

    def has_categoria(self, categorias):
        return self.categoria in categorias if self.categoria else False


# -----------------------------------
# 🔹 FACTORY
# -----------------------------------

def get_user_context(user):
    if hasattr(user, '_ctx'):
        return user._ctx

    user._ctx = UserContext(user)
    return user._ctx


def get_user_data(user):
    return get_user_context(user).data


def get_user_rol(user):
    return get_user_context(user).rol


def get_user_categoria(user):
    return get_user_context(user).categoria


def user_has_rol(user, roles):
    return get_user_context(user).has_rol(roles)


def user_has_categoria(user, categorias):
    return get_user_context(user).has_categoria(categorias)


# -----------------------------------
# 🎯 REDIRECCIÓN
# -----------------------------------

def get_redirect_url(user):
    ctx = get_user_context(user)

    if not ctx.rol:
        return None

    if ctx.rol in ['Administrador', 'Gestor']:
        return 'archivos:portada_gestor'

    if ctx.rol in ['Ministro', 'Subsecretario', 'Director General']:
        return 'funcionario:portada_func'

    if ctx.rol == 'Director':
        return 'directores:institucional'

    if ctx.categoria == 'regional':
        return 'oplectura:portada_regional'

    if ctx.categoria in ['nivel', 'modalidad']:
        return 'funcionario:portada_func'

    if ctx.categoria == 'propio':
        return 'directores:institucional'
    
    if ctx.rol == 'Supervisor':
        return 'archivos:portada_gestor'

    return None