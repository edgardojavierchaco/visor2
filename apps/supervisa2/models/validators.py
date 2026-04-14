import re
from django.core.exceptions import ValidationError
from django.core.validators import validate_email


def validate_email_strict(value):
    try:
        validate_email(value)
    except:
        raise ValidationError("Email inválido.")


def validar_cuil_afip(cuil: str) -> bool:
    cuil = ''.join(filter(str.isdigit, cuil))

    if len(cuil) != 11:
        return False

    pesos = [5,4,3,2,7,6,5,4,3,2]

    total = sum(int(cuil[i]) * pesos[i] for i in range(10))

    resto = total % 11
    digito = 11 - resto

    if digito == 11:
        digito = 0
    elif digito == 10:
        digito = 9

    return digito == int(cuil[-1])


def validate_cuil(value):
    if not value.isdigit():
        raise ValidationError("El CUIL debe contener solo números.")

    if len(value) != 11:
        raise ValidationError("El CUIL debe tener 11 dígitos.")

    if not validar_cuil_afip(value):
        raise ValidationError("CUIL inválido según AFIP.")


def validate_text_upper(value):
    if value != value.upper():
        raise ValidationError("Debe estar en MAYÚSCULAS.")

    if re.search(r"\d", value):
        raise ValidationError("No puede contener números.")


def validate_phone(value):
    if value and not re.match(r"^[0-9\s\-\+]{6,20}$", value):
        raise ValidationError("Teléfono inválido.")


def validate_fechas(fecha_desde, fecha_hasta):
    if fecha_hasta and fecha_hasta < fecha_desde:
        raise ValidationError("La fecha hasta no puede ser menor a fecha desde.")