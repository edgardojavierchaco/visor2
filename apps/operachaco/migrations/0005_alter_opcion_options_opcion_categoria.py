# Generated by Django 5.1.1 on 2025-03-27 17:24

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("operachaco", "0004_opcion_puntaje"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="opcion",
            options={"verbose_name": "Opción", "verbose_name_plural": "Opciones"},
        ),
        migrations.AddField(
            model_name="opcion",
            name="categoria",
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="opciones",
                to="operachaco.categoria",
            ),
            preserve_default=False,
        ),
    ]
