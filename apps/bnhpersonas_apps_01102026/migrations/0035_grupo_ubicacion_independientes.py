from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("bnhpersonas", "0034_ubicacion_multiplan")]

    operations = [
        migrations.AddField(
            model_name="registroactividades",
            name="grupo_ubicacion",
            field=models.UUIDField(
                blank=True,
                db_index=True,
                editable=False,
                null=True,
            ),
        ),
    ]
