# Generated by Django 4.2.5 on 2024-08-29 12:48

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("cenpe", "0009_alter_datos_personal_cenpe_celular_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="condicionactividad",
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
                    "cond_act",
                    models.CharField(
                        max_length=255, verbose_name="Condición Actividad"
                    ),
                ),
            ],
            options={
                "verbose_name": "Condicion Actividad",
                "verbose_name_plural": "Condiciones Actividades",
                "db_table": "condicion_actividad",
                "managed": True,
            },
        ),
        migrations.CreateModel(
            name="funciones",
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
                ("funcion", models.CharField(max_length=100, verbose_name="funcion")),
            ],
            options={
                "verbose_name": "Funcion",
                "verbose_name_plural": "Funciones",
                "db_table": "funciones",
                "managed": True,
            },
        ),
        migrations.CreateModel(
            name="SituacionRevista",
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
                    "sit_rev",
                    models.CharField(max_length=100, verbose_name="Situación Revista"),
                ),
            ],
            options={
                "verbose_name": "Situacion Revista",
                "verbose_name_plural": "Situaciones Revistas",
                "db_table": "situacion_revista",
                "managed": True,
            },
        ),
    ]