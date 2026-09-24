from django.core.management.base import BaseCommand, CommandError
from django.db import connections

DB_ALIAS = "sge_nacion"


class Command(BaseCommand):
    help = "Refresca asistencia mensual, nominal y alertas semanales materializadas."

    def add_arguments(self, parser):
        parser.add_argument("--anio", type=int, required=True)
        parser.add_argument("--mes", type=int, required=True)
        parser.add_argument("--semana", type=int, default=None)

    def handle(self, *args, **options):
        anio = options["anio"]
        mes = options["mes"]
        semana = options["semana"]

        if mes < 1 or mes > 12:
            raise CommandError("El mes debe estar entre 1 y 12.")

        with connections[DB_ALIAS].cursor() as cursor:
            self.stdout.write(f"Refrescando agregado mensual {mes:02d}/{anio}...")
            cursor.execute("CALL sge.refrescar_asistencia_mes(%s,%s)", [anio, mes])

            self.stdout.write("Refrescando hecho nominal...")
            cursor.execute("CALL sge.refrescar_asistencia_alumno_mes(%s,%s)", [anio, mes])

            self.stdout.write("Refrescando matrícula mensual por sección...")
            cursor.execute("CALL sge.refrescar_matricula_mes(%s,%s)", [anio, mes])

            self.stdout.write("Refrescando calidad de registración según calendario...")
            cursor.execute("CALL sge.refrescar_calidad_registro_mes(%s,%s)", [anio, mes])

            if semana is not None:
                cursor.execute(
                    "CALL sge.refrescar_alertas_alumnos_semana(%s,%s)",
                    [anio, semana],
                )
                self.stdout.write(self.style.SUCCESS(f"Semana {semana}/{anio} actualizada."))
            else:
                cursor.execute(
                    """
                    SELECT DISTINCT
                        EXTRACT(ISOYEAR FROM fecha_asistencia)::integer,
                        EXTRACT(WEEK FROM fecha_asistencia)::integer
                    FROM sge.aip_asistencia_alumno
                    WHERE fecha_asistencia >= make_date(%s,%s,1)
                      AND fecha_asistencia < (make_date(%s,%s,1) + INTERVAL '1 month')::date
                    ORDER BY 1,2
                    """,
                    [anio, mes, anio, mes],
                )
                semanas = cursor.fetchall()
                for anio_iso, semana_iso in semanas:
                    cursor.execute(
                        "CALL sge.refrescar_alertas_alumnos_semana(%s,%s)",
                        [anio_iso, semana_iso],
                    )
                    self.stdout.write(f"Semana {semana_iso}/{anio_iso} actualizada.")

        self.stdout.write(self.style.SUCCESS("Proceso finalizado."))
