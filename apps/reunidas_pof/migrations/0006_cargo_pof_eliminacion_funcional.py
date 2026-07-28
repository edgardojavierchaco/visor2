from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("reunidas_pof", "0005_alter_reunidapof_nivel"),
    ]

    operations = [
        migrations.AlterField(
            model_name="cargopof",
            name="estado_pof",
            field=models.CharField(
                choices=[
                    ("AFECTADO", "Afectado"),
                    ("DESAFECTADO", "Desafectado"),
                ],
                default="AFECTADO",
                max_length=20,
                verbose_name="Estado POF",
            ),
        ),
        migrations.AlterField(
            model_name="lotecargapof",
            name="tipo_operacion",
            field=models.CharField(
                choices=[
                    ("ALTA", "Alta"),
                    ("MODIFICACION", "Modificación"),
                    ("AFECTACION", "Afectación"),
                    ("DESAFECTACION", "Desafectación"),
                ],
                default="ALTA",
                max_length=40,
                verbose_name="Tipo de operación",
            ),
        ),
        migrations.AlterField(
            model_name="movimientocargopof",
            name="tipo_movimiento",
            field=models.CharField(
                choices=[
                    ("ALTA", "Alta"),
                    ("MODIFICACION", "Modificación"),
                    ("AFECTACION", "Afectación"),
                    ("DESAFECTACION", "Desafectación"),
                ],
                max_length=40,
                verbose_name="Tipo de movimiento",
            ),
        ),
    ]
