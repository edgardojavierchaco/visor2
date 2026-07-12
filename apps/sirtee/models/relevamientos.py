from django.db import models
from apps.sirtee.models.mixins import AuditoriaMixin, TimestampMixin, SoftDeleteMixin
from apps.sirtee.managers.secure import (
    RelevamientoManager
)
from apps.sirtee.data.padron import PadronEscuelas
from apps.usuarios.models import UsuariosVisualizador

class Relevamiento(AuditoriaMixin, TimestampMixin, SoftDeleteMixin, models.Model):
    """
    Relevamiento técnico de una escuela.

    Fuente de escuela:
    - CapaUnicaOfertas (vista externa, read-only)

    Este modelo es el núcleo operativo de SIRTEE.
    """

    # --------------------------------------
    # RELACIÓN CON PADRÓN EDUCATIVO
    # --------------------------------------

    cueanexo = models.CharField(max_length=9, db_index=True)
    
    # Puede guardar uno o varios CUI
    cui = models.JSONField(
        default=list,
        blank=True,
        verbose_name="CUI seleccionados",
    )
    
    # Puede guardar una o varias ofertas
    oferta = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Ofertas seleccionadas",
    )

    # --------------------------------------
    # DATOS DEL RELEVAMIENTO
    # --------------------------------------

    fecha = models.DateField(db_index=True)

    estado = models.CharField(
        max_length=30,
        choices=[
            ("BORRADOR", "Borrador"),
            ("EN_PROCESO", "En proceso"),
            ("FINALIZADO", "Finalizado"),
            ("OBSERVADO", "Observado"),
        ],
        default="BORRADOR"
    )

    tipo_relevamiento = models.CharField(
        max_length=50,
        choices=[
            ("INFRAESTRUCTURA", "Infraestructura"),
            ("EQUIPAMIENTO", "Equipamiento"),
            ("GENERAL", "General"),
        ],
        default="GENERAL"
    )

    observaciones = models.TextField(blank=True, null=True)

    # --------------------------------------
    # CONTROL OPERATIVO
    # --------------------------------------

    usuario_creador=models.ForeignKey(
        UsuariosVisualizador,
        on_delete=models.PROTECT,
        related_name="relevamientos_creados",
        null=True,
        blank=True,
        editable=False,
    )

    finalizado = models.BooleanField(default=False)

    fecha_finalizacion = models.DateTimeField(null=True, blank=True)

    # --------------------------------------
    # AUDITORÍA / QUERYSET / MANAGER
    # --------------------------------------

    objects = RelevamientoManager()

    # --------------------------------------
    # META
    # --------------------------------------

    class Meta:
        db_table = "sirtee_relevamientos"
        verbose_name = "Relevamiento"
        verbose_name_plural = "Relevamientos"
        ordering = ["-fecha"]

    def __str__(self):
        if self.oferta:
            return (
                f"{self.cueanexo} - "
                f"{', '.join(self.oferta)} - "
                f"{self.fecha}"
            )
        
        return f"{self.cueanexo} - {self.fecha}"

    # --------------------------------------
    # LÓGICA DE NEGOCIO
    # --------------------------------------
    
    def get_escuela(self):

        return (
            PadronEscuelas
            .get_by_cueanexos(
                self.cueanexo
            )
        )

    def finalizar(self, usuario=None):
        """
        Marca el relevamiento como finalizado.
        """
        from django.utils import timezone

        self.finalizado = True
        self.estado = "FINALIZADO"
        self.fecha_finalizacion = timezone.now()

        if usuario:
            self.usuario_creador = usuario

        self.save()

    def en_proceso(self):
        """
        Marca el relevamiento como en proceso.
        """
        self.estado = "EN_PROCESO"
        self.save(update_fields=["estado"])

    def tiene_hallazgos(self):
        """
        Hook para futura integración con hallazgos.
        """
        return hasattr(self, "hallazgos") and self.hallazgos.exists()
    
    def cantidad_hallazgos(self):

        return self.hallazgos.count()


    def hallazgos_abiertos(self):

        return self.hallazgos.filter(
            estado="ABIERTO"
        ).count()
    
    # ==========================================================
    # OFERTAS SELECCIONADAS
    # ==========================================================

    def ofertas_texto(self):
        """
        Devuelve las ofertas en formato legible.
        """

        if not self.oferta:
            return ""

        return ", ".join(self.oferta)


    def cuis_texto(self):
        """
        Devuelve los CUI en formato legible.
        """

        if not self.cui:
            return ""

        return ", ".join(self.cui)


    def cantidad_ofertas(self):

        return len(self.oferta or [])


    def tiene_oferta(self, oferta):

        return oferta in (self.oferta or [])


    def tiene_cui(self, cui):

        return cui in (self.cui or [])