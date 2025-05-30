# Generated by Django 5.1.1 on 2025-05-05 13:53

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("operativchaco", "0018_totalprimarias"),
    ]

    operations = [
        migrations.CreateModel(
            name="ExamenFluidezTercero",
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
                ("dni", models.CharField(max_length=8, verbose_name="DNI")),
                (
                    "apellidos",
                    models.CharField(max_length=255, verbose_name="Apellidos"),
                ),
                ("nombres", models.CharField(max_length=255, verbose_name="Nombres")),
                ("cueanexo", models.CharField(max_length=9, verbose_name="Cueanexo")),
                (
                    "grado",
                    models.CharField(default="3", max_length=25, verbose_name="Grado"),
                ),
                ("division", models.CharField(max_length=5, verbose_name="División")),
                ("region", models.CharField(max_length=25, verbose_name="Regional")),
                (
                    "discapacidad",
                    models.CharField(
                        choices=[("SI", "SI"), ("NO", "NO")],
                        max_length=2,
                        verbose_name="Discapacidad",
                    ),
                ),
                (
                    "etnia",
                    models.CharField(
                        choices=[
                            ("NO", "NO"),
                            ("QOM", "QOM"),
                            ("WICHI", "WICHI"),
                            ("MOQOIT", "MOQOIT"),
                        ],
                        max_length=10,
                        verbose_name="Etnia",
                    ),
                ),
                (
                    "velocidad",
                    models.IntegerField(
                        validators=[django.core.validators.MaxValueValidator(120)],
                        verbose_name="Velocidad",
                    ),
                ),
                (
                    "precision",
                    models.IntegerField(
                        validators=[django.core.validators.MaxValueValidator(120)],
                        verbose_name="Precisión",
                    ),
                ),
                (
                    "prosodia",
                    models.CharField(
                        choices=[("1", "1"), ("2", "2"), ("3", "3"), ("4", "4")],
                        verbose_name="Prosodia",
                    ),
                ),
                (
                    "p1",
                    models.CharField(
                        choices=[("NR", "NR"), ("a", "a"), ("b", "b"), ("c", "c")],
                        verbose_name="Pregunta 1",
                    ),
                ),
                (
                    "p2",
                    models.CharField(
                        choices=[("NR", "NR"), ("a", "a"), ("b", "b"), ("c", "c")],
                        verbose_name="Pregunta 2",
                    ),
                ),
                (
                    "p3",
                    models.CharField(
                        choices=[("NR", "NR"), ("a", "a"), ("b", "b"), ("c", "c")],
                        verbose_name="Pregunta 3",
                    ),
                ),
            ],
            options={
                "verbose_name": "Examen Fluidez Tercero",
                "verbose_name_plural": "Examenes Fluidez Tercero",
                "db_table": "Examen_Fluidez_Tercero",
            },
        ),
        migrations.CreateModel(
            name="RegistroAsistenciaFluidezSegundo",
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
                ("cueanexo", models.CharField(max_length=15)),
                ("fecha", models.DateTimeField(auto_now_add=True)),
                ("region", models.CharField(max_length=25)),
                ("ausentes", models.PositiveIntegerField()),
                ("total_registros", models.PositiveIntegerField()),
            ],
            options={
                "verbose_name": "Registro Asistencia Fluidez Segundo",
                "verbose_name_plural": "Registros Asistencia Fluidez Segundo",
                "db_table": "Registro_Asistencia_Fluidez_Segundo",
            },
        ),
        migrations.CreateModel(
            name="RegistroAsistenciaFluidezTercero",
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
                ("cueanexo", models.CharField(max_length=15)),
                ("fecha", models.DateTimeField(auto_now_add=True)),
                ("region", models.CharField(max_length=25)),
                ("ausentes", models.PositiveIntegerField()),
                ("total_registros", models.PositiveIntegerField()),
            ],
            options={
                "verbose_name": "Registro Asistencia Fluidez Tercero",
                "verbose_name_plural": "Registros Asistencia Fluidez Tercero",
                "db_table": "Registro_Asistencia_Fluidez_Tercero",
            },
        ),
        migrations.AlterField(
            model_name="alumnosprimariafluidez",
            name="grado",
            field=models.CharField(max_length=25, verbose_name="grado"),
        ),
        migrations.AlterField(
            model_name="examenfluidezsegundo",
            name="grado",
            field=models.CharField(default="2", max_length=25, verbose_name="Grado"),
        ),
    ]
