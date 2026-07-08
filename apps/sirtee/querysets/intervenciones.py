from django.db import models


class IntervencionQuerySet(models.QuerySet):

    def activos(self):
        return self.filter(deleted_at__isnull=True)

    def con_relaciones(self):
        return self.select_related(
            "hallazgo",
            "hallazgo__relevamiento",
            "hallazgo__relevamiento__escuela"
        )

    def en_ejecucion(self):
        return self.filter(estado="EN_EJECUCION")

    def pendientes(self):
        return self.filter(estado="PENDIENTE")

    def finalizadas(self):
        return self.filter(estado="FINALIZADA")

    def bloqueadas(self):
        return self.filter(estado="BLOQUEADO")

    def atrasadas(self):
        return self.filter(
            estado__in=["EN_EJECUCION", "PENDIENTE"],
            fecha_estimada_fin__lt=models.functions.Now()
        )

    def por_empresa(self, empresa_id):
        return self.filter(equipo_ejecutor_id=empresa_id)

    def por_escuela(self, cueanexo):
        return self.filter(
            hallazgo__relevamiento__escuela__cueanexo=cueanexo
        )

    def con_costos(self):
        return self.filter(costo_estimado__isnull=False)

    def recientes(self):
        return self.order_by("-id")