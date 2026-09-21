from collections import defaultdict

from django.db import migrations, models


NO_CORRESPONDE = "-2"


def _valor(valor):
    if valor is None:
        return NO_CORRESPONDE
    texto = str(valor).strip()
    return texto if texto else NO_CORRESPONDE


def poblar_id_puesto(apps, schema_editor):
    RegistroActividades = apps.get_model("bnhpersonas", "RegistroActividades")
    PuestoSecuencia = apps.get_model("bnhpersonas", "PuestoSecuencia")

    consecutivos = defaultdict(int)

    qs = (
        RegistroActividades.objects
        .select_related("espacio_curricular")
        .order_by("pk")
    )

    for actividad in qs.iterator(chunk_size=1000):
        if actividad.espacio_curricular_id:
            espacio_obj = actividad.espacio_curricular
            espacio = _valor(
                getattr(espacio_obj, "id_espacio_curricular", None)
            )
        else:
            espacio = NO_CORRESPONDE

        componentes = (
            str(actividad.cueanexo or "").strip(),
            _valor(actividad.nivel_curricular_id),
            _valor(actividad.titulacion),
            espacio,
            _valor(actividad.grado_anio_id),
            _valor(actividad.secciones_id),
            _valor(actividad.ceic_id),
        )

        puesto_base = "_".join(componentes)
        consecutivos[puesto_base] += 1
        consecutivo = consecutivos[puesto_base]
        id_puesto = f"{puesto_base}_{consecutivo:04d}"

        RegistroActividades.objects.filter(pk=actividad.pk).update(
            puesto_base=puesto_base,
            puesto_consecutivo=consecutivo,
            id_puesto=id_puesto,
        )

    PuestoSecuencia.objects.bulk_create(
        [
            PuestoSecuencia(
                puesto_base=puesto_base,
                ultimo_consecutivo=ultimo,
            )
            for puesto_base, ultimo in consecutivos.items()
        ],
        batch_size=1000,
    )


class Migration(migrations.Migration):

    dependencies = [
        ("bnhpersonas", "0032_alinea_estado_tipoos"),
    ]

    operations = [
        migrations.CreateModel(
            name="PuestoSecuencia",
            fields=[
                (
                    "puesto_base",
                    models.CharField(max_length=160, primary_key=True, serialize=False),
                ),
                (
                    "ultimo_consecutivo",
                    models.PositiveIntegerField(default=0),
                ),
                (
                    "actualizado_en",
                    models.DateTimeField(auto_now=True),
                ),
            ],
            options={
                "verbose_name": "Secuencia de puesto",
                "verbose_name_plural": "Secuencias de puestos",
                "db_table": "puesto_secuencia",
            },
        ),
        migrations.AddField(
            model_name="registroactividades",
            name="puesto_base",
            field=models.CharField(
                blank=True,
                db_index=True,
                max_length=160,
                null=True,
                editable=False,
            ),
        ),
        migrations.AddField(
            model_name="registroactividades",
            name="puesto_consecutivo",
            field=models.PositiveIntegerField(
                blank=True,
                null=True,
                editable=False,
            ),
        ),
        migrations.AddField(
            model_name="registroactividades",
            name="id_puesto",
            field=models.CharField(
                blank=True,
                db_index=True,
                max_length=180,
                null=True,
                editable=False,
            ),
        ),
        migrations.RunPython(
            poblar_id_puesto,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="registroactividades",
            name="puesto_base",
            field=models.CharField(
                db_index=True,
                max_length=160,
                editable=False,
            ),
        ),
        migrations.AlterField(
            model_name="registroactividades",
            name="puesto_consecutivo",
            field=models.PositiveIntegerField(
                editable=False,
            ),
        ),
        migrations.AlterField(
            model_name="registroactividades",
            name="id_puesto",
            field=models.CharField(
                db_index=True,
                max_length=180,
                editable=False,
            ),
        ),
        migrations.AddConstraint(
            model_name="registroactividades",
            constraint=models.CheckConstraint(
                condition=models.Q(puesto_consecutivo__gte=1),
                name="bnh_puesto_consecutivo_positivo",
            ),
        ),
        migrations.AddConstraint(
            model_name="registroactividades",
            constraint=models.UniqueConstraint(
                fields=("id_puesto",),
                name="bnh_id_puesto_unico",
            ),
        ),
        migrations.AddConstraint(
            model_name="registroactividades",
            constraint=models.UniqueConstraint(
                fields=("puesto_base", "puesto_consecutivo"),
                name="bnh_puesto_base_consecutivo_unico",
            ),
        ),
    ]
