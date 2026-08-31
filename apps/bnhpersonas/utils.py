#apps/bnhpersonas/utils.py
from .domain.access import (
    get_user_cueanexos,
    get_user_cuil,
    normalize_cuil,
    user_has_cueanexo_access,
)


def get_ofertas_usuario(user):
    """
    Devuelve las ofertas educativas a las que
    tiene acceso el usuario.
    """

    return get_user_cueanexos(user)