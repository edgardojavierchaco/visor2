from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("bnhpersonas", "0036_simplifica_tipo_ubicacion"),
    ]

    operations = [
        migrations.AlterField(
            model_name="registroactividades",
            name="ceic",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="bnhpersonas.nomencladorceic",
            ),
        ),
    ]
