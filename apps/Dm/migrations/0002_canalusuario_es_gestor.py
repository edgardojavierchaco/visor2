# Generated by Django 4.2.5 on 2024-09-28 02:11

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("Dm", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="canalusuario",
            name="es_gestor",
            field=models.BooleanField(default=False),
        ),
    ]
