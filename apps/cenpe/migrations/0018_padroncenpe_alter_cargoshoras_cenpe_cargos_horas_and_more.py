# Generated by Django 4.2.5 on 2024-09-02 15:31

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("cenpe", "0017_categoria_cueanexo_tipojornada_cueanexo_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="PadronCenpe",
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
                ("cueanexo", models.IntegerField(verbose_name="cueanexo")),
                (
                    "id_establecimiento",
                    models.CharField(verbose_name="id_establecimiento"),
                ),
                ("id_localizacion", models.CharField(verbose_name="id_localizacion")),
                ("id_oferta_local", models.CharField(verbose_name="id_oferta_local")),
                ("nom_est", models.CharField(verbose_name="nom_est")),
                ("acronimo_oferta", models.CharField(verbose_name="acronimo_oferta")),
                ("oferta", models.CharField(verbose_name="oferta")),
                ("nro_est", models.CharField(verbose_name="nro_est")),
                ("ambito", models.CharField(verbose_name="ambito")),
                ("sector", models.CharField(verbose_name="sector")),
                ("region_loc", models.CharField(verbose_name="region_loc")),
                ("ref_loc", models.CharField(verbose_name="ref_loc")),
                ("calle", models.CharField(verbose_name="calle")),
                ("numero", models.CharField(verbose_name="numero")),
                ("localidad", models.CharField(verbose_name="localidad")),
                ("departamento", models.CharField(verbose_name="departamento")),
                ("estado_loc", models.CharField(verbose_name="estado_loc")),
                ("est_oferta", models.CharField(verbose_name="est_oferta")),
                ("estado_est", models.CharField(verbose_name="estado_est")),
                ("jornada", models.CharField(verbose_name="jornada")),
            ],
            options={
                "verbose_name": "Padron_Cenpe",
                "verbose_name_plural": "Padrones_Cenpe",
                "db_table": "public.padron_ofertas",
                "managed": False,
            },
        ),
        migrations.AlterField(
            model_name="cargoshoras_cenpe",
            name="cargos_horas",
            field=models.CharField(max_length=255, verbose_name="Cargo_Horas"),
        ),
        migrations.AlterField(
            model_name="cargoshoras_cenpe",
            name="categoria",
            field=models.CharField(max_length=50, verbose_name="Categoría"),
        ),
        migrations.AlterField(
            model_name="cargoshoras_cenpe",
            name="condicion_actividad",
            field=models.CharField(max_length=255, verbose_name="Condicion_Actividad"),
        ),
        migrations.AlterField(
            model_name="cargoshoras_cenpe",
            name="funciones",
            field=models.CharField(max_length=255, verbose_name="Funciones"),
        ),
        migrations.AlterField(
            model_name="cargoshoras_cenpe",
            name="jornada",
            field=models.CharField(max_length=50, verbose_name="Jornada"),
        ),
        migrations.AlterField(
            model_name="cargoshoras_cenpe",
            name="nivel_cargohora",
            field=models.CharField(max_length=255, verbose_name="Nivel_Cargo_Hora"),
        ),
        migrations.AlterField(
            model_name="cargoshoras_cenpe",
            name="situacion_revista",
            field=models.CharField(max_length=150, verbose_name="Situacion_Revista"),
        ),
        migrations.AlterField(
            model_name="cargoshoras_cenpe",
            name="zona",
            field=models.CharField(max_length=150, verbose_name="Zona"),
        ),
    ]