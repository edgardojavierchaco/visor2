# apps/supervisor_registro/services/permission_service.py

# apps/supervisor_registro/services/permission_service.py

from apps.supervisa2.models import Region

from ..models import ResponsableRegional


# ============================================================
# ROLES
# ============================================================

# ÚNICOS que pueden hacer CRUD
ROLES_CRUD = {
    "administrador",
    "gestor",
}


# Visualización provincial completa
ROLES_VISUALIZACION_GLOBAL = {
    "administrador",
    "gestor",
    "funcionario",
}


# Visualización restringida territorialmente
ROLES_REGIONALES = {
    "regional",
}


class PermissionDenied(Exception):
    """Excepción de dominio para permisos del módulo."""
    pass


# ============================================================
# UTILIDADES
# ============================================================

def _normalizar_rol(valor):
    """
    Convierte el nivel de acceso a un valor comparable.
    """

    if valor is None:
        return ""

    return str(valor).strip().lower()


def get_rol_usuario(user):
    """
    Devuelve el nivel de acceso normalizado.
    """

    if not user:
        return ""

    if not getattr(
        user,
        "is_authenticated",
        False,
    ):
        return ""

    nivel = getattr(
        user,
        "nivelacceso",
        None,
    )

    if nivel is None:
        return ""

    # Compatibilidad en caso de que nivelacceso
    # pase a ser FK/objeto.
    for atributo in (
        "nombre",
        "descripcion",
        "nivel",
        "rol",
        "codigo",
    ):

        if hasattr(nivel, atributo):

            valor = getattr(
                nivel,
                atributo,
                None,
            )

            if valor:
                return _normalizar_rol(
                    valor
                )

    return _normalizar_rol(
        nivel
    )


# ============================================================
# CRUD
# ============================================================

def puede_administrar_supervisores(user):
    """
    Sólo:

        - Administrador
        - Gestor
        - superuser

    pueden hacer CRUD.
    """

    if not user:
        return False

    if not getattr(
        user,
        "is_authenticated",
        False,
    ):
        return False

    if getattr(
        user,
        "is_superuser",
        False,
    ):
        return True

    return (
        get_rol_usuario(user)
        in ROLES_CRUD
    )


def es_admin(user):
    """
    Alias para compatibilidad.

    En este módulo significa:
    usuario autorizado para CRUD.
    """

    return puede_administrar_supervisores(
        user
    )


def puede_crear_supervisor(user):
    return puede_administrar_supervisores(
        user
    )


def puede_modificar_supervisor(user):
    return puede_administrar_supervisores(
        user
    )


def puede_eliminar_supervisor(user):
    return puede_administrar_supervisores(
        user
    )


# ============================================================
# RESPONSABLE REGIONAL
# ============================================================

def get_responsable(user):
    """
    Obtiene el ResponsableRegional vinculado al usuario.

    Se intenta primero mediante el related_name del OneToOne
    y luego mediante consulta directa.

    Esto evita problemas de resolución del responsable regional.
    """

    if not user:
        return None

    if not getattr(
        user,
        "is_authenticated",
        False,
    ):
        return None

    # --------------------------------------------------------
    # PRIMER MÉTODO
    # relación OneToOne inversa
    # --------------------------------------------------------

    try:

        responsable = (
            user.responsable_regional
        )

        if responsable and responsable.activo:

            # Precarga explícita de regiones.
            return (
                ResponsableRegional.objects
                .prefetch_related(
                    "regiones"
                )
                .filter(
                    pk=responsable.pk,
                    activo=True,
                )
                .first()
            )

    except (
        ResponsableRegional.DoesNotExist,
        AttributeError,
    ):
        pass

    # --------------------------------------------------------
    # SEGUNDO MÉTODO
    # búsqueda directa por PK del usuario
    # --------------------------------------------------------

    user_pk = getattr(
        user,
        "pk",
        None,
    )

    if user_pk is None:
        return None

    return (
        ResponsableRegional.objects
        .filter(
            usuario_id=user_pk,
            activo=True,
        )
        .prefetch_related(
            "regiones"
        )
        .first()
    )


def assert_responsable(user):
    """
    Devuelve el ResponsableRegional o genera excepción.
    """

    responsable = get_responsable(
        user
    )

    if not responsable:

        raise PermissionDenied(
            "El usuario Regional no posee "
            "un ResponsableRegional activo asociado."
        )

    return responsable


# ============================================================
# REGIONES ASIGNADAS
# ============================================================

def get_ids_regiones_responsable(user):
    """
    Devuelve exclusivamente los IDs de las regiones asignadas
    al ResponsableRegional del usuario.

    Siempre devuelve lista.
    """

    responsable = get_responsable(
        user
    )

    if not responsable:
        return []

    return list(
        responsable.regiones
        .values_list(
            "pk",
            flat=True,
        )
        .distinct()
    )


# ============================================================
# VISUALIZACIÓN
# ============================================================

def puede_ver_supervisores(user):
    """
    Todos los usuarios autenticados pueden ingresar
    a las funciones de consulta.

    El alcance territorial se controla por separado.
    """

    if not user:
        return False

    return bool(
        getattr(
            user,
            "is_authenticated",
            False,
        )
    )


# ============================================================
# ALCANCE TERRITORIAL
# ============================================================

def get_regiones_usuario(user):
    """
    Devuelve el alcance territorial.

    RETORNOS
    ========================================================

    None
        Puede ver TODAS las regiones.

    [1, 2, 5]
        Sólo puede ver esas regiones.

    []
        No posee regiones habilitadas.


    REGLAS
    ========================================================

    Administrador
        todas las regiones

    Gestor
        todas las regiones

    Funcionario
        todas las regiones

    Regional
        EXCLUSIVAMENTE las regiones que tenga
        en ResponsableRegional.regiones

    Otros roles
        sólo lectura provincial
    """

    if not user:

        return []

    if not getattr(
        user,
        "is_authenticated",
        False,
    ):

        return []

    # --------------------------------------------------------
    # SUPERUSER
    # --------------------------------------------------------

    if getattr(
        user,
        "is_superuser",
        False,
    ):

        return None

    rol = get_rol_usuario(
        user
    )

    # --------------------------------------------------------
    # REGIONAL
    #
    # IMPORTANTE:
    # debe evaluarse ANTES que cualquier acceso global.
    # --------------------------------------------------------

    if rol in ROLES_REGIONALES:

        return get_ids_regiones_responsable(
            user
        )

    # --------------------------------------------------------
    # ADMINISTRADOR / GESTOR / FUNCIONARIO
    # --------------------------------------------------------

    if rol in ROLES_VISUALIZACION_GLOBAL:

        return None

    # --------------------------------------------------------
    # RESTO DE USUARIOS
    #
    # Sólo lectura provincial.
    # --------------------------------------------------------

    return None


# ============================================================
# QUERYSET REGIONES
# ============================================================

def get_regiones_queryset(user):
    """
    Devuelve las regiones que pueden aparecer en los filtros,
    selects y formularios de consulta.
    """

    regiones = get_regiones_usuario(
        user
    )

    # --------------------------------------------------------
    # ACCESO GLOBAL
    # --------------------------------------------------------

    if regiones is None:

        return (
            Region.objects
            .all()
            .order_by(
                "nombre"
            )
        )

    # --------------------------------------------------------
    # SIN REGIONES
    # --------------------------------------------------------

    if not regiones:

        return Region.objects.none()

    # --------------------------------------------------------
    # REGIONAL
    # --------------------------------------------------------

    return (
        Region.objects
        .filter(
            pk__in=regiones
        )
        .order_by(
            "nombre"
        )
    )


# ============================================================
# VERIFICAR REGIÓN
# ============================================================

def puede_operar_region(
    user,
    region_id,
    accion="ver",
):
    """
    CRUD:
        sólo Administrador/Gestor.

    Consulta:
        se controla territorialmente.
    """

    if not user:

        return False

    if not getattr(
        user,
        "is_authenticated",
        False,
    ):

        return False

    # ========================================================
    # CRUD
    # ========================================================

    if accion in {
        "crear",
        "modificar",
        "eliminar",
    }:

        return puede_administrar_supervisores(
            user
        )

    # ========================================================
    # VER
    # ========================================================

    if accion != "ver":

        return False

    regiones = get_regiones_usuario(
        user
    )

    # Acceso provincial.
    if regiones is None:

        return True

    if not regiones:

        return False

    try:

        region_id = int(
            region_id
        )

    except (
        TypeError,
        ValueError,
    ):

        return False

    return region_id in regiones


# ============================================================
# VERIFICAR SUPERVISOR
# ============================================================

def puede_operar_supervisor(
    user,
    supervisor,
    accion="ver",
):
    """
    CRUD
    ========================================================

    Administrador    SI
    Gestor           SI
    Funcionario      NO
    Regional         NO
    Otros            NO


    CONSULTA
    ========================================================

    Administrador    todos
    Gestor           todos
    Funcionario      todos

    Regional
        únicamente supervisores con una asignación activa
        perteneciente a alguna de sus regiones.
    """

    if not user:

        return False

    if not getattr(
        user,
        "is_authenticated",
        False,
    ):

        return False

    # ========================================================
    # CRUD
    # ========================================================

    if accion in {
        "crear",
        "modificar",
        "eliminar",
    }:

        return puede_administrar_supervisores(
            user
        )

    # ========================================================
    # CONSULTA
    # ========================================================

    if accion != "ver":

        return False

    if not puede_ver_supervisores(
        user
    ):

        return False

    regiones = get_regiones_usuario(
        user
    )

    # Acceso global.
    if regiones is None:

        return True

    # Regional sin regiones.
    if not regiones:

        return False

    # Tiene que existir una asignación activa del supervisor
    # dentro de una de las regiones permitidas.
    return (
        supervisor
        .asignaciones_regionales
        .filter(
            activo=True,
            region_id__in=regiones,
        )
        .exists()
    )