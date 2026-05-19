from django.db.models.signals import pre_save
from django.dispatch import receiver

from .models import DocenteFrenteGrado, Personal


@receiver(pre_save, sender=DocenteFrenteGrado)
def ensure_personal_exists(sender, instance, **kwargs):

    if instance.cuil_docente_id:

        obj, created = Personal.objects.get_or_create(
            cuil=instance.cuil_docente_id,
            defaults={
                'apellido': 'SIN REGISTRO',
                'nombres': 'SIN REGISTRO'
            }
        )

        instance.cuil_docente = obj