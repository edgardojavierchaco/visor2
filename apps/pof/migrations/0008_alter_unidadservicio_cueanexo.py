# Generated by Django 5.1.1 on 2024-12-17 17:13

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pof", "0007_detalleasignacionpof_cant_car_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="unidadservicio",
            name="cueanexo",
            field=models.CharField(max_length=9, verbose_name="Cueanexo"),
        ),
    ]
