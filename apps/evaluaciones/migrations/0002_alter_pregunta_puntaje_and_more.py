# Generated by Django 5.1.1 on 2024-12-19 12:32

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("evaluaciones", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="pregunta",
            name="puntaje",
            field=models.PositiveIntegerField(),
        ),
        migrations.AlterField(
            model_name="pregunta",
            name="respuesta_correcta",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="pregunta",
            name="tipo",
            field=models.CharField(
                choices=[("unica", "Opción Única"), ("multiple", "Opción Múltiple")],
                max_length=10,
            ),
        ),
    ]