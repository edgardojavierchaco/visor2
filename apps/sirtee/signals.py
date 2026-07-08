import threading
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType

from apps.sirtee.models.auditoria import AuditoriaBase, CambioDetalle, SnapshotObjeto


# --------------------------------------
# THREAD LOCAL (usuario/request context)
# --------------------------------------

_thread_locals = threading.local()


def set_current_user(user):
    _thread_locals.user = user


def get_current_user():
    return getattr(_thread_locals, "user", None)


def set_request_meta(ip=None, user_agent=None):
    _thread_locals.ip = ip
    _thread_locals.user_agent = user_agent


def get_request_meta():
    return (
        getattr(_thread_locals, "ip", None),
        getattr(_thread_locals, "user_agent", None),
    )


# --------------------------------------
# CACHE DE ESTADO ANTERIOR (pre_save)
# --------------------------------------

_PREV_STATE = {}


def serialize_instance(instance):
    """
    Convierte un modelo en dict simple para comparar cambios.
    """
    data = {}
    for field in instance._meta.fields:
        name = field.name
        data[name] = getattr(instance, name, None)
    return data


def is_auditable(instance):
    """
    Solo auditar si el modelo tiene mixin de auditoría.
    """
    return hasattr(instance, "auditorias")


# --------------------------------------
# PRE SAVE → guardar estado anterior
# --------------------------------------

@receiver(pre_save)
def sirtee_pre_save(sender, instance, **kwargs):
    if not is_auditable(instance):
        return

    if not instance.pk:
        return  # nuevo objeto, no hay estado previo

    try:
        old_instance = sender.objects.get(pk=instance.pk)
        _PREV_STATE[(sender, instance.pk)] = serialize_instance(old_instance)
    except sender.DoesNotExist:
        pass


# --------------------------------------
# POST SAVE → CREATE / UPDATE
# --------------------------------------

@receiver(post_save)
def sirtee_post_save(sender, instance, created, **kwargs):
    if not is_auditable(instance):
        return

    user = get_current_user()
    ip, user_agent = get_request_meta()

    content_type = ContentType.objects.get_for_model(sender)

    accion = "CREATE" if created else "UPDATE"

    # Snapshot actual
    current_state = serialize_instance(instance)

    # Crear auditoría base
    audit = AuditoriaBase.objects.create(
        usuario=user,
        accion=accion,
        content_type=content_type,
        object_id=str(instance.pk),
        objeto_str=str(instance),
        ip_address=ip,
        user_agent=user_agent,
    )

    # Snapshot completo
    SnapshotObjeto.objects.create(
        auditoria=audit,
        data=current_state
    )

    # Si es UPDATE → comparar cambios
    if not created:
        old_state = _PREV_STATE.pop((sender, instance.pk), {})

        for field, new_value in current_state.items():
            old_value = old_state.get(field)

            if old_value != new_value:
                CambioDetalle.objects.create(
                    auditoria=audit,
                    campo=field,
                    valor_anterior=str(old_value),
                    valor_nuevo=str(new_value),
                )


# --------------------------------------
# POST DELETE → auditoría de borrado
# --------------------------------------

@receiver(post_delete)
def sirtee_post_delete(sender, instance, **kwargs):
    if not is_auditable(instance):
        return

    user = get_current_user()
    ip, user_agent = get_request_meta()

    content_type = ContentType.objects.get_for_model(sender)

    audit = AuditoriaBase.objects.create(
        usuario=user,
        accion="DELETE",
        content_type=content_type,
        object_id=str(instance.pk),
        objeto_str=str(instance),
        ip_address=ip,
        user_agent=user_agent,
    )

    SnapshotObjeto.objects.create(
        auditoria=audit,
        data=serialize_instance(instance)
    )