# Generated by Django 4.2.5 on 2024-08-13 01:04

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="DirectoresRegionales",
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
                ("dni_reg", models.CharField(max_length=8, verbose_name="DNI")),
                (
                    "apellido_reg",
                    models.CharField(max_length=255, verbose_name="Apellido"),
                ),
                (
                    "nombres_reg",
                    models.CharField(max_length=255, verbose_name="Nombres"),
                ),
                ("email_reg", models.EmailField(max_length=254, verbose_name="Email")),
                (
                    "telefono_reg",
                    models.CharField(max_length=11, verbose_name="Teléfono"),
                ),
                (
                    "region_reg",
                    models.CharField(max_length=25, verbose_name="Regional"),
                ),
            ],
            options={
                "verbose_name": "Director Regional",
                "verbose_name_plural": "Directores Regionales",
                "db_table": "public.director_regional",
            },
        ),
        migrations.CreateModel(
            name="Supervisor",
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
                ("apellido", models.CharField(max_length=255, verbose_name="Apellido")),
                ("nombres", models.CharField(max_length=255, verbose_name="Nombres")),
                ("email", models.EmailField(max_length=254, verbose_name="Email")),
                ("telefono", models.CharField(max_length=11, verbose_name="Teléfono")),
                ("region", models.CharField(max_length=25, verbose_name="Regional")),
            ],
            options={
                "verbose_name": "Supervisor",
                "verbose_name_plural": "Supervisores",
                "db_table": "public.supervisores",
            },
        ),
        migrations.CreateModel(
            name="EscuelaSupervisor",
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
                ("cueanexo", models.CharField(max_length=9, verbose_name="Cueanexo")),
                ("oferta", models.CharField(max_length=100, verbose_name="Oferta")),
                (
                    "modalidad",
                    models.CharField(max_length=100, verbose_name="Modalidadad"),
                ),
                (
                    "supervisor",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="escuelas",
                        to="supervisores.supervisor",
                        verbose_name="Supervisor",
                    ),
                ),
            ],
            options={
                "verbose_name": "Escuela Supervisor",
                "verbose_name_plural": "Escuelas Supervisores",
                "db_table": "public.escuela_supervisores",
            },
        ),
    ]
