from django.core.management.base import BaseCommand, CommandError

from apps.asistencia_dashboard.maintenance import actualizar_periodo


class Command(BaseCommand):
    help = "Refresca integralmente un mes de asistencia y registra el resultado en auditoría."

    def add_arguments(self, parser):
        parser.add_argument("--anio", type=int, required=True)
        parser.add_argument("--mes", type=int, required=True)
        parser.add_argument("--semana", type=int, default=None, help="Compatibilidad: ya no es necesaria; el procedimiento integral reprocesa las semanas del mes.")

    def handle(self, *args, **options):
        anio = options["anio"]
        mes = options["mes"]
        if mes < 1 or mes > 12:
            raise CommandError("El mes debe estar entre 1 y 12.")
        try:
            resultado = actualizar_periodo(anio=anio, mes=mes, proceso="ASISTENCIA_SGE_MANUAL")
        except Exception as exc:
            raise CommandError(f"Falló el refresco integral: {exc}") from exc
        if resultado.get("estado") == "OMITIDO":
            self.stdout.write(self.style.WARNING(resultado.get("motivo", "Actualización omitida.")))
            return
        self.stdout.write(self.style.SUCCESS(f"Refresco integral {mes:02d}/{anio} finalizado correctamente."))
