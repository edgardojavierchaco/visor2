import json
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.management.base import BaseCommand, CommandError
from apps.bnhpersonas.services.catalog_import import import_catalogs

class Command(BaseCommand):
    help='Valida/simula los cinco CSV normalizados; --aplicar realiza una importación atómica y auditada.'
    def add_arguments(self, parser):
        parser.add_argument('directorio')
        parser.add_argument('--aplicar',action='store_true')
        parser.add_argument('--actor',help='Nombre de usuario exacto del administrador responsable.')
    def handle(self,*args,**options):
        actor=None
        try:
            if options['aplicar']:
                if not options['actor']:
                    raise CommandError('--aplicar requiere --actor USUARIO_ADMIN.')
                User=get_user_model()
                actor=User.objects.filter(**{User.USERNAME_FIELD:options['actor']}).first()
            result=import_catalogs(options['directorio'],apply=options['aplicar'],actor=actor)
        except (OSError,ValidationError,PermissionDenied) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(json.dumps(result,ensure_ascii=False,indent=2))
        if result['conflictos']:
            raise CommandError('Hay referencias de actividades incompatibles. No se aplicó ningún cambio.')
        self.stdout.write(self.style.SUCCESS('Importación aplicada.' if result['aplicado'] else 'Simulación finalizada. No se modificaron datos.'))
