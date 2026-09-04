"""Escrituras explícitas, atómicas y auditadas. El actor nunca se obtiene de un global."""
import json
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.shortcuts import get_object_or_404
from ..domain.access import activity_scope, person_scope, is_admin, is_regional, user_has_cueanexo_access, get_user_cueanexos
from ..models import Personas, RegistroActividades, EventoAuditoria, ActividadSede, HorarioActividad


class Conflict(ValidationError):
    pass


def snapshot(obj):
    # Valores escalares: no se serializan objetos relacionados ni credenciales.
    data = {f.attname: getattr(obj, f.attname) for f in obj._meta.concrete_fields}
    return json.loads(json.dumps(data, cls=DjangoJSONEncoder))


def audit(user, obj, action, before=None, reason="", cue=""):
    EventoAuditoria.objects.create(usuario=user, entidad=obj._meta.model_name, objeto_id=obj.pk,
        cueanexo=cue or getattr(obj, "cueanexo", ""), accion=action,
        motivo=reason, antes=before or {}, despues=snapshot(obj))


def check_version(obj, value):
    if value != obj.version:
        raise Conflict("Otro usuario modificó este registro. Recargue la página antes de continuar.")


@transaction.atomic
def save_person(user, form):
    obj = form.save(commit=False)
    before = {}
    if obj.pk:
        current = get_object_or_404(Personas.objects.select_for_update(), pk=obj.pk)
        if not person_scope(user).filter(pk=current.pk).exists():
            raise PermissionDenied
        check_version(current, form.cleaned_data.get("version"))
        before = snapshot(current)
        obj.version = current.version + 1
    else:
        if not (is_admin(user) or user_has_cueanexo_access(user, getattr(form, "authorized_cue", ""))):
            raise PermissionDenied
        obj.usuario_creacion = user
    obj.usuario_modificacion = user
    obj.save()
    audit(user, obj, "EDITAR" if before else "CREAR", before)
    # Cambiar la identidad obliga a revisar todos sus cargos, aun de otra escuela.
    if before:
        for activity in RegistroActividades.objects.select_for_update().filter(persona=obj, eliminado=False).order_by("pk"):
            old = snapshot(activity)
            activity.validacion = "BORRADOR"
            activity.version += 1
            activity.usuario_modificacion = user
            activity.save()
            audit(user, activity, "REVISAR_IDENTIDAD", old)
    return obj


@transaction.atomic
def save_activity(user, form, persona):
    # Orden de bloqueo común: persona, actividad, sede/horario.
    person = get_object_or_404(Personas.objects.select_for_update(), pk=persona.pk, archivada=False)
    obj = form.save(commit=False)
    if not user_has_cueanexo_access(user, obj.cueanexo):
        raise PermissionDenied
    before = {}
    if obj.pk:
        current = get_object_or_404(RegistroActividades.objects.select_for_update(), pk=obj.pk, eliminado=False)
        if not activity_scope(user).filter(pk=current.pk).exists() or current.persona_id != person.pk or current.cueanexo != obj.cueanexo:
            raise PermissionDenied
        check_version(current, form.cleaned_data.get("version"))
        before = snapshot(current)
        obj.version = current.version + 1
    elif not person_scope(user).filter(pk=person.pk).exists() and not getattr(form, "allow_link", False):
        raise PermissionDenied
    if not obj.pk:
        obj.uuid = form.cleaned_data["operation_id"]
    obj.persona = person
    obj.validacion = "BORRADOR"
    if not obj.pk:
        obj.usuario_creacion = user
    obj.usuario_modificacion = user
    obj.normalize()
    obj.full_clean()
    obj.save()
    audit(user, obj, "EDITAR" if before else "CREAR", before)
    return obj


@transaction.atomic
def change_activity(user, pk, action, version, reason):
    initial = get_object_or_404(activity_scope(user, include_deleted=True), pk=pk)
    Personas.objects.select_for_update().get(pk=initial.persona_id)
    obj = get_object_or_404(RegistroActividades.objects.select_for_update(), pk=pk)
    if not user_has_cueanexo_access(user, obj.cueanexo):
        raise PermissionDenied
    check_version(obj, version)
    before = snapshot(obj)
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
        # Reutiliza todas las reglas del formulario, incluidos los catálogos.
        from ..forms import ActividadDirectorForm
        data = {f: getattr(obj, obj._meta.get_field(f).attname) for f in ActividadDirectorForm.Meta.fields}
        validation = ActividadDirectorForm(data, instance=obj, user=user)
        if not validation.is_valid():
            raise ValidationError("Revise el cargo antes de validar: " + validation.errors.as_text())
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
    audit(user, obj, action, before, reason)
    return obj


@transaction.atomic
def archive_person(user, pk, version, reason):
    obj = get_object_or_404(Personas.objects.select_for_update(), pk=pk, archivada=False)
    allowed = person_scope(user).filter(pk=pk).exists() or (
        RegistroActividades.objects.filter(persona=obj).exists() and
        not RegistroActividades.objects.filter(persona=obj).exclude(cueanexo__in=get_user_cueanexos(user)).exists())
    if not (is_admin(user) or allowed):
        raise PermissionDenied
    if RegistroActividades.objects.filter(persona=obj, eliminado=False).exists():
        raise ValidationError("Primero dé de baja los cargos. No se puede eliminar una persona con cargos vigentes en el registro.")
    check_version(obj, version)
    before = snapshot(obj)
    obj.archivada = True
    obj.version += 1
    obj.usuario_modificacion = user
    obj.save(skip_clean=True)
    audit(user, obj, "ARCHIVAR", before, reason)
    return obj


@transaction.atomic
def add_schedule(user, activity_id, form, version):
    initial = get_object_or_404(activity_scope(user), pk=activity_id)
    Personas.objects.select_for_update().get(pk=initial.persona_id)
    activity = get_object_or_404(RegistroActividades.objects.select_for_update(), pk=activity_id, eliminado=False)
    if not user_has_cueanexo_access(user, activity.cueanexo):
        raise PermissionDenied
    check_version(activity, version)
    sede, _ = ActividadSede.objects.get_or_create(actividad=activity, cueanexo=activity.cueanexo)
    obj = form.save(commit=False)
    obj.actividad_sede = sede
    if HorarioActividad.objects.filter(actividad_sede=sede, dia=obj.dia, hora_desde__lt=obj.hora_hasta, hora_hasta__gt=obj.hora_desde).exists():
        raise ValidationError("El horario se superpone con otro de este cargo.")
    obj.full_clean()
    obj.save()
    audit(user, obj, "CREAR_HORARIO", cue=activity.cueanexo)
    before = snapshot(activity)
    activity.version += 1
    activity.validacion = "BORRADOR"
    activity.usuario_modificacion = user
    activity.save()
    audit(user, activity, "CAMBIAR_HORARIOS", before)
    return obj


@transaction.atomic
def delete_schedule(user, pk, version, reason):
    initial = get_object_or_404(HorarioActividad.objects.select_related("actividad_sede"), pk=pk, actividad_sede__actividad__in=activity_scope(user))
    activity_id = initial.actividad_sede.actividad_id
    initial_activity = RegistroActividades.objects.get(pk=activity_id)
    Personas.objects.select_for_update().get(pk=initial_activity.persona_id)
    activity = get_object_or_404(RegistroActividades.objects.select_for_update(), pk=activity_id, eliminado=False)
    if not user_has_cueanexo_access(user, activity.cueanexo):
        raise PermissionDenied
    check_version(activity, version)
    obj = get_object_or_404(HorarioActividad.objects.select_for_update(), pk=pk)
    audit(user, obj, "ELIMINAR_HORARIO", snapshot(obj), reason, activity.cueanexo)
    obj.delete()
    before = snapshot(activity)
    activity.version += 1
    activity.validacion = "BORRADOR"
    activity.usuario_modificacion = user
    activity.save()
    audit(user, activity, "CAMBIAR_HORARIOS", before, reason)
    return activity


@transaction.atomic
def restore_person(user, pk, version, reason):
    if not is_admin(user):
        raise PermissionDenied
    obj = get_object_or_404(Personas.objects.select_for_update(), pk=pk, archivada=True)
    check_version(obj, version)
    before = snapshot(obj)
    obj.archivada = False
    obj.version += 1
    obj.usuario_modificacion = user
    obj.save(skip_clean=True)
    audit(user, obj, "RESTAURAR_PERSONA", before, reason)
    return obj
