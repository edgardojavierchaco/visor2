import os
import json
from django.db import models
from django.conf import settings
from django.forms import model_to_dict
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator


ACTIVIDAD_CHOICES=[
    ('APOYO','APOYO'),
    ('SEGUIMIENTO','SEGUIMIENTO'),
]

MESES_CHOICES = [    
    ('ABRIL', 'ABRIL'),    
    ('JULIO', 'JULIO'),    
    ('NOVIEMBRE', 'NOVIEMBRE'),    
    ('DICIEMBRE', 'DICIEMBRE'),
]

# Modelo para Funciones de Apoyo a la Inclusión
class FuncionApoyoInclusion(models.Model):
    cod_func=models.IntegerField(verbose_name='Cod_Funcion')
    funcion=models.CharField(max_length=255, verbose_name='Funcion')
    
    class Meta:
        verbose_name='Funcion_Apoyo'
        verbose_name_plural='Funciones_Apoyos'
        db_table='funcion_apoyo'
    
    def __str__(self):
        return f'{self.cod_func} - {self.funcion}'

    def toJSON(self):
        item=model_to_dict(self)
        item=self.cod_func
        item=self.funcion
        return item


# Modelo para Servicios Discpacidad
class ServiciosDiscapacidad(models.Model):
    cod_serv=models.IntegerField(verbose_name='Cod_Servicio')
    servicio=models.CharField(max_length=255, verbose_name='Servicio')
    
    class Meta:
        verbose_name='Servicio_Discapacidad'
        verbose_name_plural='Servicios_Discapacidades'
        db_table='servicio_discapacidad'
    
    def __str__(self):
        return f'{self.cod_serv} - {self.servicio}'

    def toJSON(self):
        item=model_to_dict(self)
        item=self.cod_serv
        item=self.servicio
        return item


# Listado Discapacidad
class DiscapacidadListado(models.Model):
    cod_disc=models.IntegerField(verbose_name='Cod_Discapacidad')
    discapacidad=models.CharField(max_length=255, verbose_name='Discapacidad')
    
    class Meta:
        verbose_name='Listado_Discapacidad'
        verbose_name_plural='Listados_Discapacidades'
        db_table='listado_discapacidad'
    
    def __str__(self):
        return f'{self.cod_disc} - {self.discapacidad}'

    def toJSON(self):
        item=model_to_dict(self)
        item=self.cod_disc
        item=self.discapacidad
        return item


# Profesionales
class Profesionales(models.Model):
    cod_prof=models.IntegerField(verbose_name='Cod_Profesional')
    profesion=models.CharField(max_length=255, verbose_name='Profesion')
    
    class Meta:
        verbose_name='Listado_Profesion'
        verbose_name_plural='Listados_Profesiones'
        db_table='listado_profesion'
    
    def __str__(self):
        return f'{self.cod_prof} - {self.profesion}'

    def toJSON(self):
        item=model_to_dict(self)
        item=self.cod_prof
        item=self.profesion
        return item


# Modelo carga Escuela Especial
class MaestrosGrado(models.Model):
    cueanexo=models.CharField(max_length=9, verbose_name='Cueanexo')
    mes=models.CharField(max_length=25, choices=MESES_CHOICES, verbose_name='Mes')
    anio=models.IntegerField(validators=[MinValueValidator(2025)], verbose_name='Año')
    dni_doc=models.CharField(max_length=8, verbose_name='DNI')
    apellido=models.CharField(max_length=255, verbose_name='Apellidos')
    nombres=models.CharField(max_length=255, verbose_name='Nombres')
    pof=models.ForeignKey(FuncionApoyoInclusion, on_delete=models.CASCADE, verbose_name='POF')
    matric_compartida=models.IntegerField(verbose_name='Matric_Compartida')
    espacio_compartido=models.IntegerField(verbose_name='Espacio_Compartido')
    servicio_maestro=models.ForeignKey(ServiciosDiscapacidad, on_delete=models.CASCADE, verbose_name='Servicio')
    sede=models.IntegerField(verbose_name='Sede')
    cud=models.IntegerField(verbose_name='CUD')
    discapadidad=models.ForeignKey(DiscapacidadListado, on_delete=models.CASCADE, verbose_name='Discapacidad')
    edad=models.IntegerField(verbose_name='Edad')
    
    class Meta:
        verbose_name='Maestro_Grado_Especial'
        verbose_name_plural='Maestros_Grados_Especiales'
        db_table='especial_maestrogrado'
    
    def __str__(self):
        return f'{self.cueanexo} - {self.dni_doc}: {self.apellido}, {self.nombres}'

    def toJSON(self):
        item=model_to_dict(self)
        item=self.cueanexo
        item=self.dni_doc
        item=self.apellido
        item=self.nombres
        item=self.pof.funcion
        item=self.matric_compartida
        item=self.espacio_compartido
        item=self.servicio_maestro.servicio
        item=self.sede
        item=self.cud
        item=self.discapadidad.discapacidad
        item=self.edad
        return item


# Modelo Carga MAI
class MAI(models.Model):
    cueanexo=models.CharField(max_length=9, verbose_name='Cueanexo')
    mes=models.CharField(max_length=25, choices=MESES_CHOICES, verbose_name='Mes')
    anio=models.IntegerField(validators=[MinValueValidator(2025)], verbose_name='Año')
    actividad=models.CharField(max_length=25, choices=ACTIVIDAD_CHOICES, verbose_name='Actividad')
    total=models.IntegerField(verbose_name='Total')
    mes=models.CharField(max_length=25, choices=MESES_CHOICES, verbose_name='Mes')
    anio = models.IntegerField(validators=[MinValueValidator(2025)], verbose_name='Año')
    admision=models.IntegerField(verbose_name='Admision')
    contexto=models.IntegerField(verbose_name='Contexto')
    barreras=models.TextField(verbose_name='Barreras')
    domicilio=models.IntegerField(verbose_name='Domicilio')
    redes=models.IntegerField(verbose_name='Redes')
    instit=models.IntegerField(verbose_name='Instituciones')

    class Meta:
        verbose_name='MAI'
        verbose_name_plural='MAIS'
        db_table='registro_mai'
    
    def __str__(self):
        return f'{self.cueanexo} - {self.actividad}'

    def toJSON(self):
        item=model_to_dict(self)
        item=self.cueanexo
        item=self.mes
        item=self.anio
        item=self.actividad
        item=self.total
        item=self.mes
        item=self.anio
        item=self.admision
        item=self.contexto
        item=self.barreras
        item=self.domicilio
        item=self.redes
        item=self.instit
        return item


# Modelo de Escuelas Nivel con Especial
class EscuelacDiscapacidad(models.Model):
    cueanexo=models.CharField(max_length=9, verbose_name='Cueanexo')
    mes=models.CharField(max_length=25, choices=MESES_CHOICES, verbose_name='Mes')
    anio=models.IntegerField(validators=[MinValueValidator(2025)], verbose_name='Año')
    inclusion=models.IntegerField(verbose_name='Inclusion')
    acompanamiento=models.BooleanField(default=False, verbose_name='Acompañamiento')
    cuecuit_instit=models.CharField(max_length=11, verbose_name='CUE_CUIT')
    sector=models.CharField(max_length=50, verbose_name='Sector')
    cud=models.IntegerField(verbose_name='CUD')
    porcen_eval=models.IntegerField(verbose_name='Procentaje')
    graduados=models.IntegerField(verbose_name='Graduados')
    doc_capac=models.IntegerField(verbose_name='Docentes')
    mat_eq=models.IntegerField(verbose_name='Materiales')
    
    class Meta:
        verbose_name='Escuela_Discapacidad'
        verbose_name_plural='Escuelas_Discpacidades'
        db_table='escuela_discapacidad'
    
    def __str__(self):
        return f'{self.cueanexo} - {self.mes} {self.anio}'

    def toJSON(self):
        item=model_to_dict(self)
        item=self.cueanexo
        item=self.mes
        item=self.anio
        item=self.inclusion
        item=self.acompanamiento
        item=self.cuecuit_instit
        item=self.sector
        item=self.cud
        item=self.porcen_eval
        item=self.graduados
        item=self.doc_capac
        item=self.mat_eq
        return item


# Model Equipo Interdisciplinario
class EquipoInterProf(models.Model):
    cueanexo=models.CharField(max_length=9, verbose_name='Cueanexo')
    mes=models.CharField(max_length=25, choices=MESES_CHOICES, verbose_name='Mes')
    anio=models.IntegerField(validators=[MinValueValidator(2025)], verbose_name='Año')
    dni=models.CharField(max_length=8, verbose_name='DNI')
    apellido=models.CharField(max_length=255, verbose_name='Apellidos')
    nombres=models.CharField(max_length=255, verbose_name='Nombres')
    prof=models.ForeignKey(Profesionales, on_delete=models.CASCADE, verbose_name='Profesion')
    atendidos=models.IntegerField(verbose_name='Atendidos')
    cue=models.CharField(max_length=9, verbose_name='Cue')
    oferta=models.CharField(max_length=255, verbose_name='Oferta')
    situcion=models.CharField(max_length=255, verbose_name='situacion')
    apoyo=models.IntegerField(verbose_name='Apoyo')
    seguimiento=models.IntegerField(verbose_name='Seguimiento')
    riesgo=models.IntegerField(verbose_name='Riesgo')
    causal=models.CharField(max_length=255, verbose_name='Causal')
    ppi=models.IntegerField(verbose_name='PPI')
    plan_acompa=models.CharField(max_length=255, verbose_name='Plan')
    egresados=models.IntegerField(verbose_name='Egresados')
    deportes=models.IntegerField(verbose_name='Deportes')
    accesibilidad=models.BooleanField(default=False, verbose_name='Accesibilidad')
    articulacion=models.CharField(max_length=11, verbose_name='Articulacion')
    nombre_artic=models.CharField(max_length=255, verbose_name='Nombre_Institucion')
    alfabetizacion=models.BooleanField(default=False, verbose_name='Alfabetizacion')
    
    
    class Meta:
        verbose_name='Equipo Interdisciplinario'
        verbose_name_plural='Equipos Interdisciplinarios'
        db_table='equipo_interdisciplinario'
    
    def __str__(self):
        return f'{self.cueanexo} - {self.mes} {self.anio}'

    def toJSON(self):
        item=model_to_dict(self)
        item=self.cueanexo
        item=self.mes
        item=self.anio
        item=self.dni
        item=self.apellido
        item=self.nombres
        item=self.prof
        item=self.atendidos
        item=self.cue
        item=self.oferta
        item=self.situcion
        item=self.apoyo
        item=self.seguimiento
        item=self.riesgo
        item=self.causal
        item=self.ppi
        item=self.plan_acompa
        item=self.egresados
        item=self.deportes
        item=self.accesibilidad
        item=self.articulacion
        item=self.nombre_artic
        item=self.alfabetizacion
        return item


