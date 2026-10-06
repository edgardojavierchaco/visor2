from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("bnhpersonas", "0037_ceic_opcional_no_corresponde"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ConstanciaServicio",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("token", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("numero", models.CharField(blank=True, db_index=True, max_length=32, unique=True)),
                ("cueanexo", models.CharField(db_index=True, max_length=9)),
                ("nom_est", models.CharField(max_length=255)),
                ("fecha_emision", models.DateTimeField(db_index=True, default=django.utils.timezone.now, editable=False)),
                ("estado", models.CharField(choices=[("VIGENTE", "Vigente"), ("ANULADA", "Anulada")], db_index=True, default="VIGENTE", max_length=10)),
                ("snapshot", models.JSONField(default=dict)),
                ("hash_contenido", models.CharField(db_index=True, editable=False, max_length=64)),
                ("hash_pdf", models.CharField(blank=True, default="", editable=False, max_length=64)),
                ("fecha_anulacion", models.DateTimeField(blank=True, null=True)),
                ("motivo_anulacion", models.TextField(blank=True, default="")),
                ("persona", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="constancias_servicio", to="bnhpersonas.personas")),
                ("usuario_anulacion", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="constancias_bnh_anuladas", to=settings.AUTH_USER_MODEL)),
                ("usuario_emisor", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="constancias_bnh_emitidas", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "constancia_servicio",
                "ordering": ("-fecha_emision", "-pk"),
            },
        ),
        migrations.AddIndex(
            model_name="constanciaservicio",
            index=models.Index(fields=["cueanexo", "estado"], name="bnh_const_cue_estado_idx"),
        ),
        migrations.AddIndex(
            model_name="constanciaservicio",
            index=models.Index(fields=["persona", "estado"], name="bnh_const_persona_idx"),
        ),
        migrations.AddConstraint(
            model_name="constanciaservicio",
            constraint=models.CheckConstraint(condition=models.Q(estado__in=["VIGENTE", "ANULADA"]), name="bnh_constancia_estado_valido"),
        ),
    ]
