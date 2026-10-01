from django.db import migrations, models
import django.db.models.deletion


def ensure_modalidad1_columns(apps, schema_editor):
    """
    Los CSV nuevos de grado_anio y Secciones utilizan c_modalidad1.
    La migración 0020 había incorporado c_modalidad.

    Esta función NO elimina c_modalidad: crea c_modalidad1 si falta y copia
    el valor anterior sólo cuando el nuevo está vacío. Es deliberadamente
    conservadora para bases que fueron cargadas manualmente desde CSV.
    """
    qn = schema_editor.quote_name
    connection = schema_editor.connection

    for model_name in ("Grado_anio", "Secciones"):
        model = apps.get_model("bnhpersonas", model_name)
        table = model._meta.db_table

        with connection.cursor() as cursor:
            columns = {
                c.name: c
                for c in connection.introspection.get_table_description(cursor, table)
            }

        if "c_modalidad1" not in columns:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"ALTER TABLE {qn(table)} ADD COLUMN {qn('c_modalidad1')} integer NULL"
                )

        if "c_modalidad" in columns:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"UPDATE {qn(table)} "
                    f"SET {qn('c_modalidad1')} = {qn('c_modalidad')} "
                    f"WHERE {qn('c_modalidad1')} IS NULL"
                )



def reset_docente_validation(apps, schema_editor):
    RegistroActividades = apps.get_model("bnhpersonas", "RegistroActividades")
    RegistroActividades.objects.filter(
        categoria="DOCENTE",
        eliminado=False,
    ).update(validacion="BORRADOR")


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("bnhpersonas", "0025_titulacionfp"),
    ]

    operations = [
        migrations.RunPython(ensure_modalidad1_columns, noop),
        
        migrations.AlterModelOptions(
            name="modalidadtipo",
            options={
                "verbose_name": "Modalidad Tipo",
                "verbose_name_plural": "Modalidades Tipo",
                "ordering": [
                    "orden",
                    "descripcion",
                ],
            },
        ),

        migrations.AlterModelOptions(
            name="nivelserviciotipo",
            options={
                "verbose_name": "Nivel Servicio Tipo",
                "verbose_name_plural": "Niveles Servicio Tipo",
                "ordering": [
                    "c_modalidad1",
                    "c_nivel",
                ],
            },
        ),

        # Sólo se actualiza el estado de Django. La columna física nueva ya fue
        # creada/normalizada arriba y se conserva c_modalidad por compatibilidad.
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="DROP INDEX IF EXISTS bnh_grado_parent_idx; DROP INDEX IF EXISTS bnh_seccion_parent_idx;",
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
            state_operations=[
                migrations.RemoveIndex(
                    model_name="grado_anio",
                    name="bnh_grado_parent_idx",
                ),
                migrations.RemoveIndex(
                    model_name="secciones",
                    name="bnh_seccion_parent_idx",
                ),
                migrations.RenameField(
                    model_name="grado_anio",
                    old_name="c_modalidad",
                    new_name="c_modalidad1",
                ),
                migrations.RenameField(
                    model_name="secciones",
                    old_name="c_modalidad",
                    new_name="c_modalidad1",
                ),
            ],
        ),

        migrations.AddIndex(
            model_name="grado_anio",
            index=models.Index(
                fields=["c_modalidad1", "c_niv_grado", "estado"],
                name="bnh_grado_parent1_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="secciones",
            index=models.Index(
                fields=["c_modalidad1", "c_niv_seccion", "estado"],
                name="bnh_seccion_parent1_idx",
            ),
        ),

        migrations.AddField(
            model_name="registroactividades",
            name="modalidad_curricular",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="bnhpersonas.modalidadtipo",
            ),
        ),
        migrations.AddField(
            model_name="registroactividades",
            name="nivel_curricular",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="bnhpersonas.nivelserviciotipo",
            ),
        ),
        migrations.AddField(
            model_name="registroactividades",
            name="titulacion",
            field=models.BigIntegerField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="registroactividades",
            name="titulacion_fuente",
            field=models.CharField(
                blank=True,
                choices=[
                    ("NOMBRE", "Titulación nombre"),
                    ("SUPERIOR", "Titulación superior"),
                    ("FP", "Titulación formación profesional"),
                ],
                default="",
                max_length=12,
            ),
        ),
        migrations.AddField(
            model_name="registroactividades",
            name="espacio_curricular",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="bnhpersonas.espaciocurricularnombre",
            ),
        ),
        migrations.AddIndex(
            model_name="registroactividades",
            index=models.Index(
                fields=["modalidad_curricular", "nivel_curricular"],
                name="bnh_curricular_idx",
            ),
        ),
        # Los cargos docentes ya existentes no poseen todavía los nuevos datos
        # curriculares; vuelven a BORRADOR hasta que sean completados y validados.
        migrations.RunPython(reset_docente_validation, noop),
    ]
