from pyexpat import model
from django.db import models
from decimal import Decimal
from django.core.validators import MinValueValidator, MaxValueValidator


class AlumnosSecundariaDiagnostico(models.Model):
    dni = models.CharField(max_length=8, unique=True, verbose_name='DNI')  
    apellidos = models.CharField(max_length=255, verbose_name='Apellidos')
    nombres = models.CharField(max_length=255, verbose_name='Nombres')
    cueanexo = models.CharField(max_length=9, verbose_name='Cueanexo') 
    anio=models.CharField(max_length=25, verbose_name='Año')
    division=models.CharField(max_length=5, verbose_name='División')
    region=models.CharField(max_length=25, verbose_name='Regional')

    class Meta:
        verbose_name = "Alumno Secundaria Diagnostico"
        verbose_name_plural = "Alumnos Secundaria Diagnosticos"
        db_table = "Alumno_Secundaria_Diagnostico"

    def __str__(self):
        return f'{self.dni} {self.apellidos} {self.nombres}'   



class ConceptosLengua(models.Model):
    pregunta=models.IntegerField(verbose_name='Pregunta')
    capacidad=models.CharField(max_length=50, verbose_name='Capacidad')
    contenido=models.CharField(max_length=150, verbose_name='Contenido')
    puntaje_max=models.DecimalField(max_digits=4, decimal_places=2, verbose_name='Puntaje Maximo')
    cod=models.CharField(max_length=3, verbose_name='Codigo')
     
    class Meta:
        verbose_name = "Concepto Lengua"
        verbose_name_plural = "Conceptos Lengua"
        db_table = "Concepto_Lengua"

    def __str__(self):
        return f'{self.pregunta} {self.puntaje_max}'
    

class ConceptosMatematica(models.Model):
    pregunta=models.IntegerField(verbose_name='Pregunta')
    capacidad=models.CharField(max_length=50, verbose_name='Capacidad')
    contenido=models.CharField(max_length=150, verbose_name='Contenido')
    eje=models.CharField(max_length=50, verbose_name='Eje')
    puntaje_max=models.DecimalField(max_digits=4, decimal_places=2, verbose_name='Puntaje Maximo')
    cod=models.CharField(max_length=3, verbose_name='Codigo')
     
    class Meta:
        verbose_name = "Concepto Matematica"
        verbose_name_plural = "Conceptos Matematica"
        db_table = "Concepto_Matematica"

    def __str__(self):
        return f'{self.pregunta} {self.puntaje_max}'


class ExamenLenguaAlumno(models.Model):    

    PREG1_CHOICES = [
        (Decimal('0.00'), '0.00'),
        (Decimal('7.00'), '7.00'),
    ]
    
    PREG2_CHOICES = [
        (Decimal('0.00'), '0.00'),
        (Decimal('4.00'), '4.00'),
    ]
    
    PREG3_CHOICES = [
        (Decimal('0.00'), '0.00'),
        (Decimal('6.00'), '6.00'),
    ]
    PREG4_CHOICES = [
        (Decimal('0.00'), '0.00'),
        (Decimal('5.00'), '5.00'),
    ]
    
    DISCAPACIDAD=[
        ('SI', 'SI'),
        ('NO', 'NO'),
    ]
    
    ETNIA=[
        ('NO', 'NO'),
        ('QOM', 'QOM'),
        ('WICHI', 'WICHI'),
        ('MOQOIT', 'MOQOIT'),
    ]
    
    dni = models.CharField(max_length=8, verbose_name='DNI')  
    apellidos = models.CharField(max_length=255, verbose_name='Apellidos')
    nombres = models.CharField(max_length=255, verbose_name='Nombres')
    cueanexo = models.CharField(max_length=9, verbose_name='Cueanexo') 
    anio=models.CharField(max_length=25, verbose_name='Año')
    division=models.CharField(max_length=5, verbose_name='División')
    region=models.CharField(max_length=25, verbose_name='Regional')
    discapacidad=models.CharField(max_length=2, choices=DISCAPACIDAD,verbose_name='Discapacidad')
    etnia=models.CharField(max_length=10, choices=ETNIA,verbose_name='Etnia')
    p1 = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        choices=PREG1_CHOICES,
        verbose_name='Item 1'
    )
    p2 = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        choices=PREG1_CHOICES,
        verbose_name='Item 2'
    )
    p3 = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        choices=PREG2_CHOICES,
        verbose_name='Item 3'
    )
    p4 = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        choices=PREG3_CHOICES,
        verbose_name='Item 4'
    )
    p5 = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        choices=PREG1_CHOICES,
        verbose_name='Item 5'
    )
    p6 = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        choices=PREG1_CHOICES,
        verbose_name='Item 6'
    )
    p7 = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        choices=PREG2_CHOICES,
        verbose_name='Item 7'
    )
    p8 = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        verbose_name='Item 8',
        validators=[
            MinValueValidator(0.00),
            MaxValueValidator(12.50)
        ]
    )
    p9 = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        choices=PREG3_CHOICES,
        verbose_name='Item 9'
    )
    p10 = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        choices=PREG3_CHOICES,
        verbose_name='Item 10'
    )
    p11 = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        choices=PREG2_CHOICES,
        verbose_name='Item 11'
    )
    p12 = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        choices=PREG2_CHOICES,
        verbose_name='Item 12'
    )
    p13 = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        choices=PREG2_CHOICES,
        verbose_name='Item 13'
    )
    p14 = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        choices=PREG4_CHOICES,
        verbose_name='Item 14'
    )
    p15 = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        choices=PREG2_CHOICES,
        verbose_name='Item 15'
    )
    p16 = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        verbose_name='Item 16',
        validators=[
            MinValueValidator(0.00),
            MaxValueValidator(12.50)
        ]
    )        

    class Meta:
        verbose_name = "Examen Lengua Alumno"
        verbose_name_plural = "Examen Lengua Alumnos"
        db_table = "Examen_Lengua_Alumnos"

    def __str__(self):
        return f'{self.dni} {self.apellidos} {self.nombres}'


class ExamenMatematicaAlumno(models.Model):    

    PREG1_CHOICES = [
        (Decimal('0.00'), '0.00'),
        (Decimal('3.00'), '3.00'),
        (Decimal('10.00'), '10.00'),
    ]
    
    PREG2_CHOICES = [
        (Decimal('0.00'), '0.00'),
        (Decimal('4.00'), '4.00'),
    ]
    
    PREG3_CHOICES = [
        (Decimal('0.00'), '0.00'),
        (Decimal('2.00'), '2.00'),
    ]
    PREG4_CHOICES = [
        (Decimal('0.00'), '0.00'),
        (Decimal('5.00'), '5.00'),
        (Decimal('10.00'), '10.00'),
        (Decimal('15.00'), '15.00'),
    ]
    PREG5_CHOICES = [
        (Decimal('0.00'), '0.00'),
        (Decimal('4.00'), '4.00'),
        (Decimal('7.00'), '7.00'),
        (Decimal('10.00'), '10.00'),
    ]
    PREG6_CHOICES = [
        (Decimal('0.00'), '0.00'),
        (Decimal('3.00'), '3.00'),
        (Decimal('6.00'), '6.00'),
        (Decimal('8.00'), '8.00'),
    ]
    PREG7_CHOICES = [
        (Decimal('0.00'), '0.00'),
        (Decimal('6.00'), '6.00'),
    ]
    PREG8_CHOICES = [
        (Decimal('0.00'), '0.00'),
        (Decimal('10.00'), '10.00'),
    ]
    PREG9_CHOICES = [
        (Decimal('0.00'), '0.00'),
        (Decimal('5.00'), '5.00'),
        (Decimal('10.00'), '10.00'),
    ]
    PREG10_CHOICES = [
        (Decimal('0.00'), '0.00'),
        (Decimal('7.00'), '7.00'),
    ]
    PREG11_CHOICES = [
        (Decimal('0.00'), '0.00'),
        (Decimal('4.00'), '4.00'),
    ]
    PREG12_CHOICES = [
        (Decimal('0.00'), '0.00'),
        (Decimal('2.00'), '2.00'),
        (Decimal('4.00'), '4.00'),
        (Decimal('5.00'), '5.00'),
    ]
    PREG13_CHOICES = [
        (Decimal('0.00'), '0.00'),
        (Decimal('4.00'), '4.00'),
    ]
    PREG14_CHOICES = [
        (Decimal('0.00'), '0.00'),
        (Decimal('5.00'), '5.00'),
    ]
    
    DISCAPACIDAD=[
        ('SI', 'SI'),  
        ('NO', 'NO'),
    ]
    
    ETNIA=[
        ('NO', 'NO'),
        ('QOM', 'QOM'),
        ('WICHI', 'WICHI'),
        ('MOQOIT', 'MOQOIT'),
    ]
        
    dni = models.CharField(max_length=8, verbose_name='DNI')  
    apellidos = models.CharField(max_length=255, verbose_name='Apellidos')
    nombres = models.CharField(max_length=255, verbose_name='Nombres')
    cueanexo = models.CharField(max_length=9, verbose_name='Cueanexo') 
    anio=models.CharField(max_length=25, verbose_name='Año')
    division=models.CharField(max_length=5, verbose_name='División')
    region=models.CharField(max_length=25, verbose_name='Regional')
    discapacidad=models.CharField(max_length=2, choices=DISCAPACIDAD,verbose_name='Discapacidad')
    etnia=models.CharField(max_length=10, choices=ETNIA,verbose_name='Etnia')
    p1 = models.DecimalField(     
        max_digits=4,
        decimal_places=2,
        choices=PREG1_CHOICES,
        verbose_name='Item 1'
    )
    p2 = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        choices=PREG2_CHOICES,
        verbose_name='Item 2'
    )
    p3 = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        choices=PREG3_CHOICES,
        verbose_name='Item 3'
    )
    p4 = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        choices=PREG4_CHOICES,
        verbose_name='Item 4'
    )
    p5 = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        choices=PREG5_CHOICES,
        verbose_name='Item 5'
    )
    p6 = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        choices=PREG6_CHOICES,
        verbose_name='Item 6'
    )
    p7 = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        choices=PREG7_CHOICES,
        verbose_name='Item 7'
    )
    p8 = models.DecimalField(
        max_digits=4,
        decimal_places=2,        
        choices=PREG8_CHOICES,
        verbose_name='Item 8'
    )
    p9 = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        choices=PREG9_CHOICES,
        verbose_name='Item 9'
    )
    p10 = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        choices=PREG10_CHOICES,
        verbose_name='Item 10'
    )
    p11 = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        choices=PREG11_CHOICES,
        verbose_name='Item 11'
    )
    p12 = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        choices=PREG12_CHOICES,
        verbose_name='Item 12'
    )
    p13 = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        choices=PREG13_CHOICES,
        verbose_name='Item 13'
    )
    p14 = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        choices=PREG14_CHOICES,
        verbose_name='Item 14'
    )    

    class Meta:
        verbose_name = "Examen Matematica Alumno"
        verbose_name_plural = "Examen Matematica Alumnos"
        db_table = "Examen_Matematica_Alumnos"

    def __str__(self):
        return f'{self.dni} {self.apellidos} {self.nombres}'


class RegistroAsistenciaLengua(models.Model):
    cueanexo = models.CharField(max_length=15)
    fecha = models.DateTimeField(auto_now_add=True)
    region=models.CharField(max_length=25)
    ausentes = models.PositiveIntegerField()
    total_registros = models.PositiveIntegerField()
    
    class Meta:
        verbose_name = "Registro Asistencia Lengua"
        verbose_name_plural = "Registros Asistencia Lengua"
        db_table = "Registro_Asistencia_Lengua"


    def __str__(self):
        return f"{self.cueanexo} - {self.fecha.strftime('%d/%m/%Y')}"
    
    
class RegistroAsistenciaMatematica(models.Model):
    cueanexo = models.CharField(max_length=15)
    fecha = models.DateTimeField(auto_now_add=True)
    region=models.CharField(max_length=25)
    ausentes = models.PositiveIntegerField()
    total_registros = models.PositiveIntegerField()
    
    class Meta:
        verbose_name = "Registro Asistencia Matematica"
        verbose_name_plural = "Registros Asistencia Matematica"
        db_table = "Registro_Asistencia_Matematica"


    def __str__(self):
        return f"{self.cueanexo} - {self.fecha.strftime('%d/%m/%Y')}"


class TotalSecundarias(models.Model):
    total_escuelas=models.PositiveIntegerField(verbose_name='Total')
    estatal=models.PositiveIntegerField(verbose_name='Estatal')
    privado=models.PositiveIntegerField(verbose_name='Privada')
    gestion_social=models.PositiveIntegerField(verbose_name='Gestion Social')
    urbano=models.PositiveIntegerField(verbose_name='Urbano')
    rural_disperso=models.PositiveIntegerField(verbose_name='Rural_Disperso')
    rural_aglomerado=models.PositiveIntegerField(verbose_name='Rural_Aglomerado')
    
    class Meta:
        managed=False
        verbose_name = "Total Secundaria"
        verbose_name_plural = "Total Secundarias"
        db_table = "total_secundarias"
    
    def __str__(self):
        return f'{self.total_escuelas} {self.estatal} {self.privado} {self.gestion_social} {self.urbano} {self.rural_disperso} {self.rural_aglomerado}'
    

class EscuelasSecundarias(models.Model):
    id = models.AutoField(primary_key=True)
    cueanexo = models.CharField(max_length=9, verbose_name='Cueanexo')
    nom_est=models.CharField(max_length=255, verbose_name='Nombre')
    oferta=models.CharField(max_length=255, verbose_name='Oferta')
    region_loc=models.CharField(max_length=255, verbose_name='Region')
    sector=models.CharField(max_length=255, verbose_name='Sector')
    ambito=models.CharField(max_length=255, verbose_name='Ambito')
    localidad=models.CharField(max_length=255, verbose_name='Localidad')
    departamento=models.CharField(max_length=255, verbose_name='Departamento')
    lengua=models.CharField(max_length=255, default='PENDIENTE',verbose_name='Lengua')
    matematica=models.CharField(max_length=255, default='PENDIENTE',verbose_name='Matematica')
    
    class Meta:        
        verbose_name = "Escuela Secundaria"
        verbose_name_plural = "Escuelas Secundarias"
        db_table = "escuelas_secundarias"
    
    def __str__(self):
        return f'{self.cueanexo} {self.nom_est}'


class CorteGeneralLengua(models.Model):
    nivel_desempeño=models.CharField(max_length=50, verbose_name='Nivel Desempeño')
    punto_corte=models.DecimalField(max_digits=4, decimal_places=2, verbose_name='Punto Corte')
    
    class Meta:
        verbose_name = "Corte General Lengua"
        verbose_name_plural = "Cortes Generales Lengua"
        db_table = "corte_general_lengua"
        
    def __str__(self):
        return f'{self.nivel_desempeño} {self.punto_corte}'


class CorteInterpretarLengua(models.Model):
    nivel_desempeño=models.CharField(max_length=50, verbose_name='Nivel Desempeño')
    punto_corte=models.DecimalField(max_digits=4, decimal_places=2, verbose_name='Punto Corte')
    
    class Meta:
        verbose_name = "Corte Interpretar Lengua"
        verbose_name_plural = "Cortes Interpretar Lengua"
        db_table = "corte_interpretar_lengua"
        
    def __str__(self):
        return f'{self.nivel_desempeño} {self.punto_corte}'
    

class CorteEvaluarLengua(models.Model):
    nivel_desempeño=models.CharField(max_length=50, verbose_name='Nivel Desempeño')
    punto_corte=models.DecimalField(max_digits=4, decimal_places=2, verbose_name='Punto Corte')
    
    class Meta:
        verbose_name = "Corte Evaluar Lengua"
        verbose_name_plural = "Cortes Evaluar Lengua"
        db_table = "corte_evaluar_lengua"
        
    def __str__(self):
        return f'{self.nivel_desempeño} {self.punto_corte}'


class CorteExtraerLengua(models.Model):
    nivel_desempeño=models.CharField(max_length=50, verbose_name='Nivel Desempeño')
    punto_corte=models.DecimalField(max_digits=4, decimal_places=2, verbose_name='Punto Corte')
    
    class Meta:
        verbose_name = "Corte Extraer Lengua"
        verbose_name_plural = "Cortes Extraer Lengua"
        db_table = "corte_extraer_lengua"
        
    def __str__(self):
        return f'{self.nivel_desempeño} {self.punto_corte}'

class CorteEscrituraLengua(models.Model):
    nivel_desempeño=models.CharField(max_length=50, verbose_name='Nivel Desempeño')
    punto_corte=models.DecimalField(max_digits=4, decimal_places=2, verbose_name='Punto Corte')
    
    class Meta:
        verbose_name = "Corte Escritura Lengua"
        verbose_name_plural = "Cortes Escritura Lengua"
        db_table = "corte_escritura_lengua"
        
    def __str__(self):
        return f'{self.nivel_desempeño} {self.punto_corte}'


class CorteGeneralMatematica(models.Model):
    nivel_desempeño=models.CharField(max_length=50, verbose_name='Nivel Desempeño')
    punto_corte=models.DecimalField(max_digits=4, decimal_places=2, verbose_name='Punto Corte')
    
    class Meta:
        verbose_name = "Corte General Matematica"
        verbose_name_plural = "Cortes Generales Matematica"
        db_table = "corte_general_matematica"
        
    def __str__(self):
        return f'{self.nivel_desempeño} {self.punto_corte}'


class CorteReconocimientoMatematica(models.Model):
    nivel_desempeño=models.CharField(max_length=50, verbose_name='Nivel Desempeño')
    punto_corte=models.DecimalField(max_digits=4, decimal_places=2, verbose_name='Punto Corte')
    
    class Meta:
        verbose_name = "Corte Reconocimiento Matematica"
        verbose_name_plural = "Cortes Reconocimiento Matematica"
        db_table = "corte_reconocimiento_matematica"
        
    def __str__(self):
        return f'{self.nivel_desempeño} {self.punto_corte}'


class CorteComunicacionMatematica(models.Model):
    nivel_desempeño=models.CharField(max_length=50, verbose_name='Nivel Desempeño')
    punto_corte=models.DecimalField(max_digits=4, decimal_places=2, verbose_name='Punto Corte')
    
    class Meta:
        verbose_name = "Corte Comunicacion Matematica"
        verbose_name_plural = "Cortes Comunicacion Matematica"
        db_table = "corte_comunicacion_matematica"
        
    def __str__(self):
        return f'{self.nivel_desempeño} {self.punto_corte}'
    

class CorteResolucionMatematica(models.Model):
    nivel_desempeño=models.CharField(max_length=50, verbose_name='Nivel Desempeño')
    punto_corte=models.DecimalField(max_digits=4, decimal_places=2, verbose_name='Punto Corte')
    
    class Meta:
        verbose_name = "Corte Resolucion Matematica"
        verbose_name_plural = "Cortes Resolucion Matematica"
        db_table = "corte_resolucion_matematica"
        
    def __str__(self):
        return f'{self.nivel_desempeño} {self.punto_corte}'


class VistaGeneralLengua(models.Model):
    cueanexo=models.CharField(max_length=9, verbose_name='Cueanexo')
    nivel=models.CharField(max_length=50, verbose_name='Nivel')
    cantidad=models.PositiveIntegerField(verbose_name='Cantidad')
    porcentaje=models.DecimalField(max_digits=5, decimal_places=2, verbose_name='Porcentaje')
    
    class Meta:
        managed=False
        verbose_name = "Vista General Lengua"
        verbose_name_plural = "Vistas Generales Lengua"
        db_table = "v_gral_lengua"
    
    def __str__(self):
        return f'{self.cueanexo} {self.nivel} {self.cantidad} {self.porcentaje}'


class VistaEvaluarLengua(models.Model):
    cueanexo=models.CharField(max_length=9, verbose_name='Cueanexo')
    nivel=models.CharField(max_length=50, verbose_name='Nivel')
    cantidad=models.PositiveIntegerField(verbose_name='Cantidad')
    porcentaje=models.DecimalField(max_digits=5, decimal_places=2, verbose_name='Porcentaje')
    
    class Meta:
        managed=False
        verbose_name = "Vista Evaluar Lengua"
        verbose_name_plural = "Vistas Evaluar Lengua"
        db_table = "v_evaluar_lengua"
    
    def __str__(self):
        return f'{self.cueanexo} {self.nivel} {self.cantidad} {self.porcentaje}'


class VistaInterpretarLengua(models.Model):
    cueanexo=models.CharField(max_length=9, verbose_name='Cueanexo')
    nivel=models.CharField(max_length=50, verbose_name='Nivel')
    cantidad=models.PositiveIntegerField(verbose_name='Cantidad')
    porcentaje=models.DecimalField(max_digits=5, decimal_places=2, verbose_name='Porcentaje')
    
    class Meta:
        managed=False
        verbose_name = "Vista Interpretar Lengua"
        verbose_name_plural = "Vistas Interpretar Lengua"
        db_table = "v_interpretar_lengua"
        
    def __str__(self):
        return f'{self.cueanexo} {self.nivel} {self.cantidad} {self.porcentaje}'


class VistaExtraerLengua(models.Model):
    cueanexo=models.CharField(max_length=9, verbose_name='Cueanexo')
    nivel=models.CharField(max_length=50, verbose_name='Nivel')
    cantidad=models.PositiveIntegerField(verbose_name='Cantidad')
    porcentaje=models.DecimalField(max_digits=5, decimal_places=2, verbose_name='Porcentaje')
    
    class Meta:
        managed=False
        verbose_name = "Vista Extraer Lengua"
        verbose_name_plural = "Vistas Extraer Lengua"
        db_table = "v_extraer_lengua"
        
    def __str__(self):
        return f'{self.cueanexo} {self.nivel} {self.cantidad} {self.porcentaje}'


class VistaEscrituraLengua(models.Model):
    cueanexo=models.CharField(max_length=9, verbose_name='Cueanexo')
    nivel=models.CharField(max_length=50, verbose_name='Nivel')
    cantidad=models.PositiveIntegerField(verbose_name='Cantidad')
    porcentaje=models.DecimalField(max_digits=5, decimal_places=2, verbose_name='Porcentaje')
    
    class Meta:
        managed=False
        verbose_name = "Vista Escritura Lengua"
        verbose_name_plural = "Vistas Escritura Lengua"
        db_table = "v_escritura_lengua"
        
    def __str__(self):
        return f'{self.cueanexo} {self.nivel} {self.cantidad} {self.porcentaje}'



class VistaGeneralMatematica(models.Model):
    cueanexo=models.CharField(max_length=9, verbose_name='Cueanexo')
    nivel=models.CharField(max_length=50, verbose_name='Nivel')
    cantidad=models.PositiveIntegerField(verbose_name='Cantidad')
    porcentaje=models.DecimalField(max_digits=5, decimal_places=2, verbose_name='Porcentaje')
    
    class Meta:
        managed=False
        verbose_name = "Vista General Matematica"
        verbose_name_plural = "Vistas Generales Matematica"
        db_table = "v_gral_matematica"
    
    def __str__(self):
        return f'{self.cueanexo} {self.nivel} {self.cantidad} {self.porcentaje}'

class VistaReconocimientoMatematica(models.Model):
    cueanexo=models.CharField(max_length=9, verbose_name='Cueanexo')
    nivel=models.CharField(max_length=50, verbose_name='Nivel')
    cantidad=models.PositiveIntegerField(verbose_name='Cantidad')
    porcentaje=models.DecimalField(max_digits=5, decimal_places=2, verbose_name='Porcentaje')
    
    class Meta:
        managed=False
        verbose_name = "Vista Reconocimiento Matematica"
        verbose_name_plural = "Vistas Reconocimiento Matematica"
        db_table = "v_reconocimiento_matematica"
    
    def __str__(self):
        return f'{self.cueanexo} {self.nivel} {self.cantidad} {self.porcentaje}'

class VistaComunicacionMatematica(models.Model):
    cueanexo=models.CharField(max_length=9, verbose_name='Cueanexo')
    nivel=models.CharField(max_length=50, verbose_name='Nivel')
    cantidad=models.PositiveIntegerField(verbose_name='Cantidad')
    porcentaje=models.DecimalField(max_digits=5, decimal_places=2, verbose_name='Porcentaje')
    
    class Meta:
        managed=False
        verbose_name = "Vista Comunicacion Matematica"
        verbose_name_plural = "Vistas Comunicacion Matematica"
        db_table = "v_comunicacion_matematica"
        
    def __str__(self):
        return f'{self.cueanexo} {self.nivel} {self.cantidad} {self.porcentaje}'

class VistaResolucionMatematica(models.Model):
    cueanexo=models.CharField(max_length=9, verbose_name='Cueanexo')
    nivel=models.CharField(max_length=50, verbose_name='Nivel')
    cantidad=models.PositiveIntegerField(verbose_name='Cantidad')
    porcentaje=models.DecimalField(max_digits=5, decimal_places=2, verbose_name='Porcentaje')
    
    class Meta:
        managed=False
        verbose_name = "Vista Resolucion Matematica"
        verbose_name_plural = "Vistas Resolucion Matematica"
        db_table = "v_resolucion_matematica"
        
    def __str__(self):
        return f'{self.cueanexo} {self.nivel} {self.cantidad} {self.porcentaje}'
    

#####################
# Vistas por region #
#####################

class VistaGeneralLenguaReg(models.Model):
    region=models.CharField(max_length=9, verbose_name='Región')
    nivel=models.CharField(max_length=50, verbose_name='Nivel')
    cantidad=models.PositiveIntegerField(verbose_name='Cantidad')
    porcentaje=models.DecimalField(max_digits=5, decimal_places=2, verbose_name='Porcentaje')
    
    class Meta:
        managed=False
        verbose_name = "Vista General Lengua Region"
        verbose_name_plural = "Vistas Generales Lengua Region"
        db_table = "v_gral_lengua_reg"
    
    def __str__(self):
        return f'{self.region} {self.nivel} {self.cantidad} {self.porcentaje}'


class VistaEvaluarLenguaReg(models.Model):
    region=models.CharField(max_length=9, verbose_name='Región')
    nivel=models.CharField(max_length=50, verbose_name='Nivel')
    cantidad=models.PositiveIntegerField(verbose_name='Cantidad')
    porcentaje=models.DecimalField(max_digits=5, decimal_places=2, verbose_name='Porcentaje')
    
    class Meta:
        managed=False
        verbose_name = "Vista Evaluar Lengua Region"
        verbose_name_plural = "Vistas Evaluar Lengua Region"
        db_table = "v_evaluar_lengua_reg"
    
    def __str__(self):
        return f'{self.region} {self.nivel} {self.cantidad} {self.porcentaje}'


class VistaInterpretarLenguaReg(models.Model):
    region=models.CharField(max_length=9, verbose_name='Región')
    nivel=models.CharField(max_length=50, verbose_name='Nivel')
    cantidad=models.PositiveIntegerField(verbose_name='Cantidad')
    porcentaje=models.DecimalField(max_digits=5, decimal_places=2, verbose_name='Porcentaje')
    
    class Meta:
        managed=False
        verbose_name = "Vista Interpretar Lengua Region"
        verbose_name_plural = "Vistas Interpretar Lengua Region"
        db_table = "v_interpretar_lengua_reg"
        
    def __str__(self):
        return f'{self.region} {self.nivel} {self.cantidad} {self.porcentaje}'


class VistaExtraerLenguaReg(models.Model):
    region=models.CharField(max_length=9, verbose_name='Región')
    nivel=models.CharField(max_length=50, verbose_name='Nivel')
    cantidad=models.PositiveIntegerField(verbose_name='Cantidad')
    porcentaje=models.DecimalField(max_digits=5, decimal_places=2, verbose_name='Porcentaje')
    
    class Meta:
        managed=False
        verbose_name = "Vista Extraer Lengua Region"
        verbose_name_plural = "Vistas Extraer Lengua Region"
        db_table = "v_extraer_lengua_reg"
        
    def __str__(self):
        return f'{self.region} {self.nivel} {self.cantidad} {self.porcentaje}'


class VistaEscrituraLenguaReg(models.Model):
    region=models.CharField(max_length=9, verbose_name='Región')
    nivel=models.CharField(max_length=50, verbose_name='Nivel')
    cantidad=models.PositiveIntegerField(verbose_name='Cantidad')
    porcentaje=models.DecimalField(max_digits=5, decimal_places=2, verbose_name='Porcentaje')
    
    class Meta:
        managed=False
        verbose_name = "Vista Escritura Lengua Region"
        verbose_name_plural = "Vistas Escritura Lengua Region"
        db_table = "v_escritura_lengua_reg"
        
    def __str__(self):
        return f'{self.region} {self.nivel} {self.cantidad} {self.porcentaje}'



class VistaGeneralMatematicaReg(models.Model):
    region=models.CharField(max_length=9, verbose_name='Región')
    nivel=models.CharField(max_length=50, verbose_name='Nivel')
    cantidad=models.PositiveIntegerField(verbose_name='Cantidad')
    porcentaje=models.DecimalField(max_digits=5, decimal_places=2, verbose_name='Porcentaje')
    
    class Meta:
        managed=False
        verbose_name = "Vista General Matematica Region"
        verbose_name_plural = "Vistas Generales Matematica Region"
        db_table = "v_gral_matematica_reg"
    
    def __str__(self):
        return f'{self.region} {self.nivel} {self.cantidad} {self.porcentaje}'

class VistaReconocimientoMatematicaReg(models.Model):
    region=models.CharField(max_length=9, verbose_name='Región')
    nivel=models.CharField(max_length=50, verbose_name='Nivel')
    cantidad=models.PositiveIntegerField(verbose_name='Cantidad')
    porcentaje=models.DecimalField(max_digits=5, decimal_places=2, verbose_name='Porcentaje')
    
    class Meta:
        managed=False
        verbose_name = "Vista Reconocimiento Matematica Region"
        verbose_name_plural = "Vistas Reconocimiento Matematica Region"
        db_table = "v_reconocimiento_matematica_reg"
    
    def __str__(self):
        return f'{self.region} {self.nivel} {self.cantidad} {self.porcentaje}'

class VistaComunicacionMatematicaReg(models.Model):
    region=models.CharField(max_length=9, verbose_name='Región')
    nivel=models.CharField(max_length=50, verbose_name='Nivel')
    cantidad=models.PositiveIntegerField(verbose_name='Cantidad')
    porcentaje=models.DecimalField(max_digits=5, decimal_places=2, verbose_name='Porcentaje')
    
    class Meta:
        managed=False
        verbose_name = "Vista Comunicacion Matematica Region"
        verbose_name_plural = "Vistas Comunicacion Matematica Region"
        db_table = "v_comunicacion_matematica_reg"
        
    def __str__(self):
        return f'{self.region} {self.nivel} {self.cantidad} {self.porcentaje}'

class VistaResolucionMatematicaReg(models.Model):
    region=models.CharField(max_length=9, verbose_name='Región')
    nivel=models.CharField(max_length=50, verbose_name='Nivel')
    cantidad=models.PositiveIntegerField(verbose_name='Cantidad')
    porcentaje=models.DecimalField(max_digits=5, decimal_places=2, verbose_name='Porcentaje')
    
    class Meta:
        managed=False
        verbose_name = "Vista Resolucion Matematica Region"
        verbose_name_plural = "Vistas Resolucion Matematica Region"
        db_table = "v_resolucion_matematica_reg"
        
    def __str__(self):
        return f'{self.region} {self.nivel} {self.cantidad} {self.porcentaje}'