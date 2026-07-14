from django.db import models
from django.utils import timezone

from apps.sirtee.models.mixins import (
    AuditoriaMixin,
    TimestampMixin,
    SoftDeleteMixin,
)

from apps.sirtee.managers.secure import (
    HallazgoManager
)
from apps.sirtee.models.relevamientos import Relevamiento

from apps.usuarios.models import UsuariosVisualizador

from django.core.exceptions import ValidationError
from apps.sirtee.models.evidencias import EvidenciaHallazgo

from apps.sirtee.catalogos.models import (
    SistemaConstructivo,
    AreaAfectada,
    TipoHallazgo,
    Criticidad,
    Riesgo,
    EstadoHallazgo,
)


class Hallazgo(
    AuditoriaMixin,
    TimestampMixin,
    SoftDeleteMixin,
    models.Model,
):
    """
    Hallazgo técnico detectado durante un relevamiento.

    Toda la clasificación se realiza mediante
    catálogos institucionales.
    """

    # ==========================================================
    # RELACIÓN
    # ==========================================================

    relevamiento = models.ForeignKey(
        Relevamiento,
        on_delete=models.CASCADE,
        related_name="hallazgos",
    )

    # ==========================================================
    # CLASIFICACIÓN TÉCNICA
    # ==========================================================

    sistema_constructivo = models.ForeignKey(
        SistemaConstructivo,
        on_delete=models.PROTECT,
        related_name="hallazgos",
        db_index=True,
    )

    area_afectada = models.ForeignKey(
        AreaAfectada,
        on_delete=models.PROTECT,
        related_name="hallazgos",
        db_index=True,
    )

    tipo_hallazgo = models.ForeignKey(
        TipoHallazgo,
        on_delete=models.PROTECT,
        related_name="hallazgos",
        db_index=True,
    )

    criticidad = models.ForeignKey(
        Criticidad,
        on_delete=models.PROTECT,
        related_name="hallazgos",
        db_index=True,
    )

    riesgo = models.ForeignKey(
        Riesgo,
        on_delete=models.PROTECT,
        related_name="hallazgos",
        db_index=True,
    )

    estado = models.ForeignKey(
        EstadoHallazgo,
        on_delete=models.PROTECT,
        related_name="hallazgos",
        db_index=True,
    )

    # ==========================================================
    # INFORMACIÓN TÉCNICA
    # ==========================================================

    titulo = models.CharField(
        max_length=255,
        db_index=True,
    )

    descripcion = models.TextField()
    
    fecha_deteccion = models.DateField(
        default=timezone.now,
        db_index=True
    )

    ubicacion = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Ej.: Aula 4, Galería Norte, Cubierta Sector B",
    )
    
    referencia_espacial = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Ej: Eje B, columna 4, techo sector norte"
    )

    observacion_tecnica = models.TextField(
        blank=True,
        null=True,
    )

    recomendacion = models.TextField(
        blank=True,
        null=True,
    )
    
    requiere_seguimiento = models.BooleanField(
        default=False
    )

    # ==========================================================
    # RESPONSABLES
    # ==========================================================

    usuario_responsable = models.ForeignKey(
        UsuariosVisualizador,
        on_delete=models.PROTECT,
        related_name="hallazgos_responsables",
        null=True,
        blank=True,
    )

    fecha_resolucion = models.DateTimeField(
        blank=True,
        null=True,
        db_index=True
    )

    # ==========================================================
    # MANAGER
    # ==========================================================

    objects = HallazgoManager()

    # ==========================================================
    # META
    # ==========================================================

    class Meta:

        db_table = "sirtee_hallazgos"

        verbose_name = "Hallazgo"

        verbose_name_plural = "Hallazgos"

        ordering = [
            "-id"
        ]

    # ==========================================================
    # REPRESENTACIÓN
    # ==========================================================

    def __str__(self):

        return (
            f"{self.titulo}"
            f" ({self.criticidad.nombre})"
        )

    # ==========================================================
    # LÓGICA DE NEGOCIO
    # ==========================================================
    
    def save(self,*args,**kwargs):

        self.full_clean()

        super().save(*args,**kwargs)
        

    def marcar_resuelto(self, usuario=None):
        """
        Marca el hallazgo como resuelto.
        """

        self.estado = EstadoHallazgo.objects.get(
            codigo="RESUELTO"
        )

        self.fecha_resolucion = timezone.now()

        if usuario:

            self.usuario_responsable = usuario

        self.save()

    def es_critico(self):
        """
        Determina si el hallazgo
        es crítico.
        """

        return (
            self.criticidad.codigo
            == "CRITICA"
        )

    def requiere_intervencion_inmediata(self):
        """
        Determina si requiere
        intervención inmediata.
        """
        estados = [
            "ABIERTO",
            "EN_ANALISIS",
        ]
        
        return (

            self.criticidad.codigo in [

                "ALTA",

                "CRITICA",

            ]

            and

            self.estado.codigo in estados

        )

    def nivel_criticidad(self):
        """
        Devuelve un valor entero
        para ordenar criticidad.
        """

        orden = {

            "CRITICA": 4,

            "ALTA": 3,

            "MEDIA": 2,

            "BAJA": 1,

        }

        return orden.get(

            self.criticidad.codigo,

            0,

        )
    
    def clean(self):

        errores = {}


        if self.titulo:

            self.titulo = self.titulo.strip()


        if not self.descripcion:

            errores["descripcion"] = (
                "Debe ingresar una descripción técnica."
            )


        if (
            self.criticidad
            and self.criticidad.codigo == "CRITICA"
        ):

            if not self.recomendacion:

                errores["recomendacion"] = (
                    "Los hallazgos críticos requieren "
                    "recomendación técnica."
                )


        if (
            self.estado
            and self.estado.codigo == "RESUELTO"
        ):

            if not self.fecha_resolucion:

                errores["fecha_resolucion"] = (
                    "Debe indicar fecha de resolución."
                )


        if errores:

            raise ValidationError(
                errores
            )

    def cantidad_intervenciones(self):

        return self.intervenciones.count()

    def tiene_intervencion_activa(self):

        return self.intervenciones.filter(

            estado__codigo="EN_EJECUCION"

        ).exists()

    @property
    def esta_resuelto(self):

        return (

            self.estado.codigo

            == "RESUELTO"

        )

    @property
    def esta_abierto(self):

        return (

            self.estado.codigo

            == "ABIERTO"

        )

    @property
    def color(self):
        """
        Color institucional para dashboard/mapas.
        """

        colores = {

            "CRITICA": "#dc3545",

            "ALTA": "#fd7e14",

            "MEDIA": "#ffc107",

            "BAJA": "#198754",

        }

        return colores.get(

            self.criticidad.codigo,

            "#6c757d",

        )
    
    @property
    def badge_color(self):

        colores = {

            "CRITICA": "danger",

            "ALTA": "warning",

            "MEDIA": "info",

            "BAJA": "success",

        }

        return colores.get(
            self.criticidad.codigo,
            "secondary"
        )

    @property
    def icono(self):
        """
        Ícono para mapas y dashboards.
        """

        iconos = {

            "CRITICA": "bi-exclamation-octagon-fill",

            "ALTA": "bi-exclamation-triangle-fill",

            "MEDIA": "bi-tools",

            "BAJA": "bi-check-circle",

        }

        return iconos.get(

            self.criticidad.codigo,

            "bi-circle",

        )
    
    @property
    def titulo_completo(self):

        return (
            f"{self.tipo_hallazgo.nombre} - "
            f"{self.titulo}"
        )
    
    # ==========================================================
    # EVIDENCIAS
    # ==========================================================

    @property
    def cantidad_evidencias(self):
        """
        Cantidad total de archivos asociados.
        """
        return self.evidencias.count()

    @property
    def tiene_evidencias(self):
        """
        Indica si el hallazgo posee archivos.
        """
        return self.evidencias.exists()

    @property
    def primera_evidencia(self):
        """
        Devuelve la primera evidencia.
        """
        return self.evidencias.first()

    def obtener_evidencias(self):
        """
        Devuelve todas las evidencias ordenadas.
        """
        return self.evidencias.order_by("-fecha")

    def obtener_imagenes(self):
        """
        Devuelve únicamente imágenes.
        """
        extensiones = (
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".bmp",
            ".webp",
        )

        return self.evidencias.filter(
            tipo_archivo=EvidenciaHallazgo.TipoArchivo.IMAGEN
        )

    def obtener_documentos(self):
        """
        Devuelve documentos.
        """
        return self.evidencias.filter(
            tipo_archivo=EvidenciaHallazgo.TipoArchivo.DOCUMENTO
        )