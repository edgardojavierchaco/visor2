from django.db import migrations, models


def convertir_varias_en_unica(apps, schema_editor):
    RegistroActividades = apps.get_model("bnhpersonas", "RegistroActividades")
    # Cada integrante de VARIAS ya es un RegistroActividades independiente y
    # conserva su propio id_puesto. Solo cambia la clasificación.
    RegistroActividades.objects.filter(tipo_ubicacion="VARIAS").update(tipo_ubicacion="UNICA")


class Migration(migrations.Migration):

    dependencies = [
        ("bnhpersonas", "0035_grupo_ubicacion_independientes"),
    ]

    operations = [
        migrations.RunPython(convertir_varias_en_unica, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="registroactividades",
            name="grupo_ubicacion",
        ),
        migrations.AlterField(
            model_name="registroactividades",
            name="tipo_ubicacion",
            field=models.CharField(
                choices=[
                    ("UNICA", "Sección única"),
                    ("MULTIPLE", "Sección múltiple"),
                ],
                default="UNICA",
                max_length=10,
            ),
        ),
    ]
