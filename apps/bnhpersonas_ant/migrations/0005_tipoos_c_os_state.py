from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("bnhpersonas",
	"0005_alter_documentotipo_table_alter_estadosciviles_table_and_more",
	),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.RenameField(
                    model_name="tipoos",
                    old_name="c_tipo_os",
                    new_name="c_os",
                ),
            ],
        ),
    ]
