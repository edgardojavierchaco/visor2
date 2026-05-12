from django.db import models
import uuid

class Establecimientos2026(models.Model):
    #id = models.AutoField(primary_key=True)
    # codigo = models.IntegerField(primary_key=True, db_column='cod_estudiante')
    cueanexo = models.CharField(primary_key=True,max_length=9)
    escuela = models.CharField(max_length=255)
    sector = models.CharField(max_length=255)
    ambito = models.CharField(max_length=255)
    region = models.CharField(max_length=255)
    localidad = models.CharField(max_length=255)
    departamento = models.CharField(max_length=255)
    class Meta:
        #managed = False
        db_table = '"diagnostico_2026"."establecimientos"' 
        #unique_together = ('nombre_año', 'cueanexo')   
    def __str__(self):
        return self.escuela

class Año2026(models.Model):
    OPCIONES_AÑO = [
    # # ('PRIMERO', '1er Grado'),
    ('2do Año', '2do Año'),
    # ('3er Año/Grado', '3er Grado'),
    #cambiamos de SEGUNDO A 2do Año/Grado
    # ('CUARTO', '4to Grado'),
    # ('QUINTO', '5to Grado'),
    # ('SEXTO', '6to Grado'),
    # ('SEPTIMO', '7mo Grado'),
    ]
    #id = models.AutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4,editable=False,unique=True)
    cueanexo = models.CharField(max_length=9)#REPRESENTA A ESCUELA
    nombre_año = models.CharField(max_length=13, choices= OPCIONES_AÑO, default='2do Año')
    titulacion =models.CharField(max_length=15)
    Establecimiento = models.ForeignKey(Establecimientos2026, on_delete=models.CASCADE)
    class Meta:
       #managed = False
        db_table = '"diagnostico_2026"."años"' 
        unique_together = ('nombre_año', 'cueanexo')   
    def __str__(self):
        return self.nombre_año
    
class Seccion2026(models.Model):
    OPCIONES_TURNO = [
    ('MAÑANA', 'Mañana'),
    ('TARDE', 'Tarde'),
    ('NOCTURNO', 'Nocturno'),
    ]
    OPCIONES_SECCION = [
    ('1', '1'),
    ('2', '2'),
    ('3', '3'),
    ('4', '4'),
    ('5', '5'),
    ('6', '6'),
    ('7', '7'),
    ('8', '8'),
    ('9', '9'),
    ('10', '10'),
    ('11', '11'),
    ('12', '12'),
    ('13', '13'),
    ('14', '14'),
    ('15', '15'),
    ('16', '16'),
    ('17', '17'),
    ('18', '18'),
    ('19', '19'),
    ('20', '20'),
    ]
    #id = models.AutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4,editable=False,unique=True)
    seccion = models.CharField(max_length=5, choices=OPCIONES_SECCION)
    turno = models.CharField(max_length=9,choices=OPCIONES_TURNO)
    año = models.ForeignKey(Año2026, on_delete=models.CASCADE)
    class Meta:
        #managed = False
        db_table = '"diagnostico_2026"."secciones"'
        #unicidad
        unique_together = ('seccion','año','turno')
    def __str__(self):
        nombre_seccion=f'{self.año}_{self.seccion}'
        return nombre_seccion

class Alumno2026(models.Model):
    OPCIONES_COMUNIDAD_INDIGENA = [
    ('QOM', 'Qom'),
    ('MOQOIT', 'Moqoit'),
    ('WICHI', 'Wichí'),
    ('NINGUNA', 'Ninguna'),
]
    OPCIONES_DISCAPACIDAD = [
    ('SI', 'Sí, la persona tiene una discapacidad'),
    ('NO', 'Ninguna'),
]
    #id = models.AutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4,editable=False,unique=True)
    dni = models.CharField(max_length=8,unique=True)
    nombre = models.CharField(max_length=50)
    apellido = models.CharField(max_length=50)
    comunidad_indigena=models.CharField(max_length=11, choices= OPCIONES_COMUNIDAD_INDIGENA)
    discapacidad = models.CharField(choices=OPCIONES_DISCAPACIDAD)
    seccion = models.ForeignKey(Seccion2026, on_delete=models.CASCADE)
    class Meta:
        #managed = False
        db_table = '"diagnostico_2026"."alumnos"'
        # unique_together = ('dni','seccion')
    def __str__(self):
        alumno_nombre=f'Alumno:{self.nombre} DNI:{self.dni}'
        return alumno_nombre
    
class EvaluacionDiagnostica2026(models.Model):
    OPCIONES_MODELO = [
    ('A','A'),
    ('B','B'), 
    ]
    OPCIONES_ASISTENCIA = [
    ('PRESENTE','Presente'),
    ('AUSENTE','Ausente'), 
    ]
    #id = models.AutoField(primary_key=True)
    modelo=models.CharField(choices=OPCIONES_MODELO,default='A')
    asistencia = models.CharField(choices=OPCIONES_ASISTENCIA,default='AUSENTE')
    encargado_carga=models.CharField(max_length=9,default='DIRECTOR')
    alumno = models.ForeignKey(Alumno2026, on_delete=models.CASCADE)
    class Meta:
        #managed = False
        db_table = '"diagnostico_2026"."evaluaciones"'
    def __str__(self):
        nombre_examen=f'Evaluacion'
        return nombre_examen
class Matematica2026(EvaluacionDiagnostica2026):
    OPCIONES_RESPUESTAS_1 = [
    ('6,5', '6,5'),
    ('3,25', '3,25'),
    ('0', '0'),  
	]
    OPCIONES_RESPUESTAS_2 = [
    ('6', '6'),
    ('4', '4'),
    ('2', '2'),  
    ('0', '0'),
	]
    OPCIONES_RESPUESTAS_3 = [
    ('A', 'A'),
    ('B', 'B'),
    ('C', 'C'),  
    ('OMITÍO', 'OMITÍO'),
	]
    OPCIONES_RESPUESTAS_4 = [
    ('6', '6'),
    ('3', '3'),
    ('0', '0'),  
	]
    OPCIONES_RESPUESTAS_5 = [
    ('7', '7'),
    ('3,5', '3,5'),
    ('0', '0'),  
	]
    OPCIONES_RESPUESTAS_6 = [
    ('8', '8'),
    ('4', '4'),
    ('0', '0'),  
	]
    OPCIONES_RESPUESTAS_7 = [
    ('10', '10'),
    ('5', '5'),
    ('0', '0'),  
	]
    OPCIONES_RESPUESTAS_8 = [
    ('A', 'A'),
    ('B', 'B'),
    ('C', 'C'),
    ('OMITÍO', 'OMITÍO'),
	]
    OPCIONES_RESPUESTAS_9 = [
    ('11', '11'),
    ('5,50', '5,50'),
    ('0', '0'),  
	]
    OPCIONES_RESPUESTAS_10 = [
    ('A', 'A'),
    ('B', 'B'),
    ('C', 'C'),  
    ('OMITÍO', 'OMITÍO'),
	]
    OPCIONES_RESPUESTAS_11 = [
    ('11,5', '11,5'),
    ('7', '7'),
    ('3,5', '3,5'),
    ('0', '0'),  
	]
    OPCIONES_RESPUESTAS_12 = [
    ('9', '9'),
    ('4,5', '4,5'),
    ('0', '0'),  
	]
    # OPCIONES_ASISTENCIA = [
    # ('PRESENTE','Presente'),
    # ('AUSENTE','Ausente'), 
    # ]
    #cantidad_palabras_leidas = models.IntegerField(default=0, null=True)
    pregunta_2 = models.CharField(max_length=10,choices= OPCIONES_RESPUESTAS_2, null=True)
    pregunta_1 = models.CharField(max_length=10,choices= OPCIONES_RESPUESTAS_1, null=True)
    pregunta_3 = models.CharField(max_length=10,choices= OPCIONES_RESPUESTAS_3, null=True)
    pregunta_4 = models.CharField(max_length=10,choices= OPCIONES_RESPUESTAS_4, null=True)
    pregunta_5 = models.CharField(max_length=10,choices= OPCIONES_RESPUESTAS_5, null=True)
    pregunta_6 = models.CharField(max_length=10,choices= OPCIONES_RESPUESTAS_6, null=True)
    pregunta_7 = models.CharField(max_length=10,choices= OPCIONES_RESPUESTAS_7, null=True)
    pregunta_8 = models.CharField(max_length=10,choices= OPCIONES_RESPUESTAS_8, null=True)
    pregunta_9 = models.CharField(max_length=10,choices= OPCIONES_RESPUESTAS_9, null=True)
    pregunta_10 = models.CharField(max_length=10,choices= OPCIONES_RESPUESTAS_10, null=True)
    pregunta_11 = models.CharField(max_length=10,choices= OPCIONES_RESPUESTAS_11, null=True)
    pregunta_12 = models.CharField(max_length=10,choices= OPCIONES_RESPUESTAS_12, null=True)
    #asistencia = models.CharField(choices=OPCIONES_ASISTENCIA,default='AUSENTE')
    #alumno = models.OneToOneField(Alumno,primary_key=True, on_delete=models.CASCADE)
    class Meta:
        #managed = False
        db_table = '"diagnostico_2026"."evaluaciones_matematica"'
    def __str__(self):
        nombre_examen=f'Evaluación Diagnóstica Matemática {self.alumno.nombre} {self.alumno.apellido} DNI:{self.alumno.dni}'
        return nombre_examen
    


class Lengua2026(EvaluacionDiagnostica2026):
    OPCIONES_RESPUESTAS = [
    ('A', 'A'),
    ('B', 'B'),
    ('C', 'C'),
    ('D', 'D'),
    ('OMITÍO', 'OMITÍO'),
	]
    OPCIONES_RESULTADOS_11_1 = [
    ('2', '2'),
    ('0', '0'),
	]
    OPCIONES_RESULTADOS_11_2 = [
    ('5,65', '5,65'),
    ('2,80', '2,80'),
    ('0', '0'),
	]
    OPCIONES_RESULTADOS_11_3 = [
    ('2,30', '2,30'),
    ('1,15', '1,15'),
    ('0', '0'),
	]
    OPCIONES_RESULTADOS_11_4 = [
    ('2,30', '2,30'),
    ('1,15', '1,15'),
    ('0', '0'),
	]
    OPCIONES_RESULTADOS_22_1 = [
    ('7,65', '7,65'),
    ('3,80', '3,80'), 
    ('0', '0'),
	]
    OPCIONES_RESULTADOS_22_2 = [
    ('2,30', '2,30'),
    ('1,15', '1,15'),
    ('0', '0'),
	]
    OPCIONES_RESULTADOS_22_3 = [
    ('2,30', '2,30'),
    ('1,15', '1,15'),
    ('0', '0'),
	]
    #cantidad_palabras_leidas = models.IntegerField(default=0, null=True)
    pregunta_1 = models.CharField(max_length=10,choices= OPCIONES_RESPUESTAS, blank=True,null=True)
    pregunta_2 = models.CharField(max_length=10,choices= OPCIONES_RESPUESTAS, null=True)
    pregunta_3 = models.CharField(max_length=10,choices= OPCIONES_RESPUESTAS, null=True)
    pregunta_4 = models.CharField(max_length=10,choices= OPCIONES_RESPUESTAS, null=True)
    pregunta_5 = models.CharField(max_length=10,choices= OPCIONES_RESPUESTAS, null=True)
    pregunta_6 = models.CharField(max_length=10,choices= OPCIONES_RESPUESTAS, null=True)
    pregunta_7 = models.CharField(max_length=10,choices= OPCIONES_RESPUESTAS, null=True)
    pregunta_8 = models.CharField(max_length=10,choices= OPCIONES_RESPUESTAS, null=True)
    pregunta_9 = models.CharField(max_length=10,choices= OPCIONES_RESPUESTAS, null=True)
    pregunta_10 = models.CharField(max_length=10,choices= OPCIONES_RESPUESTAS, null=True)
    pregunta_11_1 = models.CharField(max_length=10,choices= OPCIONES_RESULTADOS_11_1, null=True)
    pregunta_11_2 = models.CharField(max_length=10,choices= OPCIONES_RESULTADOS_11_2, null=True)
    pregunta_11_3 = models.CharField(max_length=10,choices= OPCIONES_RESULTADOS_11_3, null=True)
    pregunta_11_4 = models.CharField(max_length=10,choices= OPCIONES_RESULTADOS_11_4, null=True)
    pregunta_12 = models.CharField(max_length=10,choices= OPCIONES_RESPUESTAS, null=True)
    pregunta_13 = models.CharField(max_length=10,choices= OPCIONES_RESPUESTAS, null=True)
    pregunta_14 = models.CharField(max_length=10,choices= OPCIONES_RESPUESTAS, null=True)
    pregunta_15 = models.CharField(max_length=10,choices= OPCIONES_RESPUESTAS, null=True)
    pregunta_16 = models.CharField(max_length=10,choices= OPCIONES_RESPUESTAS, null=True)
    pregunta_17 = models.CharField(max_length=10,choices= OPCIONES_RESPUESTAS, null=True)
    pregunta_18 = models.CharField(max_length=10,choices= OPCIONES_RESPUESTAS, null=True)
    pregunta_19= models.CharField(max_length=10,choices= OPCIONES_RESPUESTAS, null=True)
    pregunta_20 = models.CharField(max_length=10,choices= OPCIONES_RESPUESTAS, null=True)
    pregunta_21= models.CharField(max_length=10,choices= OPCIONES_RESPUESTAS, null=True)
    pregunta_22_1 = models.CharField(max_length=10,choices= OPCIONES_RESULTADOS_22_1, null=True)
    pregunta_22_2 = models.CharField(max_length=10,choices= OPCIONES_RESULTADOS_22_2, null=True)
    pregunta_22_3 = models.CharField(max_length=10,choices= OPCIONES_RESULTADOS_22_3, null=True)
    #asistencia = models.CharField(choices=OPCIONES_ASISTENCIA,default='AUSENTE')
    #alumno = models.OneToOneField(Alumno,primary_key=True, on_delete=models.CASCADE)
    class Meta:
        #managed = False
        db_table = '"diagnostico_2026"."evaluaciones_lengua"'
    def __str__(self):
        nombre_examen=f'Evaluación Diagnóstica Lengua {self.alumno.nombre} {self.alumno.apellido} DNI:{self.alumno.dni}'
        return nombre_examen