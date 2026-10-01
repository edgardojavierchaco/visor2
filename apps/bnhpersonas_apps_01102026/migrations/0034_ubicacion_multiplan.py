from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("bnhpersonas", "0033_id_puesto")]

    operations = [
        migrations.AddField(
            model_name="registroactividades",
            name="tipo_ubicacion",
            field=models.CharField(
                choices=[
                    ("UNICA", "Sección única"),
                    ("VARIAS", "Varias secciones independientes"),
                    ("MULTIPLE", "Sección múltiple"),
                ],
                default="UNICA",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="registroactividades",
            name="multiplan",
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name="RegistroActividadUbicacion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("turno", models.CharField(choices=[("MAÑANA", "MAÑANA"), ("MAÑANA EXTENDIDA", "MAÑANA EXTENDIDA"), ("TARDE", "TARDE"), ("TARDE EXTENDIDA", "TARDE EXTENDIDA"), ("NOCHE", "NOCHE"), ("VESPERTINO", "VESPERTINO"), ("DOBLE", "DOBLE"), ("DOBLE EXTENDIDA", "DOBLE EXTENDIDA")], max_length=20)),
                ("orden", models.PositiveSmallIntegerField(default=1)),
                ("actividad", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ubicaciones_curriculares", to="bnhpersonas.registroactividades")),
                ("grado_anio", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="bnhpersonas.grado_anio")),
                ("seccion", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="bnhpersonas.secciones")),
            ],
            options={"db_table": "registro_actividad_ubicacion", "ordering": ["orden", "pk"]},
        ),
        migrations.CreateModel(
            name="RegistroActividadTitulacion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("titulacion", models.BigIntegerField(db_index=True)),
                ("titulacion_fuente", models.CharField(choices=[("NOMBRE", "Titulación nombre"), ("SUPERIOR", "Titulación superior"), ("FP", "Titulación formación profesional")], max_length=12)),
                ("orden", models.PositiveSmallIntegerField(default=1)),
                ("actividad", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="titulaciones_curriculares", to="bnhpersonas.registroactividades")),
            ],
            options={"db_table": "registro_actividad_titulacion", "ordering": ["orden", "pk"]},
        ),
        migrations.AddConstraint(
            model_name="registroactividadubicacion",
            constraint=models.UniqueConstraint(fields=("actividad", "grado_anio", "seccion", "turno"), name="bnh_actividad_ubicacion_unica"),
        ),
        migrations.AddConstraint(
            model_name="registroactividadtitulacion",
            constraint=models.UniqueConstraint(fields=("actividad", "titulacion", "titulacion_fuente"), name="bnh_actividad_titulacion_unica"),
        ),
        migrations.RunSQL(
            sql="INSERT INTO registro_actividad_ubicacion (actividad_id, grado_anio_id, seccion_id, turno, orden) SELECT id, grado_anio_id, secciones_id, turno, 1 FROM registro_actividades WHERE grado_anio_id IS NOT NULL AND secciones_id IS NOT NULL ON CONFLICT DO NOTHING",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql="INSERT INTO registro_actividad_titulacion (actividad_id, titulacion, titulacion_fuente, orden) SELECT id, titulacion, titulacion_fuente, 1 FROM registro_actividades WHERE titulacion IS NOT NULL AND COALESCE(titulacion_fuente, '') <> '' ON CONFLICT DO NOTHING",
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
