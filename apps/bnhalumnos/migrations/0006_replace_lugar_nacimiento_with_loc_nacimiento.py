# Generated for BNH Alumnos on 2026-06-01

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("bnhalumnos", "0005_alter_alumno_lugar_nacimiento_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="alumno",
            name="loc_nacimiento",
            field=models.ForeignKey(
                blank=True,
                db_column="loc_nacimiento",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="alumnos_localidad_nacimiento",
                to="bnhpersonas.localidades",
                verbose_name="Localidad de nacimiento",
            ),
        ),
        migrations.RemoveField(
            model_name="alumno",
            name="lugar_nacimiento",
        ),
    ]
