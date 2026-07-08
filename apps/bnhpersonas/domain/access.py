# apps/bnhpersonas/domain/access.py
from django.db.models import Func, F, Value, CharField
from django.db.models.functions import Cast
from apps.consultasge.models_padron import CapaUnicaOfertas
import re


def get_user_cueanexos(user):
    """
    Devuelve los cueanexos habilitados para el usuario.
    """

    if not user or not user.is_authenticated:
        return CapaUnicaOfertas.objects.none()

    usuario_limpio = re.sub(r"\D", "", user.username)

    return (
        CapaUnicaOfertas.objects
        .annotate(
            cuit_limpio=Func(
                F("resploc_cuitcuil"),
                Value(r"\D"),
                Value(""),
                Value("g"),
                function="REGEXP_REPLACE"
            ),
            cueanexo_str=Cast(
                "cueanexo",
                output_field=CharField()
            )
        )
        .filter(cuit_limpio=usuario_limpio)
        .values_list("cueanexo_str", flat=True)
        .distinct()
    )


def user_has_cueanexo_access(user, cueanexo: str) -> bool:
    """
    Verifica si el usuario tiene acceso a un cueanexo.
    """

    if not user:
        return False

    cueanexos = set(get_user_cueanexos(user))

    return str(cueanexo) in cueanexos