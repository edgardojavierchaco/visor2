from django.core.management.base import BaseCommand

from apps.bnhpersonas.domain.catalogs import available_levels, ceic_aplica, ceic_docente
from apps.bnhpersonas.models import (
    CondicionActividadNombre,
    ModalidadNivel,
    ModalidadNivelCeic,
    TipoPersonal,
    SituacionServicio,
)


class Command(BaseCommand):
    help = "Diagnostica CEIC y Condición de actividad sin modificar datos."

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("BNH - diagnóstico de catálogos"))

        self.stdout.write("\nCEIC por Modalidad + Nivel")
        for pair in ModalidadNivel.objects.select_related("modalidad", "nivel").order_by(
            "modalidad_id", "nivel_id"
        ):
            aplica = ceic_aplica(pair.modalidad_id, pair.nivel_id, tipo_personal=1)
            qs = ceic_docente(pair.modalidad_id, pair.nivel_id) if aplica else None
            cfg = ModalidadNivelCeic.objects.filter(
                modalidad_id=pair.modalidad_id,
                nivel_id=pair.nivel_id,
            ).first()
            cantidad = qs.count() if qs is not None else 0
            self.stdout.write(
                f"{pair.modalidad_id:>2} {pair.modalidad} | {pair.nivel_id:>4} {pair.nivel} | "
                f"aplica={aplica} | ceic={cantidad} | rango={getattr(cfg, 'rango_ceic', '') or '-'}"
            )

        self.stdout.write("\nCondición de actividad por Tipo de personal + Situación de revista")
        total = CondicionActividadNombre.objects.count()
        self.stdout.write(f"Total condicion_actividad_nombre: {total}")
        for tipo in TipoPersonal.objects.order_by("c_tpersonal"):
            for sit in SituacionServicio.objects.order_by("cod_sitrev"):
                count = CondicionActividadNombre.objects.filter(
                    t_personal=tipo.c_tpersonal,
                    sit_rev=sit.cod_sitrev,
                ).count()
                if count:
                    self.stdout.write(
                        f"tipo={tipo.c_tpersonal} {tipo.descripcion} | "
                        f"sit={sit.cod_sitrev} {sit.descrip_sitrev} | condiciones={count}"
                    )

        self.stdout.write("\nCombinaciones de Situación de revista sin condición configurada:")
        faltantes = 0
        for tipo in TipoPersonal.objects.order_by("c_tpersonal"):
            for sit in SituacionServicio.objects.order_by("cod_sitrev"):
                if not CondicionActividadNombre.objects.filter(
                    t_personal=tipo.c_tpersonal,
                    sit_rev=sit.cod_sitrev,
                ).exists():
                    faltantes += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"SIN CONDICIONES: tipo={tipo.c_tpersonal} {tipo.descripcion} | "
                            f"sit={sit.cod_sitrev} {sit.descrip_sitrev}"
                        )
                    )
        self.stdout.write(f"Total combinaciones sin condición: {faltantes}")
