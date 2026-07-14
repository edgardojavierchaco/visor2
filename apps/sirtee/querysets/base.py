from django.db import models
from django.utils import timezone


class SirteeQuerySet(models.QuerySet):
    
    # ==================================================
    # SOFT DELETE
    # ==================================================
    def activos(self):
        return self.filter(is_deleted=False)

    def eliminados(self):
        return self.filter(is_deleted=True)

    # ==================================================
    # CONSULTAS GENERALES
    # ==================================================
    def recientes(self, limite=50):
        return self.order_by("-created_at")[:limite]

    def actualizados_recientemente(self):
        return self.order_by("-updated_at")
    
    # ==================================================
    # FILTROS SIRTEE COMUNES
    # ==================================================

    def por_cueanexo(
        self,
        cueanexo
    ):

        return self.filter(
            cueanexo=cueanexo
        )



    def por_cueanexos(
        self,
        cueanexos
    ):

        return self.filter(
            cueanexo__in=cueanexos
        )



    def estado(
        self,
        estado
    ):

        return self.filter(
            estado=estado
        )


    # ==================================================
    # AUDITORÍA
    # ==================================================
    def con_auditoria(self):
        return self.prefetch_related("auditorias")

    # ==================================================
    # OPERACIONES MASIVAS
    # ==================================================
    def borrar_logico(self):
        return self.update(
            is_deleted=True,
            deleted_at=timezone.now()
        )

    def restaurar(self):
        return self.update(
            is_deleted=False,
            deleted_at=None
        )

    def borrar_fisico(self):
        return super().delete()