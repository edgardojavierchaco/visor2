"""Escrituras explícitas, atómicas, idempotentes y auditadas.

Orden global de locks BNH (NO CAMBIAR entre servicios):
    1. Persona
    2. RegistroActividad
    3. ActividadSede
    4. HorarioActividad

Las consultas de frontend son sólo UX. La integridad real se garantiza aquí
más constraints/FK/UNIQUE de PostgreSQL.
"""
from __future__ import annotations

import json
import uuid

from django.core.exceptions import PermissionDenied, ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404

from ..domain.access import (
    activity_scope,
    get_user_cueanexos,
    is_admin,
    is_regional,
    person_scope,
    user_has_cueanexo_access,
)
from ..models import (
    ActividadSede,
    EventoAuditoria,
    HorarioActividad,
    Personas,
    RegistroActividades,
)
from .concurrency import (
    advisory_xact_lock,
    configure_transaction,
    retry_transient_db,
)


class Conflict(ValidationError):
    """Conflicto optimista: el registro fue modificado por otro usuario."""


class PossibleDuplicate(ValidationError):
    """La actividad coincide con la clave funcional definida como advertencia."""

    def __init__(self, queryset):
        self.duplicate_ids = list(queryset.values_list("pk", flat=True)[:10])
        count = queryset.count()
        super().__init__(
            "Se detectó un posible cargo duplicado para esta persona e institución "
            "(mismo tipo de personal, CEIC, situación de revista, tipo de designación "
            "y fecha de inicio). Revise el cargo existente. Si se trata de una "
            "designación legítimamente distinta, marque la confirmación y vuelva a guardar. "
            f"Coincidencias encontradas: {count}."
        )


class ConcurrentIdentityConflict(ValidationError):
    """Otro proceso creó el CUIL con datos de identidad incompatibles."""


IDENTITY_FIELDS = (
    "cuil",
    "dni",
    "apellido",
    "nombre",
    "f_nacimiento",
    "sexo_id",
)

DUPLICATE_ACTIVITY_FIELDS = (
    "persona_id",
    "cueanexo",
    "tipo_personal_id",
    "ceic_id",
    "sit_revista_id",
    "t_designacion_id",
    "f_desde",
)

CONSTRAINT_MESSAGES = {
    "bnh_persona_cuil_unico": "El CUIL ya se encuentra registrado.",
    "bnh_carga_positiva": "La carga horaria debe ser mayor que cero.",
    "bnh_cargo_fechas": "La fecha de finalización del cargo es inválida.",
    "bnh_funcion_fechas": "La fecha de finalización de funciones es inválida.",
    "bnh_horario_orden": "La hora de finalización debe ser posterior a la de inicio.",
    "bnh_horario_unico": "Ese horario ya se encuentra registrado para el cargo.",
    "bnh_persona_estado_valido": "El estado de la persona no es válido.",
    "bnh_actividad_estado_valido": "El estado del cargo no es válido.",
    "bnh_validacion_valida": "El estado de validación no es válido.",
    "bnh_persona_version_positiva": "La versión de la persona es inválida.",
    "bnh_actividad_version_positiva": "La versión del cargo es inválida.",
    "bnh_puesto_consecutivo_positivo": "El consecutivo del ID Puesto es inválido.",
    "bnh_id_puesto_unico": "El ID Puesto ya existe. Recargue y vuelva a guardar.",
    "bnh_puesto_base_consecutivo_unico": "La combinación base/consecutivo del puesto ya existe.",
}


def integrity_error_message(exc: IntegrityError) -> str:
    cause = getattr(exc, "__cause__", None)
    diag = getattr(cause, "diag", None)
    constraint = getattr(diag, "constraint_name", None)
    return CONSTRAINT_MESSAGES.get(
        constraint,
        "El registro ya existe o cambió mientras guardaba. Recargue y revise los datos.",
    )


def snapshot(obj):
    data = {f.attname: getattr(obj, f.attname) for f in obj._meta.concrete_fields}
    return json.loads(json.dumps(data, cls=DjangoJSONEncoder))


def audit(user, obj, action, before=None, reason="", cue="", operation_id=None):
    EventoAuditoria.objects.create(
        usuario=user,
        entidad=obj._meta.model_name,
        objeto_id=obj.pk,
        cueanexo=cue or getattr(obj, "cueanexo", ""),
        accion=action,
        motivo=reason,
        antes=before or {},
        despues=snapshot(obj),
        operacion_id=operation_id,
    )


def check_version(obj, value):
    if value != obj.version:
        raise Conflict(
            "Otro usuario modificó este registro. Recargue la página antes de continuar."
        )


def _identity_values_from_form(form):
    data = form.cleaned_data
    sexo = data.get("sexo")
    return {
        "cuil": data.get("cuil") or "",
        "dni": data.get("dni") or "",
        "apellido": " ".join((data.get("apellido") or "").upper().split()),
        "nombre": " ".join((data.get("nombre") or "").upper().split()),
        "f_nacimiento": data.get("f_nacimiento"),
        "sexo_id": getattr(sexo, "pk", None),
    }


def _identity_matches(person, form):
    expected = _identity_values_from_form(form)
    current = {
        "cuil": person.cuil or "",
        "dni": person.dni or "",
        "apellido": " ".join((person.apellido or "").upper().split()),
        "nombre": " ".join((person.nombre or "").upper().split()),
        "f_nacimiento": person.f_nacimiento,
        "sexo_id": person.sexo_id,
    }
    return current == expected


def _identity_changed(current, obj):
    return any(getattr(current, field) != getattr(obj, field) for field in IDENTITY_FIELDS)


def _person_shared_outside_user_scope(user, person):
    if is_admin(user):
        return False
    allowed = list(get_user_cueanexos(user))
    return (
        RegistroActividades.objects.filter(persona=person, eliminado=False)
        .exclude(cueanexo__in=allowed)
        .exists()
    )


def possible_activity_duplicates(obj, *, exclude_pk=None):
    """Detecta la clave funcional pedida por negocio SIN imponer UNIQUE.

    persona + cueanexo + tipo_personal + ceic + situacion_revista +
    tipo_designacion + fecha_desde
    """
    filters = {field: getattr(obj, field) for field in DUPLICATE_ACTIVITY_FIELDS}
    qs = RegistroActividades.objects.filter(eliminado=False, **filters).order_by("pk")
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    return qs


def _save_person_impl(user, form, *, operation_id=None):
    obj = form.save(commit=False)
    before = {}

    if obj.pk:
        current = get_object_or_404(
            Personas.objects.select_for_update().order_by("pk"), pk=obj.pk
        )
        if not person_scope(user).filter(pk=current.pk).exists():
            raise PermissionDenied
        check_version(current, form.cleaned_data.get("version"))
        before = snapshot(current)

        identity_changed = _identity_changed(current, obj)
        if identity_changed and _person_shared_outside_user_scope(user, current):
            raise ValidationError(
                "Los datos críticos de identidad no pueden ser modificados desde esta "
                "institución porque la persona posee cargos en otras unidades de servicio. "
                "Solicite la corrección a un usuario administrador/Estadística."
            )
        obj.version = current.version + 1
    else:
        if not (
            is_admin(user)
            or user_has_cueanexo_access(user, getattr(form, "authorized_cue", ""))
        ):
            raise PermissionDenied
        obj.usuario_creacion = user
        identity_changed = False

    obj.usuario_modificacion = user
    obj.save()
    audit(
        user,
        obj,
        "EDITAR" if before else "CREAR",
        before,
        operation_id=operation_id,
    )

    # Sólo una corrección real de identidad obliga a revisar cargos relacionados.
    # Cambios de contacto/localidad no generan locks masivos innecesarios.
    if before and identity_changed:
        activities = (
            RegistroActividades.objects.select_for_update()
            .filter(persona=obj, eliminado=False)
            .order_by("pk")
        )
        for activity in activities:
            old = snapshot(activity)
            activity.validacion = "BORRADOR"
            activity.version += 1
            activity.usuario_modificacion = user
            activity.save(update_fields=[
                "validacion", "version", "usuario_modificacion", "fecha_modificacion"
            ])
            audit(
                user,
                activity,
                "REVISAR_IDENTIDAD",
                old,
                operation_id=operation_id,
            )
    return obj


@retry_transient_db()
@transaction.atomic
def save_person(user, form):
    configure_transaction()
    return _save_person_impl(user, form, operation_id=uuid.uuid4())


def _save_activity_impl(user, form, persona, *, operation_id=None):
    # Orden de bloqueo: persona -> actividad -> sede/horario.
    person = get_object_or_404(
        Personas.objects.select_for_update().order_by("pk"),
        pk=persona.pk,
        archivada=False,
    )
    obj = form.save(commit=False)

    if not user_has_cueanexo_access(user, obj.cueanexo):
        raise PermissionDenied

    before = {}
    current = None
    if obj.pk:
        current = get_object_or_404(
            RegistroActividades.objects.select_for_update().order_by("pk"),
            pk=obj.pk,
            eliminado=False,
        )
        if (
            not activity_scope(user).filter(pk=current.pk).exists()
            or current.persona_id != person.pk
            or current.cueanexo != obj.cueanexo
        ):
            raise PermissionDenied
        check_version(current, form.cleaned_data.get("version"))
        before = snapshot(current)
        obj.version = current.version + 1
        op_uuid = current.uuid
    else:
        op_uuid = form.cleaned_data.get("operation_id") or operation_id
        if not op_uuid:
            raise ValidationError("No se recibió el identificador de operación del cargo.")

        # Idempotencia real: el mismo POST/reintento devuelve el registro ya creado.
        existing = (
            RegistroActividades.objects.select_for_update()
            .filter(uuid=op_uuid)
            .first()
        )
        if existing:
            if existing.persona_id != person.pk or existing.cueanexo != obj.cueanexo:
                raise Conflict(
                    "El identificador de operación ya fue utilizado por otro cargo. "
                    "Recargue el formulario."
                )
            if not user_has_cueanexo_access(user, existing.cueanexo):
                raise PermissionDenied
            return existing

        if (
            not person_scope(user).filter(pk=person.pk).exists()
            and not getattr(form, "allow_link", False)
        ):
            raise PermissionDenied
        obj.uuid = op_uuid

    obj.persona = person
    obj.validacion = "BORRADOR"
    if not obj.pk:
        obj.usuario_creacion = user
    obj.usuario_modificacion = user
    obj.normalize()

    # El ID Puesto se genera automáticamente. No forma parte del formulario.
    from .id_puesto import asignar_id_puesto
    asignar_id_puesto(obj, anterior=current)

    obj.full_clean()

    duplicates = possible_activity_duplicates(obj, exclude_pk=obj.pk or None)
    if duplicates.exists() and not form.cleaned_data.get("confirmar_posible_duplicado"):
        raise PossibleDuplicate(duplicates)

    obj.save()
    audit(
        user,
        obj,
        "EDITAR" if before else "CREAR",
        before,
        operation_id=op_uuid,
    )
    return obj


@retry_transient_db()
@transaction.atomic
def save_activity(user, form, persona):
    configure_transaction()
    return _save_activity_impl(user, form, persona)


@retry_transient_db()
@transaction.atomic
def create_person_with_activity(user, person_form, activity_form):
    """Alta atómica y segura ante dos instituciones creando el mismo CUIL.

    La consulta AJAX puede decir "no existe" a dos usuarios simultáneamente.
    Este servicio serializa por CUIL. El primero crea la persona; el segundo,
    si los datos críticos coinciden, reutiliza la persona sin sobrescribirla y
    sólo crea su actividad. Si la identidad difiere, bloquea la operación.
    """
    configure_transaction()
    cuil = person_form.cleaned_data["cuil"]
    advisory_xact_lock("bnh:persona:cuil", cuil)

    operation_id = activity_form.cleaned_data.get("operation_id") or uuid.uuid4()
    person = (
        Personas.objects.select_for_update().filter(cuil=cuil).first()
    )

    created_person = False
    if person:
        if person.archivada:
            raise ConcurrentIdentityConflict(
                "La persona fue registrada previamente pero su ficha está archivada. "
                "Solicite revisión antes de continuar."
            )
        if not _identity_matches(person, person_form):
            raise ConcurrentIdentityConflict(
                "Otra unidad de servicio registró este CUIL mientras se realizaba el alta, "
                "pero los datos críticos de identidad no coinciden. No se sobrescribió la "
                "ficha existente. Solicite revisión."
            )
    else:
        person_form.authorized_cue = activity_form.cleaned_data["cueanexo"]
        person = _save_person_impl(
            user, person_form, operation_id=operation_id
        )
        created_person = True

    activity_form.allow_link = True
    activity = _save_activity_impl(
        user, activity_form, person, operation_id=operation_id
    )
    return person, activity, created_person


@retry_transient_db()
@transaction.atomic
def link_existing_person_with_activity(user, identity_data, activity_form):
    """Vinculación atómica: identidad y cargo se verifican bajo el mismo lock."""
    configure_transaction()
    cuil = identity_data["cuil"]
    advisory_xact_lock("bnh:persona:cuil", cuil)

    person = (
        Personas.objects.select_for_update()
        .filter(cuil=cuil, archivada=False)
        .first()
    )
    if not person:
        raise ValidationError(
            "La persona ya no está disponible para vincular. Recargue y vuelva a consultar."
        )

    expected = {
        "dni": identity_data["dni"],
        "apellido": " ".join(identity_data["apellido"].upper().split()),
        "nombre": " ".join(identity_data["nombre"].upper().split()),
    }
    current = {
        "dni": person.dni or "",
        "apellido": " ".join((person.apellido or "").upper().split()),
        "nombre": " ".join((person.nombre or "").upper().split()),
    }
    if current != expected:
        raise ConcurrentIdentityConflict(
            "Los datos de identidad cambiaron mientras se realizaba la vinculación. "
            "Recargue el formulario y vuelva a consultar el CUIL."
        )

    activity_form.allow_link = True
    activity = _save_activity_impl(user, activity_form, person)
    return person, activity


@retry_transient_db()
@transaction.atomic
def change_activity(user, pk, action, version, reason):
    configure_transaction()
    initial = get_object_or_404(activity_scope(user, include_deleted=True), pk=pk)
    Personas.objects.select_for_update().get(pk=initial.persona_id)
    obj = get_object_or_404(
        RegistroActividades.objects.select_for_update().order_by("pk"), pk=pk
    )
    if not user_has_cueanexo_access(user, obj.cueanexo):
        raise PermissionDenied
    check_version(obj, version)
    before = snapshot(obj)
    operation_id = uuid.uuid4()

    if action == "RESTAURAR":
        if not obj.eliminado or obj.persona.archivada:
            raise ValidationError("No es posible restaurar este cargo.")
        obj.eliminado = False
        obj.validacion = "BORRADOR"
    elif obj.eliminado:
        raise ValidationError("El cargo está eliminado.")
    elif action == "ELIMINAR":
        obj.eliminado = True
        obj.validacion = "BORRADOR"
    elif action == "VALIDAR":
        obj.full_clean()
        obj.persona.full_clean()
        if not obj.persona.cuil or not obj.persona.dni:
            raise ValidationError("Complete CUIL y DNI antes de validar.")
        from ..forms import ActividadDirectorForm

        data = {
            f: getattr(obj, obj._meta.get_field(f).attname)
            for f in ActividadDirectorForm.Meta.fields
        }
        validation = ActividadDirectorForm(data, instance=obj, user=user)
        if not validation.is_valid():
            raise ValidationError(
                "Revise el cargo antes de validar: " + validation.errors.as_text()
            )
        obj.validacion = "VALIDADO"
    elif action == "OBSERVAR":
        if not (is_regional(user) or is_admin(user)):
            raise PermissionDenied
        obj.validacion = "OBSERVADO"
    else:
        raise ValidationError("Acción inválida.")

    obj.version += 1
    obj.usuario_modificacion = user
    obj.save()
    audit(user, obj, action, before, reason, operation_id=operation_id)
    return obj


@retry_transient_db()
@transaction.atomic
def archive_person(user, pk, version, reason):
    configure_transaction()
    obj = get_object_or_404(
        Personas.objects.select_for_update().order_by("pk"), pk=pk, archivada=False
    )
    allowed = person_scope(user).filter(pk=pk).exists() or (
        RegistroActividades.objects.filter(persona=obj).exists()
        and not RegistroActividades.objects.filter(persona=obj)
        .exclude(cueanexo__in=get_user_cueanexos(user))
        .exists()
    )
    if not (is_admin(user) or allowed):
        raise PermissionDenied
    if RegistroActividades.objects.filter(persona=obj, eliminado=False).exists():
        raise ValidationError(
            "Primero dé de baja los cargos. No se puede eliminar una persona con cargos vigentes en el registro."
        )
    check_version(obj, version)
    before = snapshot(obj)
    obj.archivada = True
    obj.version += 1
    obj.usuario_modificacion = user
    obj.save(skip_clean=True)
    audit(user, obj, "ARCHIVAR", before, reason, operation_id=uuid.uuid4())
    return obj


@retry_transient_db()
@transaction.atomic
def add_schedule(user, activity_id, form, version):
    configure_transaction()
    initial = get_object_or_404(activity_scope(user), pk=activity_id)
    Personas.objects.select_for_update().get(pk=initial.persona_id)
    activity = get_object_or_404(
        RegistroActividades.objects.select_for_update().order_by("pk"),
        pk=activity_id,
        eliminado=False,
    )
    if not user_has_cueanexo_access(user, activity.cueanexo):
        raise PermissionDenied
    check_version(activity, version)

    sede, _ = ActividadSede.objects.get_or_create(
        actividad=activity, cueanexo=activity.cueanexo
    )
    obj = form.save(commit=False)
    obj.actividad_sede = sede
    if HorarioActividad.objects.filter(
        actividad_sede=sede,
        dia=obj.dia,
        hora_desde__lt=obj.hora_hasta,
        hora_hasta__gt=obj.hora_desde,
    ).exists():
        raise ValidationError("El horario se superpone con otro de este cargo.")

    obj.full_clean()
    obj.save()
    operation_id = obj.uuid
    audit(
        user,
        obj,
        "CREAR_HORARIO",
        cue=activity.cueanexo,
        operation_id=operation_id,
    )

    before = snapshot(activity)
    activity.version += 1
    activity.validacion = "BORRADOR"
    activity.usuario_modificacion = user
    activity.save()
    audit(
        user,
        activity,
        "CAMBIAR_HORARIOS",
        before,
        operation_id=operation_id,
    )
    return obj


@retry_transient_db()
@transaction.atomic
def delete_schedule(user, pk, version, reason):
    configure_transaction()
    initial = get_object_or_404(
        HorarioActividad.objects.select_related("actividad_sede"),
        pk=pk,
        actividad_sede__actividad__in=activity_scope(user),
    )
    activity_id = initial.actividad_sede.actividad_id
    initial_activity = RegistroActividades.objects.get(pk=activity_id)
    Personas.objects.select_for_update().get(pk=initial_activity.persona_id)
    activity = get_object_or_404(
        RegistroActividades.objects.select_for_update().order_by("pk"),
        pk=activity_id,
        eliminado=False,
    )
    if not user_has_cueanexo_access(user, activity.cueanexo):
        raise PermissionDenied
    check_version(activity, version)

    obj = get_object_or_404(
        HorarioActividad.objects.select_for_update().order_by("pk"), pk=pk
    )
    operation_id = obj.uuid
    audit(
        user,
        obj,
        "ELIMINAR_HORARIO",
        snapshot(obj),
        reason,
        activity.cueanexo,
        operation_id,
    )
    obj.delete()

    before = snapshot(activity)
    activity.version += 1
    activity.validacion = "BORRADOR"
    activity.usuario_modificacion = user
    activity.save()
    audit(
        user,
        activity,
        "CAMBIAR_HORARIOS",
        before,
        reason,
        operation_id=operation_id,
    )
    return activity


@retry_transient_db()
@transaction.atomic
def restore_person(user, pk, version, reason):
    configure_transaction()
    if not is_admin(user):
        raise PermissionDenied
    obj = get_object_or_404(
        Personas.objects.select_for_update().order_by("pk"), pk=pk, archivada=True
    )
    check_version(obj, version)
    before = snapshot(obj)
    obj.archivada = False
    obj.version += 1
    obj.usuario_modificacion = user
    obj.save(skip_clean=True)
    audit(
        user,
        obj,
        "RESTAURAR_PERSONA",
        before,
        reason,
        operation_id=uuid.uuid4(),
    )
    return obj
