import json
from django.core.serializers.json import DjangoJSONEncoder
from django.core.management.base import BaseCommand, CommandError
from apps.bnhpersonas.models import Personas, RegistroActividades, HorarioActividad
from apps.bnhpersonas.domain.preflight import inspect_data

class Command(BaseCommand):
    help = 'Revisa datos existentes sin modificarlos antes de aplicar las migraciones ministeriales.'
    def add_arguments(self, parser):
        parser.add_argument('--database', default='default')
    def handle(self, *args, **options):
        issues = inspect_data(Personas, RegistroActividades, HorarioActividad, options['database'])
        warnings = {}
        if "cargos_posible_duplicado" in issues:
            warnings["cargos_posible_duplicado"] = issues.pop("cargos_posible_duplicado")

        payload = {"errores": issues, "advertencias": warnings}
        self.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2, cls=DjangoJSONEncoder))

        if warnings:
            self.stdout.write(self.style.WARNING(
                'Se detectaron posibles cargos duplicados. Son advertencias: no bloquean la migración y no se aplica UNIQUE.'
            ))
        if issues:
            raise CommandError('Existen inconsistencias bloqueantes. Revise los IDs informados antes de migrar. No se modificaron datos.')
        self.stdout.write(self.style.SUCCESS('Control previo aprobado; no se detectaron bloqueos para las nuevas restricciones.'))
