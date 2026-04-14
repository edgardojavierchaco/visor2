from django.db import models

class Supervisor(models.Model):
    """
    Modelo que representa a un Supervisor.

    Atributos:
        dni (str): El número de identificación único del supervisor.
        apellido (str): El apellido del supervisor.
        nombres (str): El/los nombre(s) del supervisor.
        email (str): La dirección de correo electrónico del supervisor.
        telefono (str): El número de teléfono del supervisor.
        region (str): La designación regional del supervisor.
    """
    
    dni=models.CharField(max_length=8, verbose_name='DNI')
    apellido=models.CharField(max_length=255, verbose_name='Apellido')
    nombres = models.CharField(max_length=255, verbose_name='Nombres')
    email = models.EmailField(verbose_name='Email')
    telefono = models.CharField(max_length=11, null=False, blank=False, verbose_name='Teléfono')
    region=models.CharField(max_length=25, null=False, blank=False, verbose_name='Regional')
    
    class Meta:
        verbose_name = 'Supervisor'
        verbose_name_plural='Supervisores'
        db_table= 'public.supervisores'
    
    def __str__(self):
        return f"{self.apellido} {self.nombres}"

class EscuelaSupervisor(models.Model):
    """
    Modelo que representa una escuela supervisada por un Supervisor.

    Atributos:
        cueanexo (str): El identificador único de la escuela.
        region_esc (str): La designación regional de la escuela.
        oferta (str): La oferta educativa proporcionada por la escuela.
        modalidad (str): La modalidad de educación (por ejemplo, común, técnica).
        supervisor (Supervisor): El Supervisor que supervisa la escuela.
    """
    
    cueanexo = models.CharField(max_length=9, null=False, blank=False, verbose_name='Cueanexo')
    region_esc=models.CharField(max_length=15, null=False, blank=False, verbose_name='Regional')
    oferta = models.CharField(max_length=100, null=False, blank=False, verbose_name='Oferta')
    modalidad=models.CharField(max_length=100, null=False, blank=False, verbose_name='Modalidadad')
    supervisor = models.ForeignKey(Supervisor, on_delete=models.DO_NOTHING, related_name='escuelas', verbose_name='Supervisor')

    class Meta:
        verbose_name = 'Escuela Supervisor'
        verbose_name_plural='Escuelas Supervisores'
        db_table= 'public.escuela_supervisores'
    
    def __str__(self):
        return self.cueanexo
    

class DirectoresRegionales(models.Model):
    """
    Modelo que representa a un Director Regional.

    Atributos:
        dni_reg (str): El número de identificación único del director.
        apellido_reg (str): El apellido del director.
        nombres_reg (str): El/los nombre(s) del director.
        email_reg (str): La dirección de correo electrónico del director.
        telefono_reg (str): El número de teléfono del director.
        region_reg (str): La designación regional del director.
    """
    
    dni_reg=models.CharField(max_length=8, verbose_name='DNI')
    apellido_reg=models.CharField(max_length=255, verbose_name='Apellido')
    nombres_reg = models.CharField(max_length=255, verbose_name='Nombres')
    email_reg = models.EmailField(verbose_name='Email')
    telefono_reg = models.CharField(max_length=11, null=False, blank=False, verbose_name='Teléfono')
    region_reg=models.CharField(max_length=25, null=False, blank=False, verbose_name='Regional')
    
    class Meta:
        verbose_name = 'Director Regional'
        verbose_name_plural='Directores Regionales'
        db_table= 'public.director_regional'
    
    def __str__(self):
        return f"{self.apellido_reg} {self.nombres_reg}"