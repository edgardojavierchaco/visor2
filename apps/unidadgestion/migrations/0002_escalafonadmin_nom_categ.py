# Generated by Django 5.1.1 on 2025-01-27 19:38

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("unidadgestion", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="escalafonadmin",
            name="nom_categ",
            field=models.CharField(default=1, max_length=255, verbose_name="nom_categ"),
            preserve_default=False,
        ),
    ]
