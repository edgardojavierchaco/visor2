import re 
from django.core.exceptions import ValidationError
from django.db import models
from apps.usuarios.models import UsuariosVisualizador
from django.core.validators import MinValueValidator, MaxValueValidator

class curso(models.Model):
    nom_curso=models.CharField(max_length=15, verbose_name='Curso')
    
    def __str__(self):
        return self.nom_curso
    
    class Meta:
        verbose_name='Curso'
        verbose_name_plural='Cursos'
        db_table='Curso'

class division(models.Model):
    nom_division=models.CharField(max_length=15, verbose_name='División')
    
    def __str__(self):
        return self.nom_division
    
    class Meta:
        verbose_name='Division'
        verbose_name_plural='Divisiones'
        ordering=['nom_division']
        db_table='Divisiones'
        

class turno(models.Model):
    nom_turno=models.CharField(max_length=15, verbose_name='Turnos')
    
    def __str__(self):
        return self.nom_turno
    
    class Meta:
        verbose_name='Turno'
        verbose_name_plural='Turnos'
        ordering=['nom_turno']
        db_table='Turnos'


class TipoOperativo(models.Model):
    toperativo=models.CharField(max_length=255,verbose_name='Tipo Operativo')
    
    def __str__(self):
        return self.toperativo
    
    class Meta:
        verbose_name='Operativo'
        verbose_name_plural='Operativos'
        db_table='Tipo_Operativo'
    
class RegDocporSeccion(models.Model):
    dni_docen=models.CharField(max_length=9, verbose_name='DNI')
    apellido_docen=models.CharField(max_length=255, verbose_name='Apellido')
    nombres_docen=models.CharField(max_length=255, verbose_name='Nombres')
    cueanexo=models.CharField(max_length=9, verbose_name='Cueanexo')
    curso=models.ForeignKey(curso,on_delete=models.CASCADE, verbose_name='Curso')
    division=models.ForeignKey(division,on_delete=models.CASCADE, verbose_name='División')
    turno=models.ForeignKey(turno,on_delete=models.CASCADE,verbose_name='Turno')    
    operativos=models.ForeignKey(TipoOperativo, on_delete=models.CASCADE, verbose_name='Operativo')
    validacion=models.BooleanField(default=False, verbose_name='Validación')
    
    class Meta:
        verbose_name='Docente_Aplicador'
        verbose_name_plural='Docentes_Aplicadores'
        ordering=['apellido_docen','nombres_docen']
        db_table='Docente_Aplicador'
    
    def __str__(self):
        return f"{self.apellido_docen} - {self.nombres_docen}"        

        
    """ def save(self, *args, **kwargs):
        if not self.pk:  # Solo cargar los datos automáticamente cuando se crea el objeto
            user = kwargs.pop('user', None)
            if user:
                self.dni_docen = user.username
                self.apellido_docen = user.apellido
                self.nombres_docen = user.nombres
        super(RegDocporSeccion, self).save(*args, **kwargs) """

class Periodos(models.Model):
    periodo=models.CharField(max_length=255, verbose_name='Periodos')
    
    def __str__(self):
        return self.periodo
    
    class Meta:
        verbose_name='Periodo'
        verbose_name_plural='Periodos'
        db_table='Periodos'


class RegEvaluacionFluidezLectora(models.Model):
    asistencia=models.BooleanField(default=False, verbose_name='Asistencia')
    cueanexo=models.CharField(max_length=9, blank=False, null=False, verbose_name='Cueanexo')
    region=models.CharField(max_length=255, blank=False, null=False, verbose_name='Regional')
    grado=models.CharField(max_length=25, blank=False, null=False, verbose_name='Curso')
    seccion=models.CharField(max_length=25, blank=False, null=False, verbose_name='División')
    tramo=models.ForeignKey(Periodos,on_delete=models.CASCADE, verbose_name='Tramo')
    dni_alumno=models.CharField(max_length=8, blank=False, null=False, verbose_name='DNI')
    apellido_alumno=models.CharField(max_length=255, blank=False, null=False, verbose_name='Apellido')
    nombres_alumno=models.CharField(max_length=255, blank=False, null=False, verbose_name='Nombres')
    velocidad=models.PositiveSmallIntegerField(validators=[MinValueValidator(0), MaxValueValidator(150)], verbose_name='Velocidad')
    cal_vel=models.CharField(max_length=255, verbose_name='Calificación Velocidad')
    precision=models.PositiveSmallIntegerField(validators=[MinValueValidator(0), MaxValueValidator(150)], verbose_name='Precisión')
    cal_pres=models.CharField(max_length=255, verbose_name='Calificación Precisión')
    prosodia=models.PositiveSmallIntegerField(validators=[MinValueValidator(0), MaxValueValidator(6)], verbose_name='Prosodia')
    cal_pros=models.CharField(max_length=255, verbose_name='Calificación Prosodia')
    comprension=models.PositiveSmallIntegerField(validators=[MinValueValidator(0), MaxValueValidator(5)], verbose_name='Comprensión')
    cal_comp=models.CharField(max_length=255, verbose_name='Calificación Comprensión')
    
    
    def __str__(self):
        return f"{self.cueanexo} - {self.dni_alumno}: {self.apellido_alumno}, {self.nombres_alumno}"
    
    class Meta:
        verbose_name='Evaluacion_Lectora'
        verbose_name_plural='Evaluaciones_Lectoras'
        ordering=['cueanexo']
        db_table='Evaluacion_Lectora'    
    
    def save(self, *args, **kwargs):
        self.cal_vel = self.get_calificacion_vel(self.velocidad)
        self.cal_pres = self.get_calificacion_pres(self.precision)
        self.cal_pros = self.get_calificacion_pros(self.prosodia)
        self.cal_comp = self.get_calificacion_comp(self.comprension)
        super().save(*args, **kwargs)
    
    def get_calificacion_vel(self, valor):
        if valor < 31:
            return 'Debajo del Básico'
        elif 31 <= valor <=40:
            return 'Básico'
        elif 41 <= valor <=60:
            return 'Satisfactorio'
        elif valor > 60:
            return 'Avanzado'
    
    def get_calificacion_pres(self, valor):
        if valor < 41:
            return 'Debajo del Básico'
        elif 41 <= valor <=47:
            return 'Básico'
        elif 48 <= valor <=60:
            return 'Satisfactorio'
        elif valor > 60:
            return 'Avanzado'
    
    def get_calificacion_pros(self,valor):
        if valor == 1:
            return 'Debajo del Básico'
        elif 2 <= valor <= 4:
            return 'Básico'        
        elif valor == 5:
            return 'Satisfactorio'
        elif valor == 6:
            return 'Avanzado'
    
    def get_calificacion_comp(self,valor):
        if 0 <= valor <= 2:
            return 'Debajo del Básico'        
        elif valor == 3:
            return 'Básico'
        elif valor == 4:
            return 'Satisfactorio'
        elif valor == 5:
            return 'Avanzado'
            


