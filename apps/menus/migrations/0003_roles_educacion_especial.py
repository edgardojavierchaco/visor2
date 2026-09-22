from django.core.cache import cache
from django.db import migrations


ROLES_EDUCACION_ESPECIAL = [
    "Administrador",
    "Ministro",
    "Subsecretario",
    "Director general",
    "Director de Modalidad Especial",
    "Regional",
    "Supervisor",
    "Director",
]


def actualizar_roles_menu(apps, schema_editor):
    MenuItem = apps.get_model("menus", "MenuItem")
    MenuItem.objects.filter(
        label="Educación Especial",
        parent=None,
        url="especial:inicio",
    ).update(roles=ROLES_EDUCACION_ESPECIAL)
    cache.clear()


class Migration(migrations.Migration):

    dependencies = [
        ("menus", "0002_menu_educacion_especial"),
    ]

    operations = [
        migrations.RunPython(actualizar_roles_menu, migrations.RunPython.noop),
    ]
