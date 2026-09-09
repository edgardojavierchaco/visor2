from django.core.exceptions import ValidationError
from ..models import ModalidadNivelCeic, NomencladorCeic, Grado_anio, Secciones


def expandir_rangos(texto):
    result = set()
    try:
        for piece in (texto or "").split(","):
            if not piece.strip():
                continue
            bounds = [int(x.strip()) for x in piece.split("-")]
            if len(bounds) == 1:
                bounds *= 2
            if len(bounds) != 2 or not 0 <= bounds[0] <= bounds[1] <= 100000 or bounds[1] - bounds[0] > 2000:
                raise ValueError
            result.update(range(bounds[0], bounds[1] + 1))
    except (ValueError, TypeError):
        raise ValidationError("Configuración CEIC inválida; solicite su corrección al administrador.")
    return sorted(result)


def available_levels(modalidad):
    from ..models import NivelServicio, ModalidadNivel
    if not modalidad:
        return NivelServicio.objects.none()
    return NivelServicio.objects.filter(pk__in=ModalidadNivel.objects.filter(
        modalidad_id=modalidad).values("nivel_id")).order_by("c_nivel")


def activity_catalogs(modalidad, nivel, grado=None):
    """Los CSV definen modalidad+nivel, no una asignación individual sección/grado.

    Las secciones del mismo par se habilitan tras verificar el grado elegido.
    No se equiparan códigos de nivel y códigos de modalidad.
    """
    empty = (NomencladorCeic.objects.none(), Grado_anio.objects.none(), Secciones.objects.none())
    if not modalidad or not nivel or not available_levels(modalidad).filter(pk=nivel).exists():
        return empty
    config = ModalidadNivelCeic.objects.filter(modalidad_id=modalidad, nivel_id=nivel).first()
    ceic = NomencladorCeic.objects.filter(pk__in=expandir_rangos(config.rango_ceic) if config else [])
    grados = Grado_anio.objects.filter(estado=True, c_modalidad=modalidad, c_niv_grado=nivel, t_niv_grado="Nivel")
    secciones = Secciones.objects.none()
    if grado and grados.filter(pk=grado).exists():
        secciones = Secciones.objects.filter(estado=True, c_modalidad=modalidad, c_niv_seccion=nivel, t_niv_seccion="Nivel")
    return ceic.order_by("descripcion"), grados.order_by("c_grado_anio"), secciones.order_by("c_seccion")
