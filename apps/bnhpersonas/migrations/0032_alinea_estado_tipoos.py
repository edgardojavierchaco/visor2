from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        (
            "bnhpersonas",
            "0031_concurrencia_robustez",
        ),
    ]

    operations = [

        # ========================================================
        # TipoOS
        # ========================================================
        #
        # La tabla física correcta ya existe:
        #
        #     bnh.tipo_obra_social_bnh
        #
        # El modelo TipoOS es managed=False.
        #
        # Algunas migraciones históricas dejaron en el estado
        # interno de Django el nombre:
        #
        #     tipo_obra_social
        #
        # NO queremos renombrar ninguna tabla PostgreSQL.
        #
        # Sólo sincronizamos el estado de migraciones con el
        # modelo actual.
        # ========================================================

        migrations.SeparateDatabaseAndState(

            database_operations=[
                # Intencionalmente vacío.
                #
                # No ejecutar ALTER TABLE.
                # La tabla física correcta ya existe.
            ],

            state_operations=[
                migrations.AlterModelTable(
                    name="tipoos",
                    table="tipo_obra_social_bnh",
                ),
            ],
        ),

    ]