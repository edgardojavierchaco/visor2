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


def activity_catalogs(modalidad, nivel):
    config = ModalidadNivelCeic.objects.filter(modalidad_id=modalidad, nivel_id=nivel).first() if modalidad and nivel else None
    ceic = NomencladorCeic.objects.filter(pk__in=expandir_rangos(config.rango_ceic) if config else [])
    grados, secciones = Grado_anio.objects.filter(estado=True), Secciones.objects.filter(estado=True)
    if nivel:
        grados = grados.filter(t_niv_grado="Nivel", c_niv_grado=nivel)
        secciones = secciones.filter(t_niv_seccion="Nivel", c_niv_seccion=nivel)
    elif modalidad:
        grados = grados.filter(t_niv_grado="Modalidad", c_niv_grado=modalidad)
        secciones = secciones.filter(t_niv_seccion="Modalidad", c_niv_seccion=modalidad)
    else:
        grados, secciones = grados.none(), secciones.none()
    return ceic.order_by("descripcion"), grados.order_by("nombre_grado_anio"), secciones.order_by("nombre_seccion")
