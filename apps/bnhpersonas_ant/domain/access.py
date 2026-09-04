# apps/bnhpersonas/domain/access.py

import re
from django.db.models import Func, F, Value, CharField
from django.db.models.functions import Cast
from apps.consultasge.models_padron import CapaUnicaOfertas

def normalize_cuil(value):
    """
    Normaliza un CUIL/CUIT eliminando todo carácter
    que no sea numérico.

    Ejemplos:
        20-12345678-3 -> 20123456783
        20 12345678 3 -> 20123456783
        20.12345678.3 -> 20123456783
    """

    if value is None:
        return ""

    return re.sub(r"\D", "", str(value))

def get_user_cuil(user):
    """
    Obtiene el CUIL normalizado del usuario autenticado.
    """

    if not user or not user.is_authenticated:
        return ""

    return normalize_cuil(user.username)
    
def get_user_cueanexos(user):
    """
    Devuelve un QuerySet con los CUEANEXO a los que
    tiene acceso el usuario.

    La relación de autorización se obtiene desde
    CapaUnicaOfertas mediante resploc_cuitcuil.
    """

    usuario_limpio = get_user_cuil(user)

    if not usuario_limpio:
        return CapaUnicaOfertas.objects.none().values_list(
            "cueanexo",
            flat=True
        )

    return (
        CapaUnicaOfertas.objects
        .annotate(
            cuil_limpio=Func(
                F("resploc_cuitcuil"),
                Value(r"\D"),
                Value(""),
                Value("g"),
                function="REGEXP_REPLACE",
            ),
            cueanexo_str=Cast(
                "cueanexo",
                output_field=CharField(),
            ),
        )
        .filter(
            cuil_limpio=usuario_limpio
        )
        .values_list(
            "cueanexo_str",
            flat=True
        )
        .distinct()
    )


def user_has_cueanexo_access(user, cueanexo):
    """
    Verifica si el usuario tiene autorización
    sobre un CUEANEXO determinado.
    """

    if not user or not user.is_authenticated:
        return False

    if cueanexo is None:
        return False

    return get_user_cueanexos(user).filter(
        cueanexo=str(cueanexo)
    ).exists()