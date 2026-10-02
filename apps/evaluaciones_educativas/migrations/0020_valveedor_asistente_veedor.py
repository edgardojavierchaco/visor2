from django.db import migrations, models


def marcar_asistentes_existentes(apps, schema_editor):
    """
    En los establecimientos que ya tienen 2 veedores, el cargado en segundo
    lugar (id mayor) pasa a ser el asistente. Sin esto el UniqueConstraint
    fallaría, porque los dos quedarían con asistente_veedor=False.
    """
    ValVeedor = apps.get_model('evaluaciones_educativas', 'ValVeedor')
    db = schema_editor.connection.alias
    vistos = set()
    for veedor in ValVeedor.objects.using(db).order_by('establecimiento_id', 'pk'):
        if veedor.establecimiento_id in vistos:
            veedor.asistente_veedor = True
            veedor.save(using=db, update_fields=['asistente_veedor'])
        else:
            vistos.add(veedor.establecimiento_id)


class Migration(migrations.Migration):
    dependencies = [
        ("evaluaciones_educativas", "0019_alter_valpersona_cuil"),
    ]

    operations = [
        migrations.AddField(
            model_name="valveedor",
            name="asistente_veedor",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(marcar_asistentes_existentes, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="valveedor",
            constraint=models.UniqueConstraint(
                fields=("establecimiento", "asistente_veedor"),
                name="un_veedor_y_un_asistente_por_establecimiento",
            ),
        ),
    ]
