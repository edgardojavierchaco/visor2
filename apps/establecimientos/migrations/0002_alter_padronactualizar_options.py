# Generated by Django 4.2.5 on 2024-04-12 14:26

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("establecimientos", "0001_initial"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="padronactualizar",
            options={
                "managed": False,
                "ordering": ["id_establecimiento", "id_localizacion", "cueanexo"],
                "verbose_name": "Padron_Actualizar",
                "verbose_name_plural": "Padrones_Actualizaciones",
            },
        ),
    ]
