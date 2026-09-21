import hashlib

from django.db import migrations, models


def distribuir_tipos_inclusion(apps, schema_editor):
    AlumnoSeccion = apps.get_model("especial", "AlumnoSeccion")
    tipos = ("inclusion_plena", "trayectoria_compartida")

    inscripciones = AlumnoSeccion.objects.filter(
        seccion__oferta__icontains="Integr"
    ).order_by("pk")
    for inscripcion in inscripciones.iterator(chunk_size=500):
        # Distribución pseudoaleatoria reproducible para que la migración sea segura
        # de auditar y no dependa del orden de ejecución ni de la semilla global.
        digest = hashlib.sha256(str(inscripcion.pk).encode("ascii")).digest()
        inscripcion.tipo_inclusion = tipos[digest[0] % len(tipos)]
        inscripcion.save(update_fields=["tipo_inclusion"])


class Migration(migrations.Migration):

    dependencies = [
        ("especial", "0013_renombrar_relacion_alumno_banco"),
    ]

    operations = [
        migrations.AddField(
            model_name="alumnoseccion",
            name="tipo_inclusion",
            field=models.CharField(
                blank=True,
                choices=[
                    ("inclusion_plena", "Inclusión plena"),
                    ("trayectoria_compartida", "Trayectoria compartida"),
                ],
                help_text="Tipo de inclusión para inscripciones de ofertas de Integración.",
                max_length=30,
                null=True,
            ),
        ),
        migrations.RunPython(distribuir_tipos_inclusion, migrations.RunPython.noop),
    ]
