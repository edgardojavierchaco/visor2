# Generated by Django 5.1.1 on 2024-11-12 16:03

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pof", "0002_cargoshoras_estado_cargoshoras_nivel_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="Departamento",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "denom_departamento",
                    models.CharField(
                        max_length=255, verbose_name="denominacion_departamento"
                    ),
                ),
            ],
            options={
                "verbose_name": "Departamento",
                "verbose_name_plural": "Departamentos",
                "db_table": "Dptos_pof",
            },
        ),
        migrations.RemoveField(
            model_name="departamentolocalidad",
            name="denom_departamento",
        ),
        migrations.AlterField(
            model_name="departamentolocalidad",
            name="denom_localidad",
            field=models.CharField(
                max_length=255, verbose_name="denominacion_localidad"
            ),
        ),
        migrations.AlterField(
            model_name="unidadservicio",
            name="localidad",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to="pof.departamentolocalidad",
                verbose_name="Localidad",
            ),
        ),
        migrations.AddField(
            model_name="departamentolocalidad",
            name="departamento",
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="localidades",
                to="pof.departamento",
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="unidadservicio",
            name="departamento",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to="pof.departamento",
                verbose_name="Departamento",
            ),
        ),
    ]
