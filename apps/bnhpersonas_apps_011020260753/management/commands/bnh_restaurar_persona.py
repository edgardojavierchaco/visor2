from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.core.exceptions import ValidationError
from apps.bnhpersonas.services.crud import restore_person

class Command(BaseCommand):
    help = 'Restaura una ficha archivada con actor ministerial explícito, versión y motivo. No reactiva cargos.'
    def add_arguments(self, parser):
        parser.add_argument('persona_id', type=int)
        parser.add_argument('--actor', required=True, help='Nombre de usuario/ CUlL exacto del administrador responsable')
        parser.add_argument('--version', required=True, type=int)
        parser.add_argument('--motivo', required=True)
    def handle(self, *args, **options):
        if len(options['motivo'].strip()) < 5:
            raise ValidationError('El motivo debe tener al menos cinco caracteres.')
        User = get_user_model()
        actor = User.objects.get(**{User.USERNAME_FIELD: options['actor']})
        obj = restore_person(actor, options['persona_id'], options['version'], options['motivo'])
        self.stdout.write(self.style.SUCCESS(f'Ficha {obj.pk} restaurada. Versión: {obj.version}.'))
