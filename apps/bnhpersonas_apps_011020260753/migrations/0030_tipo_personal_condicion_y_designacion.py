from django.db import migrations, models
import django.db.models.deletion


def preparar_tipos_personal(apps, schema_editor):
    TipoPersonal = apps.get_model('bnhpersonas', 'TipoPersonal')
    # Asegurar las dos categorías básicas. Si hubo duplicados por importación,
    # conservar la fila de menor PK antes de aplicar unique(c_tpersonal).
    for codigo, descripcion in ((1, 'DOCENTE'), (2, 'NO DOCENTE')):
        filas = list(
            TipoPersonal.objects.filter(c_tpersonal=codigo).order_by('pk')
        )
        if not filas:
            TipoPersonal.objects.create(c_tpersonal=codigo, descripcion=descripcion)
        else:
            principal = filas[0]
            if principal.descripcion != descripcion:
                principal.descripcion = descripcion
                principal.save(update_fields=['descripcion'])
            for duplicada in filas[1:]:
                duplicada.delete()



def renombrar_objetos_condicion_legacy(apps, schema_editor):
    """
    Rename the PostgreSQL objects left with the old cond_actividad name
    after RenameField.

    PostgreSQL renames the column, but existing index/constraint names can
    retain the old identifier. The new cond_actividad ForeignKey would then
    try to create objects with the same names.
    """
    connection = schema_editor.connection
    qn = connection.ops.quote_name

    with connection.cursor() as cursor:
        # Resolve the schema containing registro_actividades through search_path.
        cursor.execute(
            """
            SELECT n.nspname
            FROM pg_class t
            JOIN pg_namespace n ON n.oid = t.relnamespace
            WHERE t.oid = to_regclass('registro_actividades')
            """
        )
        row = cursor.fetchone()
        if not row:
            return

        schema = row[0]

        # Rename any old index whose name still refers to cond_actividad_id.
        cursor.execute(
            """
            SELECT idx.relname
            FROM pg_index i
            JOIN pg_class idx ON idx.oid = i.indexrelid
            WHERE i.indrelid = to_regclass('registro_actividades')
              AND idx.relname LIKE 'registro_actividades_cond_actividad_id%%'
            ORDER BY idx.relname
            """
        )
        old_indexes = [r[0] for r in cursor.fetchall()]

        for pos, old_name in enumerate(old_indexes, start=1):
            new_name = (
                "bnh_regact_cond_legacy_idx"
                if pos == 1
                else f"bnh_regact_cond_legacy_idx_{pos}"
            )
            cursor.execute(
                f"ALTER INDEX {qn(schema)}.{qn(old_name)} "
                f"RENAME TO {qn(new_name)}"
            )

        # Rename the old FK constraint as well, because the new FK can
        # otherwise generate the same automatic constraint name.
        cursor.execute(
            """
            SELECT conname
            FROM pg_constraint
            WHERE conrelid = to_regclass('registro_actividades')
              AND contype = 'f'
              AND conname LIKE 'registro_actividades_cond_actividad_id%%'
            ORDER BY conname
            """
        )
        old_constraints = [r[0] for r in cursor.fetchall()]

        for pos, old_name in enumerate(old_constraints, start=1):
            new_name = (
                "bnh_regact_cond_legacy_fk"
                if pos == 1
                else f"bnh_regact_cond_legacy_fk_{pos}"
            )
            cursor.execute(
                f"ALTER TABLE {qn(schema)}.{qn('registro_actividades')} "
                f"RENAME CONSTRAINT {qn(old_name)} TO {qn(new_name)}"
            )


def migrar_actividades(apps, schema_editor):
    Registro = apps.get_model('bnhpersonas', 'RegistroActividades')
    CondLegacy = apps.get_model('bnhpersonas', 'CondicionActividad')
    CondNueva = apps.get_model('bnhpersonas', 'CondicionActividadNombre')

    # Migrar Tipo de personal y, cuando sea posible, la condición histórica.
    legacy_cache = {
        obj.pk: obj.descrip_condicion
        for obj in CondLegacy.objects.all()
    }

    for actividad in Registro.objects.all().iterator(chunk_size=1000):
        categoria = str(getattr(actividad, 'categoria', '') or '').strip().upper()
        codigo = 2 if categoria == 'NO DOCENTE' else 1

        updates = {
            'tipo_personal_id': codigo,
        }

        legacy_id = getattr(actividad, 'cond_actividad_legacy_id', None)
        descripcion = legacy_cache.get(legacy_id)
        if descripcion and actividad.sit_revista_id:
            candidato = (
                CondNueva.objects
                .filter(
                    t_personal=codigo,
                    sit_rev=actividad.sit_revista_id,
                    denominacion__iexact=descripcion.strip(),
                )
                .order_by('pk')
                .first()
            )
            if candidato:
                updates['cond_actividad_id'] = candidato.pk

        Registro.objects.filter(pk=actividad.pk).update(**updates)


def revertir_tipo_personal(apps, schema_editor):
    Registro = apps.get_model('bnhpersonas', 'RegistroActividades')
    for actividad in Registro.objects.all().iterator(chunk_size=1000):
        categoria = 'NO DOCENTE' if actividad.tipo_personal_id == 2 else 'DOCENTE'
        Registro.objects.filter(pk=actividad.pk).update(categoria=categoria)


class Migration(migrations.Migration):
    dependencies = [
        ('bnhpersonas', '0029_tipopersonal_condicionactividadnombre_t_personal'),
    ]

    operations = [
        migrations.RunPython(preparar_tipos_personal, migrations.RunPython.noop),
        # El campo será destino de una FK por c_tpersonal.
        migrations.AlterField(
            model_name='tipopersonal',
            name='c_tpersonal',
            field=models.SmallIntegerField(unique=True),
        ),
        migrations.AlterModelOptions(
            name='tipopersonal',
            options={
                'ordering': ('c_tpersonal',),
                'verbose_name': 'Tipo Personal',
                'verbose_name_plural': 'Tipos Personales',
            },
        ),
        migrations.AlterModelOptions(
            name='condicionactividadnombre',
            options={
                'ordering': ('denominacion', 'c_nomen', 'pk'),
                'verbose_name': 'Condicion Actividad Nombre',
                'verbose_name_plural': 'Condiciones Actividad Nombres',
            },
        ),
        migrations.AddIndex(
            model_name='condicionactividadnombre',
            index=models.Index(
                fields=['t_personal', 'sit_rev'],
                name='bnh_cond_tipo_sit_idx',
            ),
        ),
        migrations.AddField(
            model_name='registroactividades',
            name='tipo_personal',
            field=models.ForeignKey(
                blank=True,
                db_column='c_tpersonal',
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='actividades',
                to='bnhpersonas.tipopersonal',
                to_field='c_tpersonal',
            ),
        ),
        migrations.RenameField(
            model_name='registroactividades',
            old_name='cond_actividad',
            new_name='cond_actividad_legacy',
        ),
        migrations.AlterField(
            model_name='registroactividades',
            name='cond_actividad_legacy',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='+',
                to='bnhpersonas.condicionactividad',
            ),
        ),
        # PostgreSQL puede conservar los nombres físicos antiguos del índice
        # y de la FK tras RenameField. Se renombran antes de crear el nuevo
        # cond_actividad para evitar DuplicateTable/DuplicateObject.
        migrations.RunPython(
            renombrar_objetos_condicion_legacy,
            migrations.RunPython.noop,
        ),
        migrations.AddField(
            model_name='registroactividades',
            name='cond_actividad',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='actividades',
                to='bnhpersonas.condicionactividadnombre',
            ),
        ),
        migrations.RunPython(
            migrar_actividades,
            revertir_tipo_personal,
        ),
        migrations.AlterField(
            model_name='registroactividades',
            name='tipo_personal',
            field=models.ForeignKey(
                db_column='c_tpersonal',
                on_delete=django.db.models.deletion.PROTECT,
                related_name='actividades',
                to='bnhpersonas.tipopersonal',
                to_field='c_tpersonal',
            ),
        ),
        migrations.RemoveField(
            model_name='registroactividades',
            name='categoria',
        ),
        migrations.RemoveField(
            model_name='registroactividades',
            name='designacion',
        ),
    ]
