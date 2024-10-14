import re 
from django.core.exceptions import ValidationError
from django.db import models
from apps.usuarios.models import UsuariosVisualizador
from django.core.validators import MinValueValidator, MaxValueValidator

class curso(models.Model):
    """
    Modelo que representa un curso en el sistema.

    Attributes:
        nom_curso (str): Nombre del curso.
    """
    
    nom_curso=models.CharField(max_length=15, verbose_name='Curso')
    
    def __str__(self):
        return self.nom_curso
    
    class Meta:
        verbose_name='Curso'
        verbose_name_plural='Cursos'
        db_table='Curso'

class division(models.Model):
    """
    Modelo que representa una división en el sistema.

    Attributes:
        nom_division (str): Nombre de la división.
    """
    
    nom_division=models.CharField(max_length=15, verbose_name='División')
    
    def __str__(self):
        return self.nom_division
    
    class Meta:
        verbose_name='Division'
        verbose_name_plural='Divisiones'
        ordering=['nom_division']
        db_table='Divisiones'
        

class turno(models.Model):
    """
    Modelo que representa un turno en el sistema.

    Attributes:
        nom_turno (str): Nombre del turno.
    """
    
    nom_turno=models.CharField(max_length=15, verbose_name='Turnos')
    
    def __str__(self):
        return self.nom_turno
    
    class Meta:
        verbose_name='Turno'
        verbose_name_plural='Turnos'
        ordering=['nom_turno']
        db_table='Turnos'


class TipoOperativo(models.Model):
    """
    Modelo que representa un tipo operativo en el sistema.

    Attributes:
        toperativo (str): Nombre del tipo operativo.
    """
    
    toperativo=models.CharField(max_length=255,verbose_name='Tipo Operativo')
    
    def __str__(self):
        return self.toperativo
    
    class Meta:
        verbose_name='Operativo'
        verbose_name_plural='Operativos'
        db_table='Tipo_Operativo'
    
class RegDocporSeccion(models.Model):
    """
    Modelo que representa la relación entre docentes y secciones.

    Attributes:
        dni_docen (str): DNI del docente.
        apellido_docen (str): Apellido del docente.
        nombres_docen (str): Nombres del docente.
        cueanexo (str): Cueanexo relacionado.
        curso (Curso): Curso al que pertenece el docente.
        division (Division): División al que pertenece el docente.
        turno (Turno): Turno del docente.
        operativos (TipoOperativo): Tipo operativo del docente.
        validacion (bool): Estado de validación del docente.
    """
    
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
    """
    Modelo que representa un periodo en el sistema.

    Attributes:
        periodo (str): Nombre del periodo.
    """
    
    periodo=models.CharField(max_length=255, verbose_name='Periodos')
    
    def __str__(self):
        return self.periodo
    
    class Meta:
        verbose_name='Periodo'
        verbose_name_plural='Periodos'
        db_table='Periodos'


class RegEvaluacionFluidezLectora(models.Model):
    """
    Modelo que representa la evaluación de fluidez lectora de un alumno.

    Attributes:
        asistencia (bool): Estado de asistencia del alumno.
        cueanexo (str): Cueanexo relacionado.
        region (str): Región del alumno.
        grado (str): Grado del alumno.
        seccion (str): Sección del alumno.
        tramo (Periodos): Tramo al que pertenece la evaluación.
        dni_alumno (str): DNI del alumno.
        apellido_alumno (str): Apellido del alumno.
        nombres_alumno (str): Nombres del alumno.
        velocidad (int): Velocidad de lectura del alumno.
        cal_vel (str): Calificación de la velocidad.
        precision (int): Precisión de lectura del alumno.
        cal_pres (str): Calificación de la precisión.
        prosodia (int): Prosodia del alumno.
        cal_pros (str): Calificación de la prosodia.
        comprension (int): Comprensión del alumno.
        cal_comp (str): Calificación de la comprensión.
    """
    
    asistencia=models.BooleanField(default=False, verbose_name='Asistencia')
    cueanexo=models.CharField(max_length=9, blank=False, null=False, verbose_name='Cueanexo')
    region=models.CharField(max_length=255, blank=False, null=False, verbose_name='Regional')
    grado=models.CharField(max_length=25, blank=False, null=False, verbose_name='Curso')
    seccion=models.CharField(max_length=25, blank=False, null=False, verbose_name='División')
    tramo=models.ForeignKey(Periodos,on_delete=models.CASCADE, verbose_name='Tramo')
    dni_alumno=models.CharField(max_length=8, blank=False, null=False, verbose_name='DNI')
    apellido_alumno=models.CharField(max_length=255, blank=False, null=False, verbose_name='Apellido')
    nombres_alumno=models.CharField(max_length=255, blank=False, null=False, verbose_name='Nombres')
    velocidad=models.PositiveSmallIntegerField(validators=[MinValueValidator(0), MaxValueValidator(70)], verbose_name='Velocidad')
    cal_vel=models.CharField(max_length=255, verbose_name='Calificación Velocidad')
    precision=models.PositiveSmallIntegerField(validators=[MinValueValidator(0), MaxValueValidator(70)], verbose_name='Precisión')
    cal_pres=models.CharField(max_length=255, verbose_name='Calificación Precisión')
    prosodia=models.PositiveSmallIntegerField(validators=[MinValueValidator(0), MaxValueValidator(6)], verbose_name='Prosodia')
    cal_pros=models.CharField(max_length=255, verbose_name='Calificación Prosodia')
    comprension=models.PositiveSmallIntegerField(validators=[MinValueValidator(0), MaxValueValidator(6)], verbose_name='Comprensión')
    cal_comp=models.CharField(max_length=255, verbose_name='Calificación Comprensión')
    
    
    def __str__(self):
        return f"{self.cueanexo} - {self.dni_alumno}: {self.apellido_alumno}, {self.nombres_alumno}"
    
    class Meta:
        verbose_name='Evaluacion_Lectora'
        verbose_name_plural='Evaluaciones_Lectoras'
        ordering=['cueanexo']
        db_table='Evaluacion_Lectora'    
    
    def save(self, *args, **kwargs):
        """
        Guarda la instancia del modelo después de calcular las calificaciones.

        Args:
            *args: Positional arguments.
            **kwargs: Keyword arguments.
        """
        
        self.cal_vel = self.get_calificacion_vel(self.velocidad)
        self.cal_pres = self.get_calificacion_pres(self.precision)
        self.cal_pros = self.get_calificacion_pros(self.prosodia)
        self.cal_comp = self.get_calificacion_comp(self.comprension)
        super().save(*args, **kwargs)
    
    def get_calificacion_vel(self, valor):
        """
        Obtiene la calificación para la velocidad de lectura.

        Args:
            valor (int): Valor de velocidad.

        Returns:
            str: Calificación correspondiente a la velocidad.
        """
        
        if valor < 31:
            return 'Debajo del Básico'
        elif 31 <= valor <=50:
            return 'Básico'
        elif 51 <= valor <=60:
            return 'Satisfactorio'
        elif valor > 60:
            return 'Avanzado'
    
    def get_calificacion_pres(self, valor):
        """
        Obtiene la calificación para la precisión de lectura.

        Args:
            valor (int): Valor de precisión.

        Returns:
            str: Calificación correspondiente a la precisión.
        """
        
        if valor < 41:
            return 'Debajo del Básico'
        elif 41 <= valor <=50:
            return 'Básico'
        elif 51 <= valor <=60:
            return 'Satisfactorio'
        elif valor > 60:
            return 'Avanzado'
    
    def get_calificacion_pros(self,valor):
        """
        Obtiene la calificación para la prosodia.

        Args:
            valor (int): Valor de prosodia.

        Returns:
            str: Calificación correspondiente a la prosodia.
        """
        
        if valor == 1 or valor == 2:
            return 'Debajo del Básico'
        elif valor == 3 or valor == 4:
            return 'Básico'        
        elif valor == 5:
            return 'Satisfactorio'
        elif valor == 6:
            return 'Avanzado'
    
    def get_calificacion_comp(self,valor):
        """
        Obtiene la calificación para la comprensión.

        Args:
            valor (int): Valor de comprensión.

        Returns:
            str: Calificación correspondiente a la comprensión.
        """
        
        if valor == 0 or valor == 1:
            return 'Debajo del Básico'        
        elif valor == 2:
            return 'Básico'
        elif 2 >= valor <= 5:
            return 'Satisfactorio'
        elif valor == 6:
            return 'Avanzado'
            


