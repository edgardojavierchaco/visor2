from django.db import migrations
from django.core.cache import cache


def crear_menu_educacion_especial(apps, schema_editor):
    MenuItem = apps.get_model("menus", "MenuItem")

    MenuItem.objects.get_or_create(
        label="Educación Especial",
        parent=None,
        defaults={
            "icon": "fas fa-universal-access",
            "url": "especial:inicio",
            "roles": [
                "Administrador",
                "Director",
                "Director de Modalidad Especial",
            ],
            "categorias": [],
            "orden": 30,
            "activo": True,
            "clave": "",
        },
    )
    cache.clear()


def quitar_menu_educacion_especial(apps, schema_editor):
    MenuItem = apps.get_model("menus", "MenuItem")
    MenuItem.objects.filter(
        label="Educación Especial",
        parent=None,
        url="especial:inicio",
    ).delete()
    cache.clear()


class Migration(migrations.Migration):

    dependencies = [
        ("menus", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            crear_menu_educacion_especial,
            quitar_menu_educacion_especial,
        ),
    ]
