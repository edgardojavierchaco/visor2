from django.core.exceptions import ValidationError

from ..models import (
    EspacioCurricularNombre,
    Grado_anio,
    ModalidadNivelCeic,
    ModalidadTipo,
    NivelServicio,
    NivelServicioTipo,
    NomencladorCeic,
    Secciones,
    TitulacionFP,
    TitulacionNombre,
    TitulacionSuperior,
    TipoPersonal,
    CondicionActividadNombre,
)


# ============================================================
# CIRCUITO 1: CARGO / CEIC
# LEGACY - SE MANTIENE INTACTO
# ============================================================

NO_DOCENTE_C_NIV_DESDE = 1023
NO_DOCENTE_C_NIV_HASTA = 1025


def ceic_no_docente():
    """
    CEIC habilitados para personal NO DOCENTE.
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


def expandir_rangos(texto):
    """
    Convierte configuraciones como:

        1-5,10,20-25

    en una lista de IDs CEIC.
    """

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

    except (
        ValueError,
        TypeError,
    ):

        raise ValidationError(
            "Configuración CEIC inválida; "
            "solicite su corrección al administrador."
        )

    return sorted(result)


def available_levels(modalidad):
    """
    Niveles correspondientes al circuito histórico
    Cargo / CEIC.

    IMPORTANTE:
    NO utiliza nivel_servicio_tipo.
    """

    from ..models import ModalidadNivel

    if not modalidad:
        return NivelServicio.objects.none()

    return (
        NivelServicio.objects
        .filter(
            pk__in=(
                ModalidadNivel.objects
                .filter(
                    modalidad_id=modalidad
                )
                .values(
                    "nivel_id"
                )
            )
        )
        .order_by(
            "c_nivel"
        )
    )


def activity_catalogs(
    modalidad,
    nivel,
    grado=None,
    tipo_personal=None,
    categoria=None,
):
    """
    Catálogo del CIRCUITO CARGO / CEIC.

    Este circuito conserva íntegramente la lógica anterior.

    Los nuevos catálogos curriculares NO intervienen
    en la selección de Cargo / CEIC.

    Retorna:

        (
            ceic,
            grados_legacy,
            secciones_legacy
        )

    Los grados y secciones del formulario nuevo se
    resuelven mediante curricular_catalogs().
    """

    # ========================================================
    # PERSONAL NO DOCENTE
    # ========================================================

    if is_no_docente(tipo_personal, categoria):

        return (
            ceic_no_docente(),
            Grado_anio.objects.none(),
            Secciones.objects.none(),
        )

    # ========================================================
    # PERSONAL DOCENTE
    # ========================================================

    empty = (
        NomencladorCeic.objects.none(),
        Grado_anio.objects.none(),
        Secciones.objects.none(),
    )

    if (
        not modalidad
        or not nivel
        or not (
            available_levels(
                modalidad
            )
            .filter(
                pk=nivel
            )
            .exists()
        )
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
            pk__in=(
                expandir_rangos(
                    config.rango_ceic
                )
                if config
                else []
            )
        )
        .order_by(
            "descripcion"
        )
    )

    # Sólo por compatibilidad.
    # El formulario nuevo NO utiliza estos querysets.

    grados = (
        Grado_anio.objects.none()
    )

    secciones = (
        Secciones.objects.none()
    )

    return (
        ceic,
        grados,
        secciones,
    )


# ============================================================
# CIRCUITO 2:
# UBICACIÓN CURRICULAR
# NUEVO E INDEPENDIENTE DE CEIC
# ============================================================

TITULACION_NOMBRE = "NOMBRE"
TITULACION_SUPERIOR = "SUPERIOR"
TITULACION_FP = "FP"


def tipo_personal_code(value):
    """
    Devuelve c_tpersonal a partir de un objeto, código o valor vacío.
    """
    if value in (None, ""):
        return None
    if hasattr(value, "c_tpersonal"):
        return int(value.c_tpersonal)
    try:
        return int(value)
    except (TypeError, ValueError):
        text = str(value).strip().upper()
        if text == "DOCENTE":
            return 1
        if text == "NO DOCENTE":
            return 2
        return None


def is_no_docente(tipo_personal=None, categoria=None):
    code = tipo_personal_code(tipo_personal)
    if code is None:
        code = tipo_personal_code(categoria)
    return code == 2


def condiciones_actividad(tipo_personal, situacion_revista):
    """
    Condiciones válidas según:
      - tipo_personal.c_tpersonal
      - situacion_revista.cod_sitrev
    """
    code = tipo_personal_code(tipo_personal)
    try:
        sit = int(situacion_revista) if situacion_revista not in (None, "") else None
    except (TypeError, ValueError):
        sit = None

    if not code or not sit:
        return CondicionActividadNombre.objects.none()

    return (
        CondicionActividadNombre.objects
        .filter(
            t_personal=code,
            sit_rev=sit,
        )
        .order_by("denominacion", "c_nomen", "pk")
    )


def normalize_category(value):
    """
    Normaliza DOCENTE / NO DOCENTE.
    """

    return (
        str(
            value or ""
        )
        .strip()
        .upper()
    )


def get_modalidad_curricular(
    modalidad_pk,
):
    """
    Obtiene una modalidad desde modalidad1_tipo.
    """

    if not modalidad_pk:
        return None

    try:

        return (
            ModalidadTipo.objects
            .get(
                pk=modalidad_pk
            )
        )

    except ModalidadTipo.DoesNotExist:

        return None


def available_curricular_levels(
    modalidad_pk,
):
    """
    Devuelve los niveles de nivel_servicio_tipo
    correspondientes a una fila de modalidad1_tipo.
    """

    modalidad = (
        get_modalidad_curricular(
            modalidad_pk
        )
    )

    if not modalidad:

        return (
            NivelServicioTipo.objects.none()
        )

    return (
        NivelServicioTipo.objects
        .filter(
            c_modalidad1=(
                modalidad.c_modalidad1
            )
        )
        .order_by(
            "c_nivel"
        )
    )


def titulacion_source(
    modalidad_pk,
    nivel_id,
):
    """
    Determina de qué tabla proviene la titulación.

    REGLAS:

    1. Secundario común
       -> titulacion_nombre

    2. Secundario adultos
       ESJA / ESJA Módulo / Perito
       -> titulacion_nombre

    3. Superior común
       -> titulacion_superior

    4. Formación Profesional Adultos
       -> titulacion_fp

    Para otras combinaciones se permite
    titulacion_nombre cuando existen registros.
    """

    modalidad = (
        get_modalidad_curricular(
            modalidad_pk
        )
    )

    if (
        not modalidad
        or not nivel_id
    ):
        return ""

    code = (
        modalidad.c_modalidad1
    )

    try:

        nivel_id = int(
            nivel_id
        )

    except (
        TypeError,
        ValueError,
    ):

        return ""

    # ========================================================
    # SUPERIOR COMÚN
    # ========================================================

    if (
        code == 1
        and nivel_id == 1004
    ):
        return TITULACION_SUPERIOR

    # ========================================================
    # FORMACIÓN PROFESIONAL - ADULTOS
    # ========================================================

    if (
        code == 3
        and nivel_id == 3021
    ):
        return TITULACION_FP

    # ========================================================
    # TITULACION_NOMBRE
    #
    # Incluye:
    # - Secundario común
    # - Secundario adultos
    # - ESJA
    # - ESJA módulo
    # - Perito
    # - otras combinaciones existentes
    # ========================================================

    if (
        TitulacionNombre.objects
        .filter(
            c_modalidad1=code,
            c_nivel_servicio=nivel_id,
        )
        .exists()
    ):
        return TITULACION_NOMBRE

    return ""


def titulacion_options(
    modalidad_pk,
    nivel_id,
):
    """
    Devuelve las titulaciones en una estructura uniforme:

    [
        {
            "id_titulacion": ...,
            "descripcion": ...,
            "detalle": ...,
            "fuente": ...
        }
    ]
    """

    modalidad = (
        get_modalidad_curricular(
            modalidad_pk
        )
    )

    fuente = (
        titulacion_source(
            modalidad_pk,
            nivel_id,
        )
    )

    if (
        not modalidad
        or not nivel_id
        or not fuente
    ):
        return []

    code = (
        modalidad.c_modalidad1
    )

    nivel_id = int(
        nivel_id
    )

    # ========================================================
    # TITULACION_NOMBRE
    # ========================================================

    if fuente == TITULACION_NOMBRE:

        rows = (
            TitulacionNombre.objects
            .filter(
                c_modalidad1=code,
                c_nivel_servicio=nivel_id,
            )
            .order_by(
                "nombre",
                "id_titulacion",
            )
            .values(
                "id_titulacion",
                "nombre",
                "descripcion_adicional",
            )
        )

        return [
            {
                "id_titulacion": (
                    row["id_titulacion"]
                ),

                "descripcion": (
                    row["nombre"]
                ),

                "detalle": (
                    row.get(
                        "descripcion_adicional"
                    )
                    or ""
                ),

                "fuente": fuente,
            }
            for row in rows
        ]

    # ========================================================
    # TITULACION SUPERIOR / FP
    # ========================================================

    model = (
        TitulacionSuperior
        if fuente == TITULACION_SUPERIOR
        else TitulacionFP
    )

    rows = (
        model.objects
        .filter(
            c_modalidad1=code,
            c_nivel_servicio=nivel_id,
        )
        .order_by(
            "descripcion",
            "id_titulacion",
        )
        .values(
            "id_titulacion",
            "descripcion",
        )
    )

    return [
        {
            "id_titulacion": (
                row["id_titulacion"]
            ),

            "descripcion": (
                row["descripcion"]
            ),

            "detalle": "",

            "fuente": fuente,
        }
        for row in rows
    ]


def valid_titulacion(
    modalidad_pk,
    nivel_id,
    titulacion,
    fuente=None,
):
    """
    Valida que una titulación pertenezca
    a la modalidad/nivel seleccionados.
    """

    if not titulacion:
        return False

    expected = (
        titulacion_source(
            modalidad_pk,
            nivel_id,
        )
    )

    if (
        not expected
        or (
            fuente
            and fuente != expected
        )
    ):
        return False

    return any(
        int(
            item["id_titulacion"]
        )
        ==
        int(
            titulacion
        )
        for item in (
            titulacion_options(
                modalidad_pk,
                nivel_id,
            )
        )
    )


def curricular_catalogs(
    modalidad_pk,
    nivel_id=None,
    titulacion=None,
    tipo_personal=None,
    categoria=None,
):
    """
    Resuelve el CIRCUITO CURRICULAR.

    Este circuito es totalmente independiente
    del circuito Cargo / CEIC.

    Devuelve:

        niveles
        titulaciones
        fuente_titulacion
        espacios
        grados
        secciones

    Para personal NO DOCENTE devuelve
    catálogos curriculares vacíos.
    """

    # ========================================================
    # PERSONAL NO DOCENTE
    # ========================================================

    if is_no_docente(tipo_personal, categoria):

        return {
            "niveles": (
                NivelServicioTipo.objects.none()
            ),

            "titulaciones": [],

            "fuente_titulacion": "",

            "espacios": (
                EspacioCurricularNombre.objects.none()
            ),

            "grados": (
                Grado_anio.objects.none()
            ),

            "secciones": (
                Secciones.objects.none()
            ),
        }

    # ========================================================
    # MODALIDAD / NIVELES
    # ========================================================

    modalidad = (
        get_modalidad_curricular(
            modalidad_pk
        )
    )

    niveles = (
        available_curricular_levels(
            modalidad_pk
        )
    )

    if (
        not modalidad
        or not nivel_id
        or not (
            niveles
            .filter(
                pk=nivel_id
            )
            .exists()
        )
    ):

        return {
            "niveles": niveles,

            "titulaciones": [],

            "fuente_titulacion": "",

            "espacios": (
                EspacioCurricularNombre.objects.none()
            ),

            "grados": (
                Grado_anio.objects.none()
            ),

            "secciones": (
                Secciones.objects.none()
            ),
        }

    code = (
        modalidad.c_modalidad1
    )

    nivel_id = int(
        nivel_id
    )

    # ========================================================
    # TITULACIONES
    # ========================================================

    fuente = (
        titulacion_source(
            modalidad_pk,
            nivel_id,
        )
    )

    titulaciones = (
        titulacion_options(
            modalidad_pk,
            nivel_id,
        )
    )

    # ========================================================
    # ESPACIOS CURRICULARES
    #
    # IMPORTANTE:
    # Se eliminan nombres duplicados.
    #
    # PostgreSQL genera:
    #
    # DISTINCT ON (nombre)
    #
    # Conserva la fila de menor id_espacio_curricular.
    # ========================================================

    espacios = (
        EspacioCurricularNombre.objects.none()
    )

    if (
        titulacion
        and valid_titulacion(
            modalidad_pk,
            nivel_id,
            titulacion,
            fuente,
        )
    ):

        espacios = (
            EspacioCurricularNombre.objects
            .filter(
                id_titulacion=int(
                    titulacion
                )
            )

            # Evitar nombres vacíos
            .exclude(
                nombre__isnull=True
            )
            .exclude(
                nombre=""
            )

            # DISTINCT ON necesita que el
            # order_by comience por el campo
            # utilizado en distinct().
            .order_by(
                "nombre",
                "id_espacio_curricular",
            )

            # PostgreSQL DISTINCT ON
            .distinct(
                "nombre"
            )
        )

    # ========================================================
    # GRADOS / AÑOS
    # ========================================================

    grados = (
        Grado_anio.objects
        .filter(
            estado=True,

            c_modalidad1=code,

            c_niv_grado=(
                nivel_id
            ),

            t_niv_grado__iexact=(
                "Nivel"
            ),
        )
        .order_by(
            "c_grado_anio"
        )
    )

    # ========================================================
    # SECCIONES
    # ========================================================

    secciones = (
        Secciones.objects
        .filter(
            estado=True,

            c_modalidad1=code,

            c_niv_seccion=(
                nivel_id
            ),

            t_niv_seccion__iexact=(
                "Nivel"
            ),
        )
        .order_by(
            "c_seccion"
        )
    )

    # ========================================================
    # RESULTADO
    # ========================================================

    return {
        "niveles": niveles,

        "titulaciones": titulaciones,

        "fuente_titulacion": fuente,

        "espacios": espacios,

        "grados": grados,

        "secciones": secciones,
    }


def titulacion_label(
    fuente,
    titulacion,
):
    """
    Obtiene la descripción de una titulación
    independientemente de la tabla de origen.
    """

    if (
        not fuente
        or not titulacion
    ):
        return ""

    # ========================================================
    # TITULACION_NOMBRE
    # ========================================================

    if fuente == TITULACION_NOMBRE:

        obj = (
            TitulacionNombre.objects
            .filter(
                id_titulacion=titulacion
            )
            .first()
        )

        return (
            obj.nombre
            if obj
            else ""
        )

    # ========================================================
    # TITULACION_SUPERIOR
    # ========================================================

    if fuente == TITULACION_SUPERIOR:

        obj = (
            TitulacionSuperior.objects
            .filter(
                id_titulacion=titulacion
            )
            .first()
        )

        return (
            obj.descripcion
            if obj
            else ""
        )

    # ========================================================
    # TITULACION_FP
    # ========================================================

    if fuente == TITULACION_FP:

        obj = (
            TitulacionFP.objects
            .filter(
                id_titulacion=titulacion
            )
            .first()
        )

        return (
            obj.descripcion
            if obj
            else ""
        )

    return ""