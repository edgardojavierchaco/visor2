# Generated by Django 5.1.1 on 2024-11-12 18:13

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pof", "0003_departamento_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="unidadservicio",
            name="cueanexo",
            field=models.CharField(
                default=0, editable=False, max_length=9, verbose_name="Cueanexo"
            ),
            preserve_default=False,
        ),
        migrations.CreateModel(
            name="AsignacionPof",
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
                    "cant_cargos",
                    models.IntegerField(default=0, verbose_name="Cantidad_Cargos"),
                ),
                (
                    "cant_horas",
                    models.IntegerField(default=0, verbose_name="Cantidad_Horas"),
                ),
                (
                    "unidad",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="pof.unidadservicio",
                        verbose_name="Unidad_Servicio",
                    ),
                ),
            ],
            options={
                "verbose_name": "Asignacion",
                "verbose_name_plural": "Asignaciones",
                "db_table": "AsignacionPof",
                "ordering": ["unidad"],
            },
        ),
        migrations.CreateModel(
            name="DetalleAsignacionPof",
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
                    "asignacion",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="pof.asignacionpof",
                        verbose_name="Asignacion",
                    ),
                ),
                (
                    "cargos",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="pof.cargoshoras",
                        verbose_name="Cargos",
                    ),
                ),
            ],
            options={
                "verbose_name": "Detalle_Unidad_Cargo",
                "verbose_name_plural": "Detalles_Unidades_Cargos",
                "db_table": "Detalle_Asignacion_Pof",
                "ordering": ["cargos"],
            },
        ),
    ]