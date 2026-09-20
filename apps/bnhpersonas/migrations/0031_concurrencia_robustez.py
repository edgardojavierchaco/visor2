from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("bnhpersonas", "0030_tipo_personal_condicion_y_designacion"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="RevisionCatalogos",
            fields=[
                ("id", models.PositiveSmallIntegerField(default=1, editable=False, primary_key=True, serialize=False)),
                ("version", models.PositiveBigIntegerField(default=1)),
                ("actualizado_en", models.DateTimeField(auto_now=True)),
                ("actualizado_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "bnh_revision_catalogos"},
        ),
        migrations.AddConstraint(
            model_name="revisioncatalogos",
            constraint=models.CheckConstraint(
                condition=models.Q(version__gte=1),
                name="bnh_catalog_version_positiva",
            ),
        ),

        # Auditoría por operación lógica / request.
        migrations.AddField(
            model_name="eventoauditoria",
            name="operacion_id",
            field=models.UUIDField(blank=True, db_index=True, null=True),
        ),

        # Evita índices redundantes preexistentes. DNI y teléfono conservan
        # sus índices de db_index=True; CUIL queda cubierto por el UNIQUE parcial.
        migrations.RemoveIndex(
            model_name="personas",
            name="personas_dni_9bfd07_idx",
        ),
        migrations.RemoveIndex(
            model_name="personas",
            name="personas_cuil_ef5d98_idx",
        ),
        migrations.RemoveIndex(
            model_name="personas",
            name="personas_telefon_948765_idx",
        ),
        migrations.AlterField(
            model_name="personas",
            name="cuil",
            field=models.CharField(blank=True, max_length=11, null=True),
        ),

        # Constraints defensivos de persona.
        migrations.AddConstraint(
            model_name="personas",
            constraint=models.CheckConstraint(
                condition=models.Q(estado__in=["ACTIVO", "PASIVO"]),
                name="bnh_persona_estado_valido",
            ),
        ),
        migrations.AddConstraint(
            model_name="personas",
            constraint=models.CheckConstraint(
                condition=models.Q(version__gte=1),
                name="bnh_persona_version_positiva",
            ),
        ),
        migrations.AddIndex(
            model_name="personas",
            index=models.Index(
                fields=["archivada", "apellido", "nombre"],
                name="bnh_persona_lista_idx",
            ),
        ),

        # Índices y constraints defensivos de actividades.
        migrations.AddIndex(
            model_name="registroactividades",
            index=models.Index(
                fields=["persona", "cueanexo", "eliminado"],
                name="bnh_persona_cue_del_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="registroactividades",
            index=models.Index(
                fields=["persona", "eliminado"],
                name="bnh_persona_del_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="registroactividades",
            index=models.Index(
                fields=[
                    "persona",
                    "cueanexo",
                    "tipo_personal",
                    "ceic",
                    "sit_revista",
                    "t_designacion",
                    "f_desde",
                ],
                name="bnh_posible_dup_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="registroactividades",
            constraint=models.CheckConstraint(
                condition=models.Q(estado__in=["ACTIVO", "INACTIVO"]),
                name="bnh_actividad_estado_valido",
            ),
        ),
        migrations.AddConstraint(
            model_name="registroactividades",
            constraint=models.CheckConstraint(
                condition=models.Q(validacion__in=["BORRADOR", "VALIDADO", "OBSERVADO"]),
                name="bnh_validacion_valida",
            ),
        ),
        migrations.AddConstraint(
            model_name="registroactividades",
            constraint=models.CheckConstraint(
                condition=models.Q(version__gte=1),
                name="bnh_actividad_version_positiva",
            ),
        ),

        # Moderniza unique_together a constraints nombradas.
        migrations.AlterUniqueTogether(
            name="actividadsede",
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name="actividadsede",
            constraint=models.UniqueConstraint(
                fields=("actividad", "cueanexo"),
                name="bnh_actividad_sede_unica",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="horarioactividad",
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name="horarioactividad",
            constraint=models.UniqueConstraint(
                fields=("actividad_sede", "dia", "hora_desde", "hora_hasta"),
                name="bnh_horario_unico",
            ),
        ),

        # Índices de auditoría para reconstruir eventos por objeto/CUE.
        migrations.AddIndex(
            model_name="eventoauditoria",
            index=models.Index(
                fields=["entidad", "objeto_id", "-fecha"],
                name="bnh_audit_obj_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="eventoauditoria",
            index=models.Index(
                fields=["cueanexo", "-fecha"],
                name="bnh_audit_cue_idx",
            ),
        ),
    ]
