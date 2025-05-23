# Generated by Django 5.1.1 on 2025-03-29 20:07

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="AlumnosSecundaria",
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
            ],
            options={
                "verbose_name": "Alumno Secundaria",
                "verbose_name_plural": "Alumnos Secundaria",
                "db_table": "Alumno_Secundaria",
            },
        ),
        migrations.CreateModel(
            name="Pregunta",
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
                    "descripcion",
                    models.CharField(max_length=255, verbose_name="Descripción"),
                ),
                (
                    "puntaje_maximo",
                    models.DecimalField(
                        decimal_places=2, max_digits=4, verbose_name="Puntaje Máximo"
                    ),
                ),
                ("opciones", models.JSONField(default=list, verbose_name="Opciones")),
            ],
            options={
                "verbose_name": "Pregunta",
                "verbose_name_plural": "Preguntas",
                "db_table": "Pregunta",
            },
        ),
        migrations.CreateModel(
            name="ExamenAlumnoCueanexoL",
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
                ("fecha_examen", models.DateTimeField(auto_now_add=True)),
                (
                    "alumno",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="operativoschaco.alumnossecundaria",
                    ),
                ),
            ],
            options={
                "verbose_name": "Examen Alumno",
                "verbose_name_plural": "Exámenes Alumnos",
                "db_table": "Examen_Alumno_Cueanexo",
            },
        ),
        migrations.CreateModel(
            name="Respuesta",
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
                    "opcion_seleccionada",
                    models.CharField(
                        max_length=255, verbose_name="Opción Seleccionada"
                    ),
                ),
                (
                    "puntaje",
                    models.DecimalField(
                        decimal_places=2,
                        default=0.0,
                        max_digits=4,
                        verbose_name="Puntaje",
                    ),
                ),
                (
                    "examen",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="operativoschaco.examenalumnocueanexol",
                    ),
                ),
                (
                    "pregunta",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="operativoschaco.pregunta",
                    ),
                ),
            ],
            options={
                "verbose_name": "Respuesta",
                "verbose_name_plural": "Respuestas",
                "db_table": "Respuesta",
            },
        ),
    ]
