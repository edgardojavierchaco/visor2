from django.db import models
# from .modelo_oficial import *

# #--------------------------------FLUIDEZ OCTUBRE 2026-----------------------------------


# class Fluidez_Lectora_Octubre_2026 (models.Model):
#     """
#     Evaluación de Fluidez Lectora - Octubre 2026.
#     Subtipo exclusivo de Evaluación (especialización).
#     Relación: 1:1 con Evaluación y 1:1 con AlumnoFluidez2026.
#     """
#     OPCIONES_EVALUACION = [
#         ('A', 'A'),
#         ('B', 'B'),
#         ('C', 'C'),
#         ('D', 'D'),
#         ('NORESPONDE', 'NoResponde'),
#     ]
#     OPCIONES_ASISTENCIA = [
#         ('PRESENTE', 'Presente'),
#         ('AUSENTE', 'Ausente'),
#     ]

#     evaluacion = models.OneToOneField(
#         Evaluacion,
#         on_delete=models.CASCADE,
#         primary_key=True,
#         related_name="fluidez_lectora_octubre_2026",
#     )
#     alumno = models.OneToOneField(
#         'AlumnoFluidez2026',
#         on_delete=models.CASCADE,
#         related_name="fluidez_lectora_octubre_2026",
#         null=True,
#         blank=True,
#     )
#     cantidad_palabras_leidas = models.IntegerField(default=0, null=True)
#     pregunta_1 = models.CharField(max_length=10, choices=OPCIONES_EVALUACION, blank=True, null=True)
#     pregunta_2 = models.CharField(max_length=10, choices=OPCIONES_EVALUACION, blank=True, null=True)
#     pregunta_3 = models.CharField(max_length=10, choices=OPCIONES_EVALUACION, blank=True, null=True)
#     pregunta_4 = models.CharField(max_length=10, choices=OPCIONES_EVALUACION, blank=True, null=True)
#     pregunta_5 = models.CharField(max_length=10, choices=OPCIONES_EVALUACION, blank=True, null=True)
#     pregunta_6 = models.CharField(max_length=10, choices=OPCIONES_EVALUACION, blank=True, null=True)
#     asistencia = models.CharField(choices=OPCIONES_ASISTENCIA, default='AUSENTE')
#     encargado_carga = models.CharField(max_length=9)

#     class Meta:
#         db_table = '"datos_oficiales"."fluidez_lectora_octubre_2026"'
#         verbose_name = "Fluidez Lectora Octubre 2026"
#         verbose_name_plural = "Fluidez Lectora Octubre 2026"

#     def __str__(self):
#         alumno_info = self.alumno.nombre if self.alumno else f"Eval #{self.evaluacion_id}"
#         return f"Fluidez Lectora Octubre 2026 - {alumno_info}"



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

class TemporalCargaTabuladoresFluidez2026Eliminar(models.Model):
    region = models.CharField(max_length=100)
    tabuladores_permitidos = models.IntegerField(default=0)

    class Meta:
        managed = False  
        db_table = '"datos_oficiales"."temporal_carga_tabuladores_fluidez_2026_eliminar"'  
    def __str__(self):
        return f"{self.region} (Tabuladores: {self.tabuladores_permitidos})"