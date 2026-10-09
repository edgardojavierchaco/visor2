from django.db import migrations


MODALIDAD_COMUN = 1
NIVEL_SECUNDARIO_COMUN = 1003
VALOR_NO_CORRESPONDE = -2
TEXTO_NO_CORRESPONDE = "NO CORRESPONDE"


def agregar_no_corresponde(apps, schema_editor):
    TitulacionNombre = apps.get_model(
        "bnhpersonas",
        "TitulacionNombre",
    )
    EspacioCurricularNombre = apps.get_model(
        "bnhpersonas",
        "EspacioCurricularNombre",
    )

    # ------------------------------------------------------------
    # TITULACIÓN
    # Sólo para COMÚN + SECUNDARIO.
    # ------------------------------------------------------------
    TitulacionNombre.objects.get_or_create(
        id_nombre_titulacion=VALOR_NO_CORRESPONDE,
        id_titulacion=VALOR_NO_CORRESPONDE,
        c_nivel_servicio=NIVEL_SECUNDARIO_COMUN,
        c_modalidad1=MODALIDAD_COMUN,
        defaults={
            "descripcion_adicional": "",
            "nombre": TEXTO_NO_CORRESPONDE,
        },
    )

    # Si ya existía con esos códigos, asegurar la denominación.
    TitulacionNombre.objects.filter(
        id_nombre_titulacion=VALOR_NO_CORRESPONDE,
        id_titulacion=VALOR_NO_CORRESPONDE,
        c_nivel_servicio=NIVEL_SECUNDARIO_COMUN,
        c_modalidad1=MODALIDAD_COMUN,
    ).update(
        nombre=TEXTO_NO_CORRESPONDE,
        descripcion_adicional="",
    )

    # ------------------------------------------------------------
    # ESPACIO CURRICULAR
    # Queda asociado exclusivamente a la titulación -2.
    # Por eso sólo aparece cuando se selecciona NO CORRESPONDE
    # como titulación.
    # ------------------------------------------------------------
    EspacioCurricularNombre.objects.get_or_create(
        id_espacio_curricular=VALOR_NO_CORRESPONDE,
        id_titulacion=VALOR_NO_CORRESPONDE,
        id_nombre_espacio_curricular=VALOR_NO_CORRESPONDE,
        defaults={
            "nombre": TEXTO_NO_CORRESPONDE,
        },
    )

    EspacioCurricularNombre.objects.filter(
        id_espacio_curricular=VALOR_NO_CORRESPONDE,
        id_titulacion=VALOR_NO_CORRESPONDE,
        id_nombre_espacio_curricular=VALOR_NO_CORRESPONDE,
    ).update(
        nombre=TEXTO_NO_CORRESPONDE,
    )


def quitar_no_corresponde(apps, schema_editor):
    TitulacionNombre = apps.get_model(
        "bnhpersonas",
        "TitulacionNombre",
    )
    EspacioCurricularNombre = apps.get_model(
        "bnhpersonas",
        "EspacioCurricularNombre",
    )

    # Sólo elimina los registros centinela creados por esta migración.
    EspacioCurricularNombre.objects.filter(
        id_espacio_curricular=VALOR_NO_CORRESPONDE,
        id_titulacion=VALOR_NO_CORRESPONDE,
        id_nombre_espacio_curricular=VALOR_NO_CORRESPONDE,
        nombre=TEXTO_NO_CORRESPONDE,
    ).delete()

    TitulacionNombre.objects.filter(
        id_nombre_titulacion=VALOR_NO_CORRESPONDE,
        id_titulacion=VALOR_NO_CORRESPONDE,
        c_nivel_servicio=NIVEL_SECUNDARIO_COMUN,
        c_modalidad1=MODALIDAD_COMUN,
        nombre=TEXTO_NO_CORRESPONDE,
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("bnhpersonas", "0038_constancia_servicio_verificable"),
    ]

    operations = [
        migrations.RunPython(
            agregar_no_corresponde,
            quitar_no_corresponde,
        ),
    ]
