#apps/bnhpersonas/helpers.py
from .domain.access import get_user_cueanexos


def get_cueanexos_usuario(user):
    return get_user_cueanexos(user)