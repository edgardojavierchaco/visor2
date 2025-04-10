# Generated by Django 5.1.1 on 2025-01-27 19:33

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="CargosCeic",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                ("nivel", models.CharField(max_length=255, verbose_name="nivel")),
                ("ceic_id", models.IntegerField(verbose_name="ceic_id")),
                (
                    "descripcion_ceic",
                    models.CharField(max_length=255, verbose_name="descripcion_ceic"),
                ),
                ("estado", models.BooleanField(default=True, verbose_name="estado")),
                ("puntos", models.IntegerField(verbose_name="puntos")),
            ],
            options={
                "db_table": "ceic_puntos",
                "managed": False,
            },
        ),
        migrations.CreateModel(
            name="FuncionesDoc",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                ("funcion", models.CharField(max_length=100, verbose_name="funcion")),
            ],
            options={
                "db_table": "funciones",
                "managed": False,
            },
        ),
        migrations.CreateModel(
            name="EscalafonAdmin",
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
                ("categoria", models.IntegerField(verbose_name="categoria")),
                (
                    "descripcion",
                    models.CharField(max_length=100, verbose_name="descripcion"),
                ),
            ],
            options={
                "verbose_name": "Escalafon_Admin",
                "verbose_name_plural": "Escalafones_Admin",
                "db_table": "Escalafon_Admin",
            },
        ),
        migrations.CreateModel(
            name="PersonalDocCentral",
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
                    "t_dni",
                    models.CharField(
                        choices=[
                            ("DNI", "DNI"),
                            ("CI", "CI"),
                            ("LC", "LC"),
                            ("LE", "LE"),
                            ("CEDULA MERCOSUR", "CEDULA MERCOSUR"),
                            ("PASAPORTE EXTRANJERO", "PASAPORTE EXTRANJERO"),
                            ("CI EXTRANJERA", "CI EXTRANJERA"),
                            ("OTRO DOCUMENTO EXTRANJERO", "OTRO DOCUMENTO EXTRANJERO"),
                        ],
                        verbose_name="T_DNI",
                    ),
                ),
                ("dni", models.CharField(max_length=8, verbose_name="DNI")),
                ("cuil", models.CharField(max_length=11, verbose_name="CUIL")),
                ("apellido", models.CharField(max_length=255, verbose_name="Apellido")),
                ("nombres", models.CharField(max_length=255, verbose_name="Nombres")),
                (
                    "f_nac",
                    models.DateField(default="1900-01-01", verbose_name="Fecha_Nac"),
                ),
                (
                    "sexo",
                    models.CharField(
                        choices=[("Masculino", "Masculino"), ("Femenino", "Femenino")],
                        max_length=9,
                        verbose_name="Sexo",
                    ),
                ),
                (
                    "nivelmod",
                    models.CharField(
                        choices=[
                            ("INICIAL", "INICIAL"),
                            ("PRIMARIO", "PRIMARIO"),
                            ("SECUNDARIO", "SECUNDARIO"),
                            ("TÉCNICA", "TÉCNICA"),
                            ("SUPERIOR", "SUPERIOR"),
                            ("ARTÍSTICA", "ARTÍSTICA"),
                            ("BIBLIOTECAS", "BIBLIOTECAS"),
                            ("SERVICIOS TÉCNICOS", "SERVICIOS TÉCNICOS"),
                            ("EDUCACIÓN FÍSICA", "EDUCACIÓN FÍSICA"),
                            ("ESPECIAL", "ESPECIAL"),
                        ],
                        max_length=25,
                        verbose_name="Nivel_Mod",
                    ),
                ),
                (
                    "sector",
                    models.CharField(
                        choices=[
                            ("Gestión Estatal", "Gestión Estatal"),
                            ("Gestión Social", "Gestión Social"),
                            ("Gestión Comunitaria", "Gestión Comunitaria"),
                            ("Gestión Privada", "Gestión Privada"),
                            ("Multigestión", "Multigestión"),
                        ],
                        max_length=50,
                        verbose_name="Sector",
                    ),
                ),
                (
                    "sit_revista",
                    models.CharField(
                        choices=[
                            ("Titular", "Titular"),
                            ("Interino", "Interino"),
                            ("Suplente", "Suplente"),
                        ],
                        max_length=100,
                        verbose_name="Sit_Revista",
                    ),
                ),
                (
                    "f_designacion",
                    models.DateField(
                        default="1900-01-01", verbose_name="Fecha_Designacion"
                    ),
                ),
                (
                    "f_desde",
                    models.DateField(default="1900-01-01", verbose_name="Fecha_Desde"),
                ),
                (
                    "f_hasta",
                    models.DateField(default="2059-12-31", verbose_name="Fecha_Hasta"),
                ),
                (
                    "carga_horaria_sem",
                    models.DecimalField(
                        decimal_places=2, max_digits=4, verbose_name="Horas_Semanales"
                    ),
                ),
                ("cuof", models.IntegerField(verbose_name="CUOF")),
                ("cuof_anexo", models.IntegerField(verbose_name="Anexo CUOF")),
                ("email", models.EmailField(max_length=255, verbose_name="Correo")),
                ("telefono", models.CharField(max_length=11, verbose_name="Teléfono")),
                (
                    "region",
                    models.CharField(
                        choices=[
                            ("R.E. 1", "R.E. 1"),
                            ("R.E. 2", "R.E. 2"),
                            ("R.E. 3", "R.E. 3"),
                            ("R.E. 4-A", "R.E. 4-A"),
                            ("R.E. 4-B", "R.E. 4-B"),
                            ("R.E. 5", "R.E. 5"),
                            ("R.E. 6", "R.E. 6"),
                            ("R.E. 7", "R.E. 7"),
                            ("R.E. 8-A", "R.E. 8-A"),
                            ("R.E. 8-B", "R.E. 8-B"),
                            ("R.E. 9", "R.E. 9"),
                            ("R.E. 10-A", "R.E. 10-A"),
                            ("R.E. 10-B", "R.E. 10-B"),
                            ("R.E. 10-C", "R.E. 10-C"),
                            ("SUB. R.E. 1-A", "SUB. R.E. 1-A"),
                            ("SUB. R.E. 1-B", "SUB. R.E. 1-B"),
                            ("SUB. R.E. 2", "SUB. R.E. 2"),
                            ("SUB. R.E. 3", "SUB. R.E. 3"),
                            ("SUB. R.E. 5", "SUB. R.E. 5"),
                        ],
                        max_length=100,
                        verbose_name="Regional",
                    ),
                ),
                (
                    "cargo",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="unidadgestion.cargosceic",
                        verbose_name="Cargos",
                    ),
                ),
                (
                    "nom_funcion",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="unidadgestion.funcionesdoc",
                        verbose_name="nom_funcion",
                    ),
                ),
            ],
            options={
                "verbose_name": "Personal_Doc_Central",
                "verbose_name_plural": "Personales_Doc_Centrales",
                "db_table": "Personal_Doc_Central",
            },
        ),
        migrations.CreateModel(
            name="PersonalNoDocCentral",
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
                    "t_dni",
                    models.CharField(
                        choices=[
                            ("DNI", "DNI"),
                            ("CI", "CI"),
                            ("LC", "LC"),
                            ("LE", "LE"),
                            ("CEDULA MERCOSUR", "CEDULA MERCOSUR"),
                            ("PASAPORTE EXTRANJERO", "PASAPORTE EXTRANJERO"),
                            ("CI EXTRANJERA", "CI EXTRANJERA"),
                            ("OTRO DOCUMENTO EXTRANJERO", "OTRO DOCUMENTO EXTRANJERO"),
                        ],
                        verbose_name="T_DNI",
                    ),
                ),
                ("dni", models.CharField(max_length=8, verbose_name="DNI")),
                ("cuil", models.CharField(max_length=11, verbose_name="CUIL")),
                ("apellido", models.CharField(max_length=255, verbose_name="Apellido")),
                ("nombres", models.CharField(max_length=255, verbose_name="Nombres")),
                (
                    "f_nac",
                    models.DateField(default="1900-01-01", verbose_name="Fecha_Nac"),
                ),
                (
                    "sexo",
                    models.CharField(
                        choices=[("Masculino", "Masculino"), ("Femenino", "Femenino")],
                        max_length=9,
                        verbose_name="Sexo",
                    ),
                ),
                (
                    "sit_nom",
                    models.CharField(
                        choices=[
                            ("Planta Permanente", "Planta Permanente"),
                            ("Contratado", "Contratado"),
                            ("Jornalizado", "Jornalizado"),
                        ],
                        max_length=100,
                        verbose_name="Sit_Nombramiento",
                    ),
                ),
                (
                    "f_designacion",
                    models.DateField(
                        default="1900-01-01", verbose_name="Fecha_Designacion"
                    ),
                ),
                (
                    "f_desde",
                    models.DateField(default="1900-01-01", verbose_name="Fecha_Desde"),
                ),
                (
                    "f_hasta",
                    models.DateField(default="2059-12-31", verbose_name="Fecha_Hasta"),
                ),
                (
                    "carga_horaria_sem",
                    models.DecimalField(
                        decimal_places=2, max_digits=4, verbose_name="Horas_Semanales"
                    ),
                ),
                ("cuof", models.IntegerField(verbose_name="CUOF")),
                ("cuof_anexo", models.IntegerField(verbose_name="Anexo CUOF")),
                ("email", models.EmailField(max_length=255, verbose_name="Correo")),
                ("telefono", models.CharField(max_length=11, verbose_name="Teléfono")),
                (
                    "region",
                    models.CharField(
                        choices=[
                            ("R.E. 1", "R.E. 1"),
                            ("R.E. 2", "R.E. 2"),
                            ("R.E. 3", "R.E. 3"),
                            ("R.E. 4-A", "R.E. 4-A"),
                            ("R.E. 4-B", "R.E. 4-B"),
                            ("R.E. 5", "R.E. 5"),
                            ("R.E. 6", "R.E. 6"),
                            ("R.E. 7", "R.E. 7"),
                            ("R.E. 8-A", "R.E. 8-A"),
                            ("R.E. 8-B", "R.E. 8-B"),
                            ("R.E. 9", "R.E. 9"),
                            ("R.E. 10-A", "R.E. 10-A"),
                            ("R.E. 10-B", "R.E. 10-B"),
                            ("R.E. 10-C", "R.E. 10-C"),
                            ("SUB. R.E. 1-A", "SUB. R.E. 1-A"),
                            ("SUB. R.E. 1-B", "SUB. R.E. 1-B"),
                            ("SUB. R.E. 2", "SUB. R.E. 2"),
                            ("SUB. R.E. 3", "SUB. R.E. 3"),
                            ("SUB. R.E. 5", "SUB. R.E. 5"),
                        ],
                        max_length=100,
                        verbose_name="Regional",
                    ),
                ),
                (
                    "categoria",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="unidadgestion.escalafonadmin",
                        verbose_name="Categoria",
                    ),
                ),
                (
                    "nom_funcion",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="unidadgestion.funcionesdoc",
                        verbose_name="nom_funcion",
                    ),
                ),
            ],
            options={
                "verbose_name": "Personal_No_Doc_Central",
                "verbose_name_plural": "Personales_No_Doc_Centrales",
                "db_table": "Personal_No_Doc_Central",
            },
        ),
    ]
