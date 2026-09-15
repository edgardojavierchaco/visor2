from django.core.exceptions import ValidationError

from ..models import (
    ModalidadNivelCeic,
    NomencladorCeic,
    Grado_anio,
    Secciones,
)


# ============================================================
# CEIC PARA PERSONAL NO DOCENTE
# ============================================================

NO_DOCENTE_C_NIV_DESDE = 1023
NO_DOCENTE_C_NIV_HASTA = 1025


def ceic_no_docente():
    """
    Devuelve exclusivamente los cargos CEIC habilitados
    para personal NO DOCENTE.

    La regla jurisdiccional establece que deben mostrarse
    los registros de nomenclador_ceic cuyo c_niv esté
    comprendido entre 1023 y 1025 inclusive.
    """

    return (
        NomencladorCeic.objects
        .filter(
            c_niv__gte=NO_DOCENTE_C_NIV_DESDE,
            c_niv__lte=NO_DOCENTE_C_NIV_HASTA,
        )
        .order_by(
            "c_niv",
            "descripcion",
        )
    )


# ============================================================
# EXPANSIÓN DE RANGOS CEIC
# ============================================================

def expandir_rangos(texto):
    result = set()

    try:
        for piece in (texto or "").split(","):

            if not piece.strip():
                continue

            bounds = [
                int(x.strip())
                for x in piece.split("-")
            ]

            if len(bounds) == 1:
                bounds *= 2

            if (
                len(bounds) != 2
                or not 0 <= bounds[0] <= bounds[1] <= 100000
                or bounds[1] - bounds[0] > 2000
            ):
                raise ValueError

            result.update(
                range(
                    bounds[0],
                    bounds[1] + 1,
                )
            )

    except (ValueError, TypeError):
        raise ValidationError(
            "Configuración CEIC inválida; "
            "solicite su corrección al administrador."
        )

    return sorted(result)


# ============================================================
# NIVELES DISPONIBLES POR MODALIDAD
# ============================================================

def available_levels(modalidad):

    from ..models import (
        NivelServicio,
        ModalidadNivel,
    )

    if not modalidad:
        return NivelServicio.objects.none()

    return (
        NivelServicio.objects
        .filter(
            pk__in=ModalidadNivel.objects
            .filter(
                modalidad_id=modalidad
            )
            .values("nivel_id")
        )
        .order_by("c_nivel")
    )


# ============================================================
# CATÁLOGOS DE ACTIVIDAD
# ============================================================

def activity_catalogs(
    modalidad,
    nivel,
    grado=None,
    categoria=None,
):
    """
    Obtiene los catálogos correspondientes a una actividad.

    DOCENTE
    -------
    El CEIC se determina por la configuración
    ModalidadNivelCeic y los grados/secciones se obtienen
    de la combinación modalidad + nivel.

    NO DOCENTE
    ----------
    El Cargo / CEIC NO depende del rango configurado para
    modalidad/nivel.

    Se muestran exclusivamente los registros de
    nomenclador_ceic cuyo:

        1023 <= c_niv <= 1025

    Para personal NO DOCENTE no corresponden:
        - grado/año
        - sección
        - espacio curricular
    """

    # Normalizamos la categoría porque el valor visible puede llegar
    # con distintas combinaciones de mayúsculas/minúsculas.
    categoria_normalizada = str(categoria or "").strip().upper()

    # --------------------------------------------------------
    # PERSONAL NO DOCENTE
    # --------------------------------------------------------

    if categoria_normalizada == "NO DOCENTE":

        return (
            ceic_no_docente(),
            Grado_anio.objects.none(),
            Secciones.objects.none(),
        )

    # --------------------------------------------------------
    # PERSONAL DOCENTE
    # --------------------------------------------------------

    empty = (
        NomencladorCeic.objects.none(),
        Grado_anio.objects.none(),
        Secciones.objects.none(),
    )

    if (
        not modalidad
        or not nivel
        or not available_levels(modalidad)
        .filter(pk=nivel)
        .exists()
    ):
        return empty

    config = (
        ModalidadNivelCeic.objects
        .filter(
            modalidad_id=modalidad,
            nivel_id=nivel,
        )
        .first()
    )

    ceic = (
        NomencladorCeic.objects
        .filter(
            pk__in=expandir_rangos(
                config.rango_ceic
            )
            if config
            else []
        )
    )

    grados = (
        Grado_anio.objects
        .filter(
            estado=True,
            c_modalidad=modalidad,
            c_niv_grado=nivel,
            t_niv_grado="Nivel",
        )
    )

    secciones = Secciones.objects.none()

    if (
        grado
        and grados
        .filter(pk=grado)
        .exists()
    ):
        secciones = (
            Secciones.objects
            .filter(
                estado=True,
                c_modalidad=modalidad,
                c_niv_seccion=nivel,
                t_niv_seccion="Nivel",
            )
        )

    return (
        ceic.order_by("descripcion"),
        grados.order_by("c_grado_anio"),
        secciones.order_by("c_seccion"),
    )