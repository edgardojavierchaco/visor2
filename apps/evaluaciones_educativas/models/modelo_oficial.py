"""
Modelo oficial de evaluaciones: operativo -> evaluacion -> datos_completo.

`Evaluacion` es el padre de todos los exámenes (una fila por examen rendido).
Cada operativo guarda sus datos propios en su tabla hija, cuya PK es
`evaluacion_id` (especialización exclusiva: una evaluación tiene a lo sumo
una hija). `tipo_evaluacion` indica cuál es la tabla hija.

`DatosCompleto` asocia la evaluación con el alumno y la escuela.
"""
from django.db import models, transaction


class Operativo(models.Model):
    tipo_operativo = models.CharField(max_length=100)
    anio = models.IntegerField()
    mes = models.IntegerField()

    class Meta:
        db_table = '"datos_oficiales"."operativo"'
        unique_together = ('tipo_operativo', 'anio', 'mes')

    def __str__(self):
        return f"{self.tipo_operativo} {self.mes:02d}/{self.anio}"


class Evaluacion(models.Model):
    """Padre de todos los exámenes. Los datos propios de cada operativo están
    en la tabla hija que corresponde a `tipo_evaluacion`."""
    operativo = models.ForeignKey(Operativo, on_delete=models.PROTECT, related_name='evaluaciones')
    tipo_evaluacion = models.CharField(max_length=100, db_index=True)

    class Meta:
        db_table = '"datos_oficiales"."evaluacion"'

    def __str__(self):
        return f"{self.tipo_evaluacion} - {self.operativo}"

    @property
    def hija(self):
        """Registro de la tabla hija de esta evaluación, o None."""
        modelo = EvaluacionHija.registro.get(self.tipo_evaluacion)
        return modelo.objects.filter(pk=self.pk).first() if modelo else None


class DatosCompleto(models.Model):
    """
    Alumno y escuela de una evaluación. Los alumnos salen de la vista
    materializada de SGE con estado_inscripcion = 'Regular'.

    - *_original: cueanexo y grado del alumno al momento de cargar el examen
      (donde fue evaluado). No se modifican nunca; la visualización usa estos.
    - cueanexo / id_grado: inscripción Regular actual del alumno. Si el alumno
      cambia de escuela o de grado se actualizan con `actualizar_inscripcion`.
    El grado es c_grado_nivel_servicio de SGE.
    """
    id_uuid_alumno = models.CharField(max_length=50, db_index=True)  # id_persona de SGE
    cueanexo_original = models.CharField(max_length=15)             # cueanexo donde se evaluó
    id_grado_original = models.BigIntegerField(null=True, blank=True)  # grado donde se evaluó
    cueanexo = models.CharField(max_length=15)                      # cueanexo actual (Regular)
    id_grado = models.BigIntegerField(null=True, blank=True)        # grado actual (Regular)
    evaluacion = models.OneToOneField(Evaluacion, on_delete=models.CASCADE, related_name='datos_completo')

    class Meta:
        db_table = '"datos_oficiales"."datos_completo"'

    def __str__(self):
        return f"{self.id_uuid_alumno} - {self.cueanexo_original} - eval {self.evaluacion_id}"

    def actualizar_inscripcion(self, cueanexo, id_grado):
        """Actualiza la inscripción actual; los datos originales no cambian."""
        if (self.cueanexo, self.id_grado) != (cueanexo, id_grado):
            self.cueanexo, self.id_grado = cueanexo, id_grado
            self.save(update_fields=['cueanexo', 'id_grado'])


class EvaluacionHija(models.Model):
    """
    Base de las tablas hijas (una por operativo). Cada subclase define:
        TIPO_EVALUACION = 'Fluidez Lectora Octubre 2026'
        OPERATIVO = ('Fluidez Lectora', 2026, 10)   # tipo_operativo, anio, mes
    y queda registrada sola para que `Evaluacion.hija` la encuentre.
    """
    TIPO_EVALUACION = None
    OPERATIVO = None
    registro = {}  # tipo_evaluacion -> modelo hijo

    evaluacion = models.OneToOneField(
        Evaluacion, on_delete=models.CASCADE, primary_key=True, related_name='%(class)s',
    )

    class Meta:
        abstract = True

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls.TIPO_EVALUACION:
            EvaluacionHija.registro[cls.TIPO_EVALUACION] = cls

    @classmethod
    def operativo(cls):
        tipo, anio, mes = cls.OPERATIVO
        return Operativo.objects.get_or_create(tipo_operativo=tipo, anio=anio, mes=mes)[0]

    @classmethod
    def de_alumno(cls, id_alumno):
        """Examen de este operativo ya cargado para el alumno, o None."""
        return cls.objects.select_related('evaluacion__datos_completo').filter(
            evaluacion__operativo=cls.operativo(),
            evaluacion__datos_completo__id_uuid_alumno=str(id_alumno),
        ).first()

    @classmethod
    def crear(cls, *, id_alumno, cueanexo_original, id_grado_original=None,
              cueanexo=None, id_grado=None, **campos):
        """
        Crea padre (evaluacion) + datos_completo + hija en una transacción.
        Los *_original son la inscripción Regular del alumno al cargar el
        examen; los actuales, si no se pasan, arrancan iguales a los originales.
        """
        cueanexo = cueanexo or cueanexo_original
        id_grado = id_grado if id_grado is not None else id_grado_original
        # La app está ruteada a otra base (routers.py): la transacción va en esa.
        with transaction.atomic(using=cls.objects.db):
            evaluacion = Evaluacion.objects.create(
                operativo=cls.operativo(), tipo_evaluacion=cls.TIPO_EVALUACION,
            )
            DatosCompleto.objects.create(
                evaluacion=evaluacion, id_uuid_alumno=str(id_alumno),
                cueanexo_original=cueanexo_original, id_grado_original=id_grado_original,
                cueanexo=cueanexo, id_grado=id_grado,
            )
            return cls.objects.create(evaluacion=evaluacion, **campos)

    def delete(self, *args, **kwargs):
        # Borrar el padre arrastra por CASCADE a la hija y a datos_completo.
        return self.evaluacion.delete(*args, **kwargs)
