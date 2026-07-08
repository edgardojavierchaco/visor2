import re

from django.core.exceptions import ValidationError
from django.core.validators import validate_email


# ==========================================================
# CUEANEXO
# ==========================================================

def validate_cueanexo(value):
    """
    Valida un CUEANEXO.
    """

    if not value:

        raise ValidationError(
            "El CUEANEXO es obligatorio."
        )

    value = str(value).strip()

    if len(value) != 9:

        raise ValidationError(
            "El CUEANEXO debe tener exactamente 9 dígitos."
        )

    if not value.isdigit():

        raise ValidationError(
            "El CUEANEXO sólo puede contener números."
        )


# ==========================================================
# CUI
# ==========================================================

def validate_cui(value):

    if not value:

        return

    value = str(value).strip()

    if not value.isdigit():

        raise ValidationError(
            "El CUI debe contener únicamente números."
        )


# ==========================================================
# CUIT
# ==========================================================

def validate_cuit(value):

    if not value:

        return

    value = value.replace("-", "").strip()

    if len(value) != 11:

        raise ValidationError(
            "El CUIT debe tener 11 dígitos."
        )

    if not value.isdigit():

        raise ValidationError(
            "El CUIT sólo puede contener números."
        )


# ==========================================================
# EMAIL
# ==========================================================

def validate_email_estricto(value):

    if not value:

        return

    try:

        validate_email(value)

    except ValidationError:

        raise ValidationError(
            "Correo electrónico inválido."
        )


# ==========================================================
# TELÉFONO
# ==========================================================

def validate_telefono(value):

    if not value:

        return

    patron = r"^[0-9+\-\(\)\s]+$"

    if not re.match(
        patron,
        value,
    ):

        raise ValidationError(
            "Número telefónico inválido."
        )


# ==========================================================
# PORCENTAJE
# ==========================================================

def validate_porcentaje(value):

    if value is None:

        return

    if value < 0 or value > 100:

        raise ValidationError(
            "El porcentaje debe estar entre 0 y 100."
        )


# ==========================================================
# CRITICIDAD
# ==========================================================

def validate_criticidad(value):

    allowed = [

        "BAJA",

        "MEDIA",

        "ALTA",

        "CRITICA",

    ]

    if value not in allowed:

        raise ValidationError(
            "Nivel de criticidad inválido."
        )


# ==========================================================
# ESTADO INTERVENCIÓN
# ==========================================================

def validate_estado_intervencion(value):

    allowed = [

        "PENDIENTE",

        "PROGRAMADA",

        "EN_EJECUCION",

        "PAUSADA",

        "FINALIZADA",

        "CANCELADA",

    ]

    if value not in allowed:

        raise ValidationError(
            "Estado de intervención inválido."
        )


# ==========================================================
# COSTO
# ==========================================================

def validate_costo(value):

    if value is None:

        return

    if value < 0:

        raise ValidationError(
            "El costo no puede ser negativo."
        )


# ==========================================================
# TEXTO
# ==========================================================

def validate_texto_no_vacio(value):

    if value is None:

        return

    if not str(value).strip():

        raise ValidationError(
            "Este campo no puede estar vacío."
        )


# ==========================================================
# NOMBRE
# ==========================================================

def validate_nombre(value):

    if not value:

        raise ValidationError(
            "Debe ingresar un nombre todo en mayúsculas."
        )

    if len(value.strip()) < 3:

        raise ValidationError(
            "Debe contener al menos 3 caracteres."
        )


# ==========================================================
# ARCHIVOS
# ==========================================================

def validate_extension_documento(filename):

    permitidos = (

        ".pdf",

        ".doc",

        ".docx",

        ".xls",

        ".xlsx",

        ".jpg",

        ".jpeg",

        ".png",

        ".zip",

    )

    nombre = filename.lower()

    if not nombre.endswith(permitidos):

        raise ValidationError(
            "Tipo de archivo no permitido."
        )


# ==========================================================
# TAMAÑO DE ARCHIVO
# ==========================================================

def validate_filesize(file):

    limite = 20 * 1024 * 1024  # 20 MB

    if file.size > limite:

        raise ValidationError(
            "El archivo supera el límite de 20 MB."
        )


# ==========================================================
# FECHAS
# ==========================================================

def validate_rango_fechas(inicio, fin):

    if inicio and fin:

        if inicio > fin:

            raise ValidationError(
                "La fecha de inicio no puede ser posterior a la fecha de fin."
            )