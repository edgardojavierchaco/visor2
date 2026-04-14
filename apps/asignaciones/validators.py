# validators.py

from django.core.exceptions import ValidationError


def validar_asignacion(supervisor, escuela):

    regiones = set(supervisor.regiones.values_list("nombre", flat=True))
    ofertas = set(supervisor.niveles_modalidad.values_list("nombre", flat=True))

    # región
    if escuela.region_loc not in regiones:
        raise ValidationError("Escuela fuera de la región del supervisor")

    # oferta (ANTES nivel_modalidad ❌)
    if escuela.oferta not in ofertas:
        raise ValidationError("Escuela fuera de la modalidad permitida")