from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("bnhpersonas", "0017_modalidadnivelceic"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name="personas",
                    name="archivada",
                    field=models.BooleanField(default=False),
                ),
            ],
            database_operations=[],
        ),
    ]
