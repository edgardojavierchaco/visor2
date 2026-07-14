from django.db import models


class IntervencionQuerySet(models.QuerySet):

    def activos(self):
        return self.filter(deleted_at__isnull=True)

    def en_ejecucion(self):
        return self.filter(estado="EN_EJECUCION")

    def finalizadas(self):
        return self.filter(estado="FINALIZADA")

    def pendientes(self):
        return self.filter(estado="PENDIENTE")

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


class IntervencionManager(models.Manager):

    def get_queryset(self):
        return IntervencionQuerySet(self.model, using=self._db)

    def activos(self):
        return self.get_queryset().activos()

    def en_ejecucion(self):
        return self.get_queryset().en_ejecucion()

    def finalizadas(self):
        return self.get_queryset().finalizadas()

    def atrasadas(self):
        return self.get_queryset().atrasadas()

    def por_empresa(self, empresa_id):
        return self.get_queryset().por_empresa(empresa_id)

    def por_escuela(self, cueanexo):
        return self.get_queryset().por_escuela(cueanexo)