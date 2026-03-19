from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("infraestructura", "0004_vcapaunicaofertascuicuof"),
    ]

    operations = [
        # Alteramos departamentos para que acepte NULL y esté en blanco
        migrations.AlterField(
            model_name="datosescuela",
            name="departamentos",  # Debe coincidir con el nombre en tu modelo
            field=models.CharField(
                max_length=255,
                verbose_name="Departamento",
                blank=True,
                null=True,
            ),
        ),
        # Alteramos localidades para que acepte NULL y esté en blanco
        migrations.AlterField(
            model_name="datosescuela",
            name="localidades",  # Debe coincidir con el nombre en tu modelo
            field=models.CharField(
                max_length=255,
                verbose_name="Localidad",
                blank=True,
                null=True,
            ),
        ),
    ]