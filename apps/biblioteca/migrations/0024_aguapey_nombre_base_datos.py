from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("biblioteca", "0023_bibliotecarioscue_turno_bnh_and_more"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="aguapey",
            options={
                "verbose_name": "Base de datos utilizada",
                "verbose_name_plural": "Bases de datos utilizadas",
            },
        ),
        migrations.AddField(
            model_name="aguapey",
            name="nombre_base_datos",
            field=models.CharField(
                max_length=120,
                blank=True,
                default="",
                verbose_name="Base de datos utilizada",
            ),
        ),
    ]
