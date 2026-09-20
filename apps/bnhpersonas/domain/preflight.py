"""Comprobaciones de integridad en modo sólo lectura."""

import re
from collections import defaultdict

from django.db.models import Count, F, Q


def inspect_data(
    Personas,
    RegistroActividades,
    HorarioActividad,
    using="default",
):
    issues = {}

    # ============================================================
    # PERSONAS
    # ============================================================

    identities = defaultdict(list)
    malformed = []

    for pk, cuil in (
        Personas.objects
        .using(using)
        .values_list("pk", "cuil")
        .iterator(chunk_size=2000)
    ):
        if not cuil:
            continue

        normalized = re.sub(
            r"[^0-9]",
            "",
            cuil,
        )

        identities[normalized].append(pk)

        if (
            cuil != normalized
            or len(normalized) != 11
        ):
            malformed.append(pk)

    duplicates = [
        ids
        for ids in identities.values()
        if len(ids) > 1
    ]

    if duplicates:
        issues[
            "personas_cuil_duplicado_ids"
        ] = duplicates

    if malformed:
        issues[
            "personas_cuil_no_canonico_ids"
        ] = malformed

    # ============================================================
    # ACTIVIDADES OPERATIVAS
    # ============================================================
    #
    # IMPORTANTE:
    # Las actividades eliminadas lógicamente NO participan de
    # los controles operativos/preflight.
    #
    # Se conservan físicamente para auditoría/trazabilidad,
    # pero no deben bloquear migraciones ni generar advertencias
    # de duplicidad activa.
    # ============================================================

    activity = (
        RegistroActividades.objects
        .using(using)
        .filter(eliminado=False)
    )

    # ============================================================
    # VALIDACIONES BLOQUEANTES
    # ============================================================

    checks = {
        "cargos_carga_no_positiva_ids": (
            activity.filter(
                carga_horaria__lte=0
            )
        ),

        "cargos_fechas_invertidas_ids": (
            activity.filter(
                f_hasta__lt=F("f_desde")
            )
        ),

        "funciones_fechas_invertidas_ids": (
            activity.filter(
                f_hasta_funciones__lt=F(
                    "f_desde_funciones"
                )
            )
        ),

        # --------------------------------------------------------
        # HORARIOS
        # --------------------------------------------------------
        #
        # También se excluyen horarios cuya actividad padre
        # está eliminada lógicamente.
        #
        "horarios_invalidos_ids": (
            HorarioActividad.objects
            .using(using)
            .filter(
                actividad_sede__actividad__eliminado=False,
                hora_hasta__lte=F("hora_desde"),
            )
        ),

        # --------------------------------------------------------
        # CIRCUITO CURRICULAR
        # --------------------------------------------------------

        "docentes_sin_modalidad_curricular_ids": (
            activity.filter(
                tipo_personal_id=1,
                modalidad_curricular__isnull=True,
            )
        ),

        "docentes_sin_nivel_curricular_ids": (
            activity.filter(
                tipo_personal_id=1,
                nivel_curricular__isnull=True,
            )
        ),

        "no_docentes_con_datos_curriculares_ids": (
            activity
            .filter(
                tipo_personal_id=2
            )
            .filter(
                Q(
                    modalidad_curricular__isnull=False
                )
                | Q(
                    nivel_curricular__isnull=False
                )
                | Q(
                    titulacion__isnull=False
                )
                | Q(
                    espacio_curricular__isnull=False
                )
                | Q(
                    grado_anio__isnull=False
                )
                | Q(
                    secciones__isnull=False
                )
            )
        ),

        "niveles_curriculares_incompatibles_ids": (
            activity
            .filter(
                modalidad_curricular__isnull=False,
                nivel_curricular__isnull=False,
            )
            .exclude(
                modalidad_curricular__c_modalidad1=F(
                    "nivel_curricular__c_modalidad1"
                )
            )
        ),

        "espacios_curriculares_incompatibles_ids": (
            activity
            .filter(
                titulacion__isnull=False,
                espacio_curricular__isnull=False,
            )
            .exclude(
                titulacion=F(
                    "espacio_curricular__id_titulacion"
                )
            )
        ),
    }

    for key, qs in checks.items():
        ids = list(
            qs.values_list(
                "pk",
                flat=True,
            )
        )

        if ids:
            issues[key] = ids

    # ============================================================
    # POSIBLES DUPLICADOS DE CARGOS
    # ============================================================
    #
    # NO ES UNIQUE.
    #
    # Es sólo una advertencia funcional.
    #
    # Se considera posible duplicado cuando coinciden:
    #
    # persona
    # cueanexo
    # tipo_personal
    # ceic
    # situacion_revista
    # tipo_designacion
    # fecha_desde
    #
    # Se excluyen actividades eliminadas.
    # ============================================================

    possible_duplicates = (
        activity
        .values(
            "persona_id",
            "cueanexo",
            "tipo_personal_id",
            "ceic_id",
            "sit_revista_id",
            "t_designacion_id",
            "f_desde",
        )
        .annotate(
            cantidad=Count("id")
        )
        .filter(
            cantidad__gt=1
        )
        .order_by(
            "persona_id",
            "cueanexo",
            "f_desde",
        )
    )

    duplicate_rows = list(
        possible_duplicates
    )

    if duplicate_rows:
        issues[
            "cargos_posible_duplicado"
        ] = duplicate_rows

    return issues