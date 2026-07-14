from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.validators import (
    MinValueValidator,
    MaxValueValidator,
)
from django.core.exceptions import ValidationError


from apps.sirtee.models.mixins import (
    AuditoriaMixin,
    TimestampMixin,
    SoftDeleteMixin,
)

from apps.sirtee.managers.secure import (
    IntervencionManager
)


from apps.sirtee.catalogos.models import (
    TipoIntervencion,
    EstadoIntervencion,
    Prioridad,
    FuenteFinanciamiento,
    OrganismoResponsable,
)



class Intervencion(
    AuditoriaMixin,
    TimestampMixin,
    SoftDeleteMixin,
    models.Model,
):


    """
    Acción correctiva asociada
    a un hallazgo técnico.
    """



    # ==================================================
    # RELACIÓN
    # ==================================================

    hallazgo = models.ForeignKey(

        "sirtee.Hallazgo",

        on_delete=models.CASCADE,

        related_name="intervenciones",

        db_index=True,

        verbose_name="Hallazgo asociado",

    )



    # ==================================================
    # INFORMACIÓN GENERAL
    # ==================================================

    titulo = models.CharField(
        max_length=255,
        verbose_name="Título",
    )


    descripcion = models.TextField(
        verbose_name="Descripción técnica",
    )



    # ==================================================
    # CLASIFICACIÓN
    # ==================================================

    tipo = models.ForeignKey(

        TipoIntervencion,

        on_delete=models.PROTECT,

        related_name="intervenciones",

    )


    estado = models.ForeignKey(

        EstadoIntervencion,

        on_delete=models.PROTECT,

        related_name="intervenciones",

        db_index=True,

    )


    prioridad = models.ForeignKey(

        Prioridad,

        on_delete=models.PROTECT,

        related_name="intervenciones",

        blank=True,

        null=True,

    )



    # ==================================================
    # EJECUCIÓN
    # ==================================================

    empresa = models.ForeignKey(

        "sirtee.Empresa",

        on_delete=models.SET_NULL,

        related_name="intervenciones",

        null=True,

        blank=True,

    )


    responsable = models.CharField(

        max_length=150,

        blank=True,

        null=True,

    )


    equipo_ejecutor = models.CharField(

        max_length=255,

        blank=True,

        null=True,

    )



    # ==================================================
    # FINANCIAMIENTO
    # ==================================================

    organismo_responsable = models.ForeignKey(

        OrganismoResponsable,

        on_delete=models.PROTECT,

        related_name="intervenciones",

        blank=True,

        null=True,

    )


    fuente_financiamiento = models.ForeignKey(

        FuenteFinanciamiento,

        on_delete=models.PROTECT,

        related_name="intervenciones",

        blank=True,

        null=True,

    )



    # ==================================================
    # FECHAS
    # ==================================================

    fecha_inicio = models.DateTimeField(
        blank=True,
        null=True,
    )


    fecha_fin = models.DateTimeField(
        blank=True,
        null=True,
    )


    fecha_estimada_fin = models.DateField(
        blank=True,
        null=True,
    )



    # ==================================================
    # COSTOS
    # ==================================================

    costo_estimado = models.DecimalField(

        max_digits=14,

        decimal_places=2,

        blank=True,

        null=True,

    )


    costo_real = models.DecimalField(

        max_digits=14,

        decimal_places=2,

        blank=True,

        null=True,

    )



    # ==================================================
    # AVANCE
    # ==================================================

    porcentaje_avance = models.PositiveIntegerField(

        default=0,

        validators=[

            MinValueValidator(0),

            MaxValueValidator(100),

        ],

    )


    observaciones = models.TextField(

        blank=True,

        null=True,

    )



    objects = IntervencionManager()



    class Meta:

        db_table = "sirtee_intervenciones"

        verbose_name = (
            "Intervención"
        )


        verbose_name_plural = (
            "Intervenciones"
        )


        ordering = [
            "-id"
        ]


        indexes = [

            models.Index(
                fields=[
                    "estado",
                    "fecha_inicio"
                ]
            ),

            models.Index(
                fields=[
                    "hallazgo"
                ]
            ),

        ]



    # ==================================================
    # REPRESENTACIÓN
    # ==================================================

    def __str__(self):

        return (
            f"{self.titulo} "
            f"- {self.estado.nombre}"
        )



    def save(self, *args, **kwargs):

        self.full_clean()

        super().save(
            *args,
            **kwargs
        )
        
    # ==================================================
    # VALIDACIÓN
    # ==================================================

    def clean(self):


        errores = {}



        if (

            self.fecha_inicio

            and

            self.fecha_fin

            and

            self.fecha_fin < self.fecha_inicio

        ):

            errores["fecha_fin"] = (
                "La fecha final no puede "
                "ser anterior al inicio."
            )



        if (

            self.costo_estimado

            and

            self.costo_estimado < 0

        ):

            errores["costo_estimado"] = (
                "El costo no puede ser negativo."
            )



        if (

            self.costo_real

            and

            self.costo_real < 0

        ):

            errores["costo_real"] = (
                "El costo no puede ser negativo."
            )



        if errores:

            raise ValidationError(
                errores
            )



    # ==================================================
    # NEGOCIO - CAMBIO DE ESTADO
    # ==================================================
    def puede_cambiar_a(
        self,
        nuevo_estado
    ):
        """
        Determina si la transición de estado
        es válida según el flujo de trabajo.
        """

        flujo = {

            "PENDIENTE": [
                "EN_EJECUCION",
                "CANCELADA",
            ],

            "EN_EJECUCION": [
                "PAUSADA",
                "FINALIZADA",
                "CANCELADA",
            ],

            "PAUSADA": [
                "EN_EJECUCION",
                "CANCELADA",
            ],

            "FINALIZADA": [],

            "CANCELADA": [],

        }


        return (
            nuevo_estado
            in flujo.get(
                self.estado.codigo,
                []
            )
        )

    def cambiar_estado(
        self,
        codigo_estado,
        update_fields=None
    ):
        """
        Cambia el estado de la intervención
        utilizando el catálogo institucional.
        """
        if not self.puede_cambiar_a(
            codigo_estado
        ):

            raise ValidationError(
                f"No se puede cambiar "
                f"de {self.estado.codigo} "
                f"a {codigo_estado}"
            )


        self.estado = (
            EstadoIntervencion.objects.get(
                codigo=codigo_estado
            )
        )
        
        campos = [
            "estado",
        ]

        if update_fields:
            campos.extend(update_fields)

        self.save(
            update_fields=campos
        )



    def iniciar(self):

        self.estado = (
            EstadoIntervencion.objects.get(
                codigo="EN_EJECUCION"
            )
        )


        self.fecha_inicio = timezone.now()


        self.save(
            update_fields=[
                "estado",
                "fecha_inicio",
                "updated_at",
            ]
        )



    def pausar(self):

        self.cambiar_estado(
            "PAUSADA"
        )



    def finalizar(self):

        self.estado = (
            EstadoIntervencion.objects.get(
                codigo="FINALIZADA"
            )
        )


        self.porcentaje_avance = 100


        self.fecha_fin = timezone.now()


        self.save(
            update_fields=[
                "estado",
                "porcentaje_avance",
                "fecha_fin",
                "updated_at",
            ]
        )



    def cancelar(self):

        self.cambiar_estado(
            "CANCELADA"
        )



    # ==================================================
    # PROPIEDADES
    # ==================================================

    @property
    def esta_activa(self):

        return (
            self.estado.codigo
            ==
            "EN_EJECUCION"
        )



    @property
    def esta_finalizada(self):

        return (
            self.estado.codigo
            ==
            "FINALIZADA"
        )



    @property
    def esta_pausada(self):

        return (
            self.estado.codigo
            ==
            "PAUSADA"
        )



    @property
    def esta_cancelada(self):

        return (
            self.estado.codigo
            ==
            "CANCELADA"
        )



    @property
    def progreso(self):

        return (
            f"{self.porcentaje_avance}%"
        )



    @property
    def dias_ejecucion(self):

        if not self.fecha_inicio:

            return 0


        fin = (
            self.fecha_fin
            or
            timezone.now()
        )


        return (
            fin.date()
            -
            self.fecha_inicio.date()
        ).days



    @property
    def diferencia_costo(self):

        if (
            self.costo_real
            and
            self.costo_estimado
        ):

            return (
                self.costo_real
                -
                self.costo_estimado
            )


        return 0



    @property
    def tiene_sobrecosto(self):

        return (
            self.diferencia_costo > 0
        )