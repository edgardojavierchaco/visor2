from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("bnhpersonas", "0033_id_puesto"),
    ]

    operations = [
        migrations.AddField(
            model_name="registroactividades",
            name="seccion_multiple",
            field=models.BooleanField(
                choices=[(False, "NO"), (True, "SÍ")],
                default=False,
            ),
        ),
    ]
