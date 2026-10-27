"""
Migración 0004 - Menú de Educación Intercultural Bilingüe.

Integra Intercultural al menú dinámico de Visor Educativo Chaco.

Características:
- Utiliza el modelo menus.MenuItem.
- No crea un sidebar independiente.
- Conserva las entradas existentes.
- Evita duplicar las opciones del módulo.
- Respeta la estructura jerárquica del menú.
- No depende de la disponibilidad de Redis para migrar.
- Limpia la caché después de confirmar la transacción.
"""

import logging

from django.core.cache import cache
from django.db import migrations, transaction


logger = logging.getLogger(__name__)


# ============================================================
# ROLES HABILITADOS
# ============================================================

ROLES = [
    "Administrador",
    "Ministro",
    "Subsecretario",
    "Director general",
    "Director General",
    "Regional",
    "Supervisor",
    "Director",
    "Director de Modalidad Especial",
    "Evaluacion",
]


# ============================================================
# OPCIONES DEL MENÚ INTERCULTURAL
# ============================================================

OPCIONES = [
    (
        "Panorama Ejecutivo",
        "fas fa-chart-pie",
        "intercultural:dashboard",
        10,
    ),
    (
        "Establecimientos",
        "fas fa-school",
        "intercultural:establecimientos",
        20,
    ),
    (
        "Registro Estadístico",
        "fas fa-table",
        "intercultural:alumnos_list",
        30,
    ),
    (
        "Mapa Territorial",
        "fas fa-map-marked-alt",
        "intercultural:mapa",
        40,
    ),
    (
        "Guía de Indicadores",
        "fas fa-book-open",
        "intercultural:guia",
        50,
    ),
]


# ============================================================
# LIMPIEZA SEGURA DE CACHÉ
# ============================================================

def limpiar_cache_menu():
    """
    Intenta limpiar la caché después de aplicar la migración.

    Redis puede no estar disponible cuando Django se ejecuta
    directamente desde Ubuntu.

    Si Redis falla, la migración no debe interrumpirse.
    """

    try:

        cache.clear()

        logger.info(
            "Caché invalidada después de actualizar "
            "el menú Intercultural EIB."
        )

    except Exception as exc:

        logger.warning(
            "No fue posible limpiar la caché del menú "
            "Intercultural EIB: %s",
            exc,
        )


def programar_limpieza_cache(database_alias):
    """
    Programa la limpieza después de confirmar
    la transacción de PostgreSQL.
    """

    transaction.on_commit(
        limpiar_cache_menu,
        using=database_alias,
        robust=True,
    )


# ============================================================
# CREAR MENÚ INTERCULTURAL
# ============================================================

def crear_menu(apps, schema_editor):

    MenuItem = apps.get_model(
        "menus",
        "MenuItem",
    )

    database_alias = schema_editor.connection.alias

    manager = MenuItem.objects.using(database_alias)

    # --------------------------------------------------------
    # CREAR MENÚ PRINCIPAL
    # --------------------------------------------------------

    padre, creado = manager.get_or_create(

        parent=None,

        label="Educación Intercultural Bilingüe",

        defaults={
            "icon": "fas fa-globe-americas",
            "url": "",
            "roles": ROLES,
            "categorias": [],
            "orden": 38,
            "activo": True,
            "clave": "",
        },

    )

    if creado:

        logger.info(
            "Menú principal Intercultural EIB creado."
        )

    else:

        logger.info(
            "El menú principal Intercultural EIB "
            "ya existe. Se conserva."
        )

    # --------------------------------------------------------
    # CREAR SUBMENÚS
    # --------------------------------------------------------

    for label, icon, url, orden in OPCIONES:

        item, item_creado = manager.get_or_create(

            parent=padre,

            url=url,

            defaults={
                "label": label,
                "icon": icon,
                "roles": ROLES,
                "categorias": [],
                "orden": orden,
                "activo": True,
                "clave": "",
            },

        )

        if item_creado:

            logger.info(
                "Opción de menú creada: %s",
                label,
            )

        else:

            logger.info(
                "La opción %s ya existe. "
                "Se conserva su configuración.",
                label,
            )

    # --------------------------------------------------------
    # INVALIDAR CACHÉ DESPUÉS DEL COMMIT
    # --------------------------------------------------------

    programar_limpieza_cache(database_alias)


# ============================================================
# REVERSIÓN DE LA MIGRACIÓN
# ============================================================

def quitar_menu(apps, schema_editor):

    MenuItem = apps.get_model(
        "menus",
        "MenuItem",
    )

    database_alias = schema_editor.connection.alias

    manager = MenuItem.objects.using(database_alias)

    padre = manager.filter(

        parent=None,

        label="Educación Intercultural Bilingüe",

    ).first()

    if padre:

        urls = [
            opcion[2]
            for opcion in OPCIONES
        ]

        manager.filter(

            parent=padre,

            url__in=urls,

        ).delete()

        # Eliminar el menú principal solamente si
        # no quedan opciones asociadas.

        if not manager.filter(
            parent=padre
        ).exists():

            padre.delete()

    programar_limpieza_cache(database_alias)


# ============================================================
# MIGRACIÓN DJANGO
# ============================================================

class Migration(migrations.Migration):

    dependencies = [
        (
            "menus",
            "0003_roles_educacion_especial",
        ),
    ]

    operations = [

        migrations.RunPython(
            crear_menu,
            quitar_menu,
        ),

    ]