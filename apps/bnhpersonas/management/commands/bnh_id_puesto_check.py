from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db.models import Count

from apps.bnhpersonas.models import PuestoSecuencia, RegistroActividades
from apps.bnhpersonas.services.id_puesto import construir_id_puesto, construir_puesto_base


class Command(BaseCommand):
    help = "Verifica consistencia de ID Puesto y secuencias BNH."

    def handle(self, *args, **options):
        total = 0
        sin_id = 0
        base_inconsistente = 0
        id_inconsistente = 0
        maximos = defaultdict(int)

        qs = RegistroActividades.objects.select_related("espacio_curricular").order_by("pk")

        for actividad in qs.iterator(chunk_size=1000):
            total += 1
            esperado_base = construir_puesto_base(actividad)

            if actividad.puesto_base != esperado_base:
                base_inconsistente += 1

            if not actividad.id_puesto or not actividad.puesto_consecutivo:
                sin_id += 1
                continue

            esperado_id = construir_id_puesto(
                actividad.puesto_base,
                actividad.puesto_consecutivo,
            )
            if actividad.id_puesto != esperado_id:
                id_inconsistente += 1

            maximos[actividad.puesto_base] = max(
                maximos[actividad.puesto_base],
                actividad.puesto_consecutivo,
            )

        duplicados = (
            RegistroActividades.objects.values("id_puesto")
            .annotate(total=Count("pk"))
            .filter(total__gt=1)
            .count()
        )

        secuencias_mal = 0
        for puesto_base, maximo in maximos.items():
            actual = (
                PuestoSecuencia.objects.filter(puesto_base=puesto_base)
                .values_list("ultimo_consecutivo", flat=True)
                .first()
            )
            if actual is None or actual < maximo:
                secuencias_mal += 1

        self.stdout.write(f"Registros revisados: {total}")
        self.stdout.write(f"Sin ID puesto: {sin_id}")
        self.stdout.write(f"Base inconsistente: {base_inconsistente}")
        self.stdout.write(f"ID inconsistente: {id_inconsistente}")
        self.stdout.write(f"ID duplicados: {duplicados}")
        self.stdout.write(f"Secuencias atrasadas/ausentes: {secuencias_mal}")

        if any((sin_id, base_inconsistente, id_inconsistente, duplicados, secuencias_mal)):
            self.stderr.write(self.style.ERROR("ID Puesto presenta inconsistencias."))
            return

        self.stdout.write(self.style.SUCCESS("ID Puesto consistente."))
