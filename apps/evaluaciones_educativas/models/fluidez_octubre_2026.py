from django.db import models
from .modelo_oficial import *

#--------------------------------FLUIDEZ OCTUBRE 2026-----------------------------------


class FluidezLectoraOctubre2026(EvaluacionHija):
    """
    Examen de Fluidez Lectora - Octubre 2026. Tabla hija de Evaluacion
    (PK = evaluacion_id). El alumno es de SGE (otra base): alumno_id guarda
    su id_persona, igual que datos_completo.id_uuid_alumno.
    """
    TIPO_EVALUACION = 'Fluidez Lectora Octubre 2026'
    OPERATIVO = ('Fluidez Lectora', 2026, 10)

    OPCIONES_EVALUACION = [
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C'),
        ('D', 'D'),
        ('NORESPONDE', 'NoResponde'),
    ]
    OPCIONES_ASISTENCIA = [
        ('PRESENTE', 'Presente'),
        ('AUSENTE', 'Ausente'),
    ]

    cantidad_palabras_leidas = models.IntegerField(default=0, null=True, blank=True)
    pregunta_1 = models.CharField(max_length=10, choices=OPCIONES_EVALUACION, blank=True, null=True)
    pregunta_2 = models.CharField(max_length=10, choices=OPCIONES_EVALUACION, blank=True, null=True)
    pregunta_3 = models.CharField(max_length=10, choices=OPCIONES_EVALUACION, blank=True, null=True)
    pregunta_4 = models.CharField(max_length=10, choices=OPCIONES_EVALUACION, blank=True, null=True)
    pregunta_5 = models.CharField(max_length=10, choices=OPCIONES_EVALUACION, blank=True, null=True)
    pregunta_6 = models.CharField(max_length=10, choices=OPCIONES_EVALUACION, blank=True, null=True)
    asistencia = models.CharField(max_length=10, choices=OPCIONES_ASISTENCIA, default='AUSENTE')
    encargado_carga = models.CharField(max_length=9)
    alumno_id = models.IntegerField(null=True, blank=True, db_index=True)

    class Meta:
        db_table = '"datos_oficiales"."fluidez_lectora_octubre_2026"'
        verbose_name = "Fluidez Lectora Octubre 2026"
        verbose_name_plural = "Fluidez Lectora Octubre 2026"

    def __str__(self):
        return f"Fluidez Lectora Octubre 2026 - alumno {self.alumno_id} (eval #{self.evaluacion_id})"


class CierreCargaFluidezOctubre2026(models.Model):
    """Estado de la carga de exámenes de un grado de una escuela."""
    cueanexo = models.CharField(max_length=15)
    anio_grado = models.CharField(max_length=50)
    estado_carga = models.BooleanField(default=False)  # True = carga cerrada
    cuil_tabulador = models.CharField(max_length=20, null=True, blank=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = '"datos_oficiales"."cierre_carga_fluidez_octubre_2026"'
        unique_together = ('cueanexo', 'anio_grado')

    def __str__(self):
        estado = 'cerrada' if self.estado_carga else 'abierta'
        return f"{self.cueanexo} - {self.anio_grado}: {estado}"


#-------------tabla aplicadores----------------------------

class AplicadoresFluidezOctubre2026(models.Model):
    """Datos personales del aplicador. Una fila por persona; sus secciones
    están en SeccionesAplicadorFluidezOctubre2026."""
    cuil = models.CharField(max_length=11, primary_key=True)
    apellido = models.CharField(max_length=250)
    nombre = models.CharField(max_length=250)
    correo = models.EmailField(max_length=250, null=True, blank=True)
    celular = models.CharField(max_length=20, null=True, blank=True)
    region = models.CharField(max_length=100)  # región del regional que lo cargó

    class Meta:
        db_table = '"datos_oficiales"."aplicadores_fluidez_octubre_2026"'

    def __str__(self):
        return f"{self.apellido}, {self.nombre} - {self.cuil}"


class SeccionesAplicadorFluidezOctubre2026(models.Model):
    """Sección asignada a un aplicador. Los datos de escuela y sección se
    copian de public.trayectoria_alumnos_sge (base sge_nacion) al asignarla."""
    aplicador = models.ForeignKey(
        AplicadoresFluidezOctubre2026,
        on_delete=models.CASCADE,
        related_name='secciones',
    )
    # id de la sección en SGE. Único: una sección tiene un solo aplicador.
    id_seccion = models.BigIntegerField(unique=True)
    id_institucion = models.BigIntegerField()
    cueanexo = models.CharField(max_length=15)
    c_grado_nivel_servicio = models.BigIntegerField()
    anio_grado = models.CharField(max_length=50, null=True, blank=True)
    turno = models.CharField(max_length=50, null=True, blank=True)
    ciclo_lectivo = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        db_table = '"datos_oficiales"."secciones_aplicadores_fluidez_octubre_2026"'

    def __str__(self):
        return f"{self.cueanexo} - {self.anio_grado} sección {self.id_seccion} ({self.turno}) - {self.aplicador_id}"

#-------------tabla tabuladores----------------------------

class TabuladoresFluidezOctubre2026(models.Model):
    apellido = models.CharField(max_length=250, null=True, blank=True)
    nombre = models.CharField(max_length=250, null=True, blank=True)
    cuil = models.CharField(max_length=20, primary_key=True)
    correo = models.CharField(max_length=250, null=True, blank=True)
    celular = models.CharField(max_length=250, null=True, blank=True)
    region = models.CharField(max_length=250, null=True, blank=True)
    lista_cueanexos = models.JSONField(default=list, null=True, blank=True)

    class Meta:
        db_table = '"datos_oficiales"."tabuladores_fluidez_octubre_2026"'
    
    def __str__(self):
        return f"{self.apellido} {self.nombre} - {self.cuil}"


class TabuladoresCueanexoFluidezOctubre2026(models.Model):
    """
    Igual a TabuladoresFluidezOctubre2026 pero con una fila por cueanexo
    (en vez de lista_cueanexos) y el estado de la carga de cada cueanexo.
    Se puebla desde la tabla vieja con `poblar_desde_tabuladores`.
    """
    apellido = models.CharField(max_length=250, null=True, blank=True)
    nombre = models.CharField(max_length=250, null=True, blank=True)
    cuil = models.CharField(max_length=20, db_index=True)
    correo = models.CharField(max_length=250, null=True, blank=True)
    celular = models.CharField(max_length=250, null=True, blank=True)
    region = models.CharField(max_length=250, null=True, blank=True)
    cueanexo = models.CharField(max_length=15, db_index=True)
    estado_carga = models.BooleanField(default=False)  # True = carga cerrada

    class Meta:
        db_table = '"datos_oficiales"."tabuladores_cueanexo_fluidez_octubre_2026"'
        unique_together = ('cuil', 'cueanexo')

    def __str__(self):
        estado = 'cerrada' if self.estado_carga else 'abierta'
        return f"{self.apellido} {self.nombre} - {self.cuil} - {self.cueanexo}: {estado}"

    @classmethod
    def poblar_desde_tabuladores(cls):
        """Crea una fila por (tabulador, cueanexo) de lista_cueanexos. Las
        filas que ya existen no se tocan, así conservan su estado_carga."""
        filas = [
            cls(apellido=t.apellido, nombre=t.nombre, cuil=t.cuil, correo=t.correo,
                celular=t.celular, region=t.region, cueanexo=str(cue).strip())
            for t in TabuladoresFluidezOctubre2026.objects.all()
            for cue in dict.fromkeys(t.lista_cueanexos or [])
            if str(cue).strip()
        ]
        return cls.objects.bulk_create(filas, ignore_conflicts=True)


class TemporalCargaTabuladoresFluidez2026Eliminar(models.Model):
    region = models.CharField(max_length=100)
    tabuladores_permitidos = models.IntegerField(default=0)

    class Meta:
        managed = False  
        db_table = '"datos_oficiales"."temporal_carga_tabuladores_fluidez_2026_eliminar"'  
    def __str__(self):
        return f"{self.region} (Tabuladores: {self.tabuladores_permitidos})"