import os
from django.db import models
from django.conf import settings
from django.forms import model_to_dict
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator


MESES_CHOICES = [
    ('ENERO', 'ENERO'),
    ('FEBRERO', 'FEBRERO'),
    ('MARZO', 'MARZO'),
    ('ABRIL', 'ABRIL'),
    ('MAYO', 'MAYO'),
    ('JUNIO', 'JUNIO'),
    ('JULIO', 'JULIO'),
    ('AGOSTO', 'AGOSTO'),
    ('SEPTIEMBRE', 'SEPTIEMBRE'),
    ('OCTUBRE', 'OCTUBRE'),
    ('NOVIEMBRE', 'NOVIEMBRE'),
    ('DICIEMBRE', 'DICIEMBRE'),
]

INSTALACIONES_CHOICES=[
    ('SALA', 'SALA'),
    ('AULA', 'AULA'),
    ('DOMICILIO', 'DOMICILIO'),
    ('OTRAS', 'OTRAS'),        
]

NIVELES_CHOICES=[
    ('INICIAL', 'INICIAL'),
    ('PRIMARIO', 'PRIMARIO'),
    ('SECUNDARIO', 'SECUNDARIO'),
    ('PRIMARIO ADULTO', 'PRIMARIO ADULTO'),
    ('SECUNDARIO ADULTO', 'SECUNDARIO ADULTO'),
    ('SUPERIOR NO UNIVERSITARIO', 'SUPERIOR NO UNIVERSITARIO'),
    ('UNIVERSITARIO', 'UNIVERSITARIO'),
    ('OTROS', 'OTROS'),        
]

USUARIOS_CHOICES=[
    ('ALUMNOS', 'ALUMNOS'),
    ('DOCENTES', 'DOCENTES'),
    ('OTROS', 'OTROS'),        
]

PROCESOS_CHOICES=[
    ('SELLADOS', 'SELLADOS'),
    ('INVENTARIADOS', 'INVENTARIADOS'),
    ('CLASIFICADOS', 'CLASIFICADOS'),     
    ('CATALOGADOS', 'CATALOGADOS'),   
    ('RESTAURADOS', 'RESTAURADOS'),
    ('BAJAS', 'BAJAS'),
]

class ServiciosMatBiblio(models.Model):
    cod_servicio=models.IntegerField(verbose_name='Codigo')
    cod_nomservicio=models.IntegerField(default=0,verbose_name='CodNom')
    nom_servicio=models.CharField(max_length=255, verbose_name='Detalle')
    
    class Meta:        
        verbose_name = 'Servicio_Material_Biblio'
        verbose_name_plural='Servicios_Materiales_Biblios'
        db_table= 'servicio_material_biblio'

    def __str__(self):
        return self.nom_servicio
    
    def toJSON(self):
        item = model_to_dict(self)
        item['cod_servicio'] = self.cod_servicio
        item['cod_nomservicio'] = self.cod_nomservicio
        item['nom_servicio'] = self.nom_servicio
        return item


class Turnos(models.Model):
    nom_turno=models.CharField(max_length=50, verbose_name='Turno')
    
    class Meta:        
        verbose_name = 'Turno'
        verbose_name_plural='Turnos'
        db_table= 'turno'
    
    def __str__(self):
        return self.nom_turno
    
    

class TipoMaterialBiblio(models.Model):
    nom_material=models.CharField(max_length=255, verbose_name='Tipo_Material')
    
    class Meta:        
        verbose_name = 'Tipo_Material_Biblio'
        verbose_name_plural='Tipos_Materiales_Biblios'
        db_table= 'tipo_material_biblio'
    
    def __str__(self):
        return self.nom_material
        
        
class MaterialBibliografico(models.Model):
    cueanexo=models.CharField(max_length=9, verbose_name='Cueanexo')
    mes=models.CharField(max_length=25, choices=MESES_CHOICES, verbose_name='Mes')
    anio = models.IntegerField(validators=[MinValueValidator(2025)], verbose_name='Año')
    servicio=models.ForeignKey(ServiciosMatBiblio, on_delete=models.CASCADE, verbose_name='Servicio')
    turnos=models.ForeignKey(Turnos, on_delete=models.CASCADE, verbose_name='Turnos')
    t_material=models.ForeignKey(TipoMaterialBiblio, on_delete=models.CASCADE, verbose_name='Material')
    cantidad=models.IntegerField(verbose_name='Cantidad')
    
    class Meta:        
        verbose_name = 'Material_Bibliografico'
        verbose_name_plural='Materiales_Bibliograficos'
        db_table= 'material_bibliografico'

    def __str__(self):
        return f"{self.cueanexo} - {self.servicio}"
    
    def clean(self):
        """ Validación para permitir solo servicios con cod_servicio=1 """
        if self.servicio.cod_servicio != 1:
            raise ValidationError({'servicio': 'El servicio seleccionado no es válido.'})
    
    def toJSON(self):
        item = model_to_dict(self)
        item['cueanexo'] = self.cueanexo
        item['mes'] = self.mes 
        item['anio'] = self.anio
        item['servicio'] = self.servicio.nom_servicio
        item['turnos'] = self.turnos.nom_turno
        item['t_material'] = self.t_material.nom_material
        item['cantidad'] = self.cantidad
        return item
    
    

class ServicioReferencia(models.Model):
    cueanexo=models.CharField(max_length=9, verbose_name='Cueanexo')
    mes=models.CharField(max_length=25, choices=MESES_CHOICES, verbose_name='Mes')
    anio = models.IntegerField(validators=[MinValueValidator(2025)], verbose_name='Año')
    servicio=models.ForeignKey(ServiciosMatBiblio, on_delete=models.CASCADE, verbose_name='Servicio')
    turnos=models.ForeignKey(Turnos, on_delete=models.CASCADE, verbose_name='Turnos')
    varones=models.IntegerField(verbose_name='Varones')
    total=models.IntegerField(verbose_name='Total')
    
    class Meta:        
        verbose_name = 'Servicio_Referencia'
        verbose_name_plural='Servicios_Referencias'
        db_table= 'servicio_referencia'

    def __str__(self):
        return f"{self.cueanexo} - {self.servicio}"   
    
    
    def toJSON(self):
        item = model_to_dict(self)
        item['cueanexo'] = self.cueanexo
        item['mes'] = self.mes 
        item['anio'] = self.anio
        item['servicio'] = self.servicio.nom_servicio
        item['turnos'] = self.turnos.nom_turno
        item['varones'] = self.varones
        item['total'] = self.total
        return item    
    
    
class ServicioReferenciaVirtual(models.Model):
    cueanexo=models.CharField(max_length=9, verbose_name='Cueanexo')
    mes=models.CharField(max_length=25, choices=MESES_CHOICES, verbose_name='Mes')
    anio = models.IntegerField(validators=[MinValueValidator(2025)], verbose_name='Año')
    servicio=models.ForeignKey(ServiciosMatBiblio, on_delete=models.CASCADE, verbose_name='Servicio')
    turnos=models.ForeignKey(Turnos, on_delete=models.CASCADE, verbose_name='Turnos')
    varones=models.IntegerField(verbose_name='Varones')
    total=models.IntegerField(verbose_name='Total')
    
    class Meta:        
        verbose_name = 'Servicio_Referencia_Virtual'
        verbose_name_plural='Servicios_Referencias_Virtuales'
        db_table= 'servicio_referencia_virtual'

    def __str__(self):
        return f"{self.cueanexo} - {self.servicio}"    
    
    
    def toJSON(self):
        item = model_to_dict(self)
        item['cueanexo'] = self.cueanexo
        item['mes'] = self.mes 
        item['anio'] = self.anio
        item['servicio'] = self.servicio.nom_servicio
        item['turnos'] = self.turnos.nom_turno
        item['varones'] = self.varones
        item['total'] = self.total
        return item


class ServicioPrestamo(models.Model):
    cueanexo=models.CharField(max_length=9, verbose_name='Cueanexo')
    mes=models.CharField(max_length=25, choices=MESES_CHOICES, verbose_name='Mes')
    anio = models.IntegerField(validators=[MinValueValidator(2025)], verbose_name='Año')
    servicio=models.ForeignKey(ServiciosMatBiblio, on_delete=models.CASCADE, verbose_name='Servicio')
    turnos=models.ForeignKey(Turnos, on_delete=models.CASCADE, verbose_name='Turnos')
    instalacion=models.CharField(max_length=255, choices=INSTALACIONES_CHOICES, verbose_name='Instalacion')
    total=models.IntegerField(verbose_name='Total')
    
    class Meta:        
        verbose_name = 'Servicio_Prestamo'
        verbose_name_plural='Servicios_Prestamos'
        db_table= 'servicio_prestamo'

    def __str__(self):
        return f"{self.cueanexo} - {self.servicio}"
    
        
    def toJSON(self):
        item = model_to_dict(self)
        item['cueanexo'] = self.cueanexo
        item['mes'] = self.mes 
        item['anio'] = self.anio
        item['servicio'] = self.servicio.nom_servicio
        item['turnos'] = self.turnos.nom_turno
        item['instalacion'] = self.instalacion
        item['total'] = self.total
        return item
        


class InformePedagogico(models.Model):
    cueanexo=models.CharField(max_length=9, verbose_name='Cueanexo')
    mes=models.CharField(max_length=25, choices=MESES_CHOICES, verbose_name='Mes')
    anio = models.IntegerField(validators=[MinValueValidator(2025)], verbose_name='Año')
    servicio=models.ForeignKey(ServiciosMatBiblio, on_delete=models.CASCADE, verbose_name='Servicio')
    varones=models.IntegerField(verbose_name='Varones')
    total=models.IntegerField(verbose_name='Total')
    
    class Meta:        
        verbose_name = 'Informe_Pedagogico'
        verbose_name_plural='Informes_Pedagogicos'
        db_table= 'informe_pedagogico'

    def __str__(self):
        return f"{self.cueanexo} - {self.servicio}"    
    
    
    def toJSON(self):
        item = model_to_dict(self)
        item['cueanexo'] = self.cueanexo
        item['mes'] = self.mes 
        item['anio'] = self.anio
        item['servicio'] = self.servicio.nom_servicio
        item['varones'] = self.varones
        item['total'] = self.total
        return item


class AsistenciaUsuarios(models.Model):
    cueanexo=models.CharField(max_length=9, verbose_name='Cueanexo')
    mes=models.CharField(max_length=25, choices=MESES_CHOICES, verbose_name='Mes')
    anio = models.IntegerField(validators=[MinValueValidator(2025)], verbose_name='Año')
    nivel=models.CharField(max_length=50, choices=NIVELES_CHOICES, verbose_name='Nivel')
    usuario=models.CharField(max_length=50, choices=USUARIOS_CHOICES, verbose_name='Usuarios')
    varones=models.IntegerField(verbose_name='Varones')
    total=models.IntegerField(verbose_name='Total')
    
    class Meta:        
        verbose_name = 'Asistencia_Usuario'
        verbose_name_plural='Asistencias_Usuarios'
        db_table= 'asistencia_usuario'

    def __str__(self):
        return f"{self.cueanexo} - {self.nivel}: {self.usuario}"    
    
    def toJSON(self):
        item = model_to_dict(self)
        item['cueanexo'] = self.cueanexo
        item['mes'] = self.mes 
        item['anio'] = self.anio
        item['nivel'] = self.nivel
        item['usuario'] = self.usuario
        item['varones'] = self.varones
        item['total'] = self.total
        return item


class InstitucionesPrestaServicios(models.Model):
    cueanexo=models.CharField(max_length=9, verbose_name='Cueanexo')
    mes=models.CharField(max_length=25, choices=MESES_CHOICES, verbose_name='Mes')
    anio = models.IntegerField(validators=[MinValueValidator(2025)], verbose_name='Año')    
    escuela=models.CharField(max_length=255, verbose_name='Escuela')
    matricula=models.IntegerField(verbose_name='Matricula')
    docentes=models.IntegerField(verbose_name='Docentes')
    matricdisc=models.IntegerField(verbose_name='Discapacidad')
    etnia=models.IntegerField(verbose_name='Etnia')
        
    class Meta:        
        verbose_name = 'Institucion_Servicio'
        verbose_name_plural='Instituciones_Servicios'
        db_table= 'institucion_servicio'

    def __str__(self):
        return f"{self.escuela}"    
    
    def toJSON(self):
        item = model_to_dict(self)
        item['cueanexo'] = self.cueanexo
        item['mes'] = self.mes 
        item['anio'] = self.anio
        item['escuela'] = self.escuela
        item['matricula'] = self.matricula
        item['docentes'] = self.docentes
        item['matricdisc'] = self.matricdisc
        item['etnia'] = self.etnia
        return item


class ProcesosTecnicos(models.Model):
    cueanexo=models.CharField(max_length=9, verbose_name='Cueanexo')
    mes=models.CharField(max_length=25, choices=MESES_CHOICES, verbose_name='Mes')
    anio = models.IntegerField(validators=[MinValueValidator(2025)], verbose_name='Año')
    material=models.ForeignKey(TipoMaterialBiblio, on_delete=models.CASCADE, verbose_name='Material')    
    procesos=models.CharField(max_length=255, choices=PROCESOS_CHOICES, verbose_name='Procesos')    
    total=models.IntegerField(verbose_name='Total')
        
    class Meta:        
        verbose_name = 'Proceso_Tecnico'
        verbose_name_plural='Procesos_Tecnicos'
        db_table= 'proceso_tecnico'

    def __str__(self):
        return f"{self.cueanexo} - {self.material}: {self.procesos}"    
    
    def toJSON(self):
        item = model_to_dict(self)
        item['cueanexo'] = self.cueanexo
        item['mes'] = self.mes 
        item['anio'] = self.anio
        item['material'] = self.material.nom_material
        item['procesos'] = self.procesos
        item['total'] = self.total        
        return item


class Aguapey(models.Model):
    cueanexo=models.CharField(max_length=9, verbose_name='Cueanexo')
    mes=models.CharField(max_length=25, choices=MESES_CHOICES, verbose_name='Mes')
    anio = models.IntegerField(validators=[MinValueValidator(2025)], verbose_name='Año')    
    total_mes=models.IntegerField(verbose_name='Total Mes')
    total_base=models.IntegerField(verbose_name='Total Base')
        
    class Meta:        
        verbose_name = 'Aguapey'
        verbose_name_plural='Aguapeys'
        db_table= 'Aguapey'

    def __str__(self):
        return f"{self.cueanexo} - {self.total_mes}: {self.total_base}"    
    
    def toJSON(self):
        item = model_to_dict(self)
        item['cueanexo'] = self.cueanexo
        item['mes'] = self.mes 
        item['anio'] = self.anio
        item['total_mes'] = self.total_mes
        item['total_base'] = self.total_base        
        return item


class Escuelas(models.Model):
    id = models.IntegerField(primary_key=True)
    cueanexo=models.CharField(max_length=9, verbose_name='Cueanexo')
    nom_est=models.CharField(max_length=255, verbose_name='Nombre')
    oferta=models.CharField(max_length=255, verbose_name='Ofertas')
    region_loc=models.CharField(max_length=255, verbose_name='Regional')
    localidad=models.CharField(max_length=255, verbose_name='Localidad')
    departamento=models.CharField(max_length=255, verbose_name='Departamento')
    
    class Meta:  
        managed=False      
        verbose_name = 'Escuela'
        verbose_name_plural='Escuelas'
        db_table= 'cueanexo_nomest_ofertas'

    def __str__(self):
        return f"{self.cueanexo} - {self.nom_est}: {self.oferta}"    
    
    def toJSON(self):
        item = model_to_dict(self)
        item['id'] = self.id
        item['cueanexo'] = self.cueanexo
        item['nom_est'] = self.nom_est
        item['oferta'] = self.oferta
        item['region_loc'] = self.region_loc
        item['localidad'] = self.localidad     
        item['departamento'] = self.departamento   
        return item


class GenerarInforme(models.Model):
    cueanexo=models.CharField(max_length=9, verbose_name='Cueanexo')
    meses=models.CharField(max_length=25, choices=MESES_CHOICES, verbose_name='Mes')
    annos=models.IntegerField(validators=[MinValueValidator(2025)],verbose_name='Año')
    f_generacion=models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Generación")
    estado=models.CharField(default='GENERADO', verbose_name='Estado')
    f_envio=models.DateTimeField(auto_now_add=False,blank=True, null=True, verbose_name='Fecha Envío')
    
    class Meta:              
        verbose_name = 'GenerarInforme'
        verbose_name_plural='GenerarInformes'
        db_table= 'generar_informe'

    def __str__(self):
        return f"{self.cueanexo} - {self.meses}: {self.annos}"    
    
    def toJSON(self):
        item = model_to_dict(self)        
        item['cueanexo'] = self.cueanexo
        item['meses'] = self.meses
        item['annos'] = self.annos
        item['f_generacion'] = self.f_generacion      
        item['estado'] = self.estado
        item['f_envio'] = self.f_envio   
        return item


class PlanillasAnexas(models.Model):
    cueanexo=models.CharField(max_length=9, verbose_name='Cueanexo')
    mes=models.CharField(max_length=25, verbose_name='Mes')
    anio=models.IntegerField(verbose_name='Año')
    servicio=models.ForeignKey(ServiciosMatBiblio, on_delete=models.CASCADE, verbose_name='Servicios')
    cantidad=models.IntegerField(verbose_name='Cantidad')
    
    class Meta:              
        verbose_name = 'PlanillaAnexa'
        verbose_name_plural='PlanillasAnexas'
        db_table= 'planilla_anexa'
        
    def __str__(self):
        return f"{self.cueanexo} {self.mes} {self.anio} - {self.servicio}"
    
    def toJSON(self):
        item = model_to_dict(self)        
        item['cueanexo'] = self.cueanexo
        item['mes'] = self.mes
        item['anios'] = self.anio
        item['servicio'] = self.servicio.nom_servicio      
        item['cantidad'] = self.cantidad 
        return item
