from django.db import models

class Supervisor(models.Model):
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