from ast import mod
import os
import json
from django.db import models
from django.conf import settings
from django.forms import model_to_dict
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from datetime import date

from apps.oplectura.models import turno


MESES_CHOICES = [    
    ('ABRIL', 'ABRIL'),    
    ('JULIO', 'JULIO'),    
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
        
        
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.forms import model_to_dict

class MaterialBibliografico(models.Model):
    cueanexo = models.CharField(max_length=9, verbose_name='Cueanexo')
    mes = models.CharField(max_length=25, choices=MESES_CHOICES, verbose_name='Mes')
    anio = models.IntegerField(validators=[MinValueValidator(2025)], verbose_name='Año')

    servicio = models.ForeignKey(
        ServiciosMatBiblio,
        on_delete=models.CASCADE,
        verbose_name='Servicio'
    )

    turnos = models.ForeignKey(
        Turnos,
        on_delete=models.CASCADE,
        verbose_name='Turnos'
    )

    t_material = models.ForeignKey(
        TipoMaterialBiblio,
        on_delete=models.CASCADE,
        verbose_name='Material'
    )

    cantidad = models.PositiveIntegerField(verbose_name='Cantidad')

    class Meta:
        verbose_name = 'Material_Bibliografico'
        verbose_name_plural = 'Materiales_Bibliograficos'
        db_table = 'material_bibliografico'

        # 🔥 SEGURIDAD A NIVEL BASE DE DATOS (CLAVE)
        constraints = [
            models.UniqueConstraint(
                fields=[
                    'cueanexo',
                    'mes',
                    'anio',
                    'servicio',
                    'turnos',
                    't_material'
                ],
                name='unique_material_bibliografico'
            )
        ]

    def __str__(self):
        return f"{self.cueanexo} - {self.servicio}"

    # =========================
    # 🔥 VALIDACIONES
    # =========================
    def clean(self):
        super().clean()

        # 🔴 VALIDACIÓN SERVICIO PERMITIDO
        if self.servicio and self.servicio.cod_servicio not in [110, 111, 112, 113]:
            raise ValidationError({
                'servicio': 'El servicio seleccionado no es válido.'
            })

        # 🔴 VALIDACIÓN DE DUPLICADO
        if all([
            self.cueanexo,
            self.mes,
            self.anio,
            self.servicio,
            self.turnos,
            self.t_material
        ]):

            qs = MaterialBibliografico.objects.filter(
                cueanexo=self.cueanexo,
                mes=self.mes,
                anio=self.anio,
                servicio=self.servicio,
                turnos=self.turnos,
                t_material=self.t_material
            )

            # excluir si es edición
            if self.pk:
                qs = qs.exclude(pk=self.pk)

            if qs.exists():
                raise ValidationError({
                    '__all__': '⚠️ Ya existe este registro para el mismo CUE, Mes, Año, Servicio, Turno y Material.'
                })

    # =========================
    # 🔥 GUARDA SEGURO
    # =========================
    def save(self, *args, **kwargs):
        self.full_clean()  # asegura validaciones antes de guardar
        super().save(*args, **kwargs)

    # =========================
    # 🔥 JSON PARA AJAX
    # =========================
    def toJSON(self):
        item = model_to_dict(self)

        item['cueanexo'] = self.cueanexo
        item['mes'] = self.mes
        item['anio'] = self.anio

        item['servicio'] = self.servicio.nom_servicio if self.servicio else ''
        item['turnos'] = self.turnos.nom_turno if self.turnos else ''
        item['t_material'] = self.t_material.nom_material if self.t_material else ''

        item['cantidad'] = self.cantidad

        return item
    
    

class ServicioReferencia(models.Model):
    cueanexo = models.CharField(max_length=9, verbose_name='Cueanexo')
    mes = models.CharField(max_length=25, choices=MESES_CHOICES, verbose_name='Mes')
    anio = models.IntegerField(validators=[MinValueValidator(2025)], verbose_name='Año')

    servicio = models.ForeignKey(
        ServiciosMatBiblio,
        on_delete=models.CASCADE,
        verbose_name='Servicio'
    )

    turnos = models.ForeignKey(
        Turnos,
        on_delete=models.CASCADE,
        verbose_name='Turnos'
    )

    varones = models.PositiveIntegerField(verbose_name='Varones')
    total = models.PositiveIntegerField(verbose_name='Total')

    class Meta:
        verbose_name = 'Servicio_Referencia'
        verbose_name_plural = 'Servicios_Referencias'
        db_table = 'servicio_referencia'

        # 🔥 EVITA DUPLICADOS A NIVEL BASE DE DATOS
        constraints = [
            models.UniqueConstraint(
                fields=[
                    'cueanexo',
                    'mes',
                    'anio',
                    'servicio',
                    'turnos'
                ],
                name='unique_servicio_referencia'
            )
        ]

    def __str__(self):
        return f"{self.cueanexo} - {self.servicio}"

    # =========================
    # 🔥 VALIDACIONES
    # =========================
    def clean(self):
        super().clean()

        # 🔴 VALIDACIÓN 1: total no puede ser menor que varones
        if self.varones is not None and self.total is not None:
            if self.total < self.varones:
                raise ValidationError({
                    'total': 'El Total no puede ser menor que Varones.'
                })

        # 🔴 VALIDACIÓN 2: DUPLICADO (regla de negocio)
        if all([
            self.cueanexo,
            self.mes,
            self.anio,
            self.servicio,
            self.turnos
        ]):

            qs = ServicioReferencia.objects.filter(
                cueanexo=self.cueanexo,
                mes=self.mes,
                anio=self.anio,
                servicio=self.servicio,
                turnos=self.turnos
            )

            # excluir si es edición
            if self.pk:
                qs = qs.exclude(pk=self.pk)

            if qs.exists():
                raise ValidationError({
                    '__all__': '⚠️ Ya existe este Servicio con este Turno para el mismo CUE, Mes y Año.'
                })

    # =========================
    # 🔥 GUARDA SEGURO
    # =========================
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    # =========================
    # 🔥 JSON PARA AJAX
    # =========================
    def toJSON(self):
        item = model_to_dict(self)

        item['cueanexo'] = self.cueanexo
        item['mes'] = self.mes
        item['anio'] = self.anio

        item['servicio'] = self.servicio.nom_servicio if self.servicio else ''
        item['turnos'] = self.turnos.nom_turno if self.turnos else ''

        item['varones'] = self.varones
        item['total'] = self.total

        return item
    
    
class ServicioReferenciaVirtual(models.Model):
    cueanexo = models.CharField(max_length=9, verbose_name='Cueanexo')
    mes = models.CharField(max_length=25, choices=MESES_CHOICES, verbose_name='Mes')
    anio = models.IntegerField(validators=[MinValueValidator(2025)], verbose_name='Año')

    servicio = models.ForeignKey(
        ServiciosMatBiblio,
        on_delete=models.CASCADE,
        verbose_name='Servicio'
    )

    turnos = models.ForeignKey(
        Turnos,
        on_delete=models.CASCADE,
        verbose_name='Turnos'
    )

    varones = models.PositiveIntegerField(verbose_name='Varones')
    total = models.PositiveIntegerField(verbose_name='Total')

    class Meta:
        verbose_name = 'Servicio_Referencia_Virtual'
        verbose_name_plural = 'Servicios_Referencias_Virtuales'
        db_table = 'servicio_referencia_virtual'

        # 🔥 EVITA DUPLICADOS EN BASE DE DATOS
        constraints = [
            models.UniqueConstraint(
                fields=[
                    'cueanexo',
                    'mes',
                    'anio',
                    'servicio',
                    'turnos'
                ],
                name='unique_servicio_referencia_virtual'
            )
        ]

    def __str__(self):
        return f"{self.cueanexo} - {self.servicio}"

    # =========================
    # 🔥 VALIDACIONES
    # =========================
    def clean(self):
        super().clean()

        # 🔴 VALIDACIÓN 1: total >= varones
        if self.varones is not None and self.total is not None:
            if self.total < self.varones:
                raise ValidationError({
                    'total': 'El Total no puede ser menor que Varones.'
                })

        # 🔴 VALIDACIÓN 2: DUPLICADO
        if all([
            self.cueanexo,
            self.mes,
            self.anio,
            self.servicio,
            self.turnos
        ]):

            qs = ServicioReferenciaVirtual.objects.filter(
                cueanexo=self.cueanexo,
                mes=self.mes,
                anio=self.anio,
                servicio=self.servicio,
                turnos=self.turnos
            )

            # excluir si es edición
            if self.pk:
                qs = qs.exclude(pk=self.pk)

            if qs.exists():
                raise ValidationError({
                    '__all__': '⚠️ Ya existe este Servicio Virtual con este Turno para el mismo CUE, Mes y Año.'
                })

    # =========================
    # 🔥 GUARDA SEGURO
    # =========================
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    # =========================
    # 🔥 JSON PARA FRONTEND
    # =========================
    def toJSON(self):
        item = model_to_dict(self)

        item['cueanexo'] = self.cueanexo
        item['mes'] = self.mes
        item['anio'] = self.anio

        item['servicio'] = self.servicio.nom_servicio if self.servicio else ''
        item['turnos'] = self.turnos.nom_turno if self.turnos else ''

        item['varones'] = self.varones
        item['total'] = self.total

        return item


class ServicioPrestamo(models.Model):
    cueanexo = models.CharField(max_length=9, verbose_name='Cueanexo')
    mes = models.CharField(max_length=25, choices=MESES_CHOICES, verbose_name='Mes')
    anio = models.IntegerField(validators=[MinValueValidator(2025)], verbose_name='Año')

    servicio = models.ForeignKey(
        ServiciosMatBiblio,
        on_delete=models.CASCADE,
        verbose_name='Servicio'
    )

    turnos = models.ForeignKey(
        Turnos,
        on_delete=models.CASCADE,
        verbose_name='Turnos'
    )

    instalacion = models.CharField(
        max_length=255,
        choices=INSTALACIONES_CHOICES,
        verbose_name='Instalacion'
    )

    total = models.PositiveIntegerField(verbose_name='Total')

    class Meta:
        verbose_name = 'Servicio_Prestamo'
        verbose_name_plural = 'Servicios_Prestamos'
        db_table = 'servicio_prestamo'

        # 🔥 EVITA DUPLICADOS A NIVEL BASE DE DATOS
        constraints = [
            models.UniqueConstraint(
                fields=[
                    'cueanexo',
                    'mes',
                    'anio',
                    'servicio',
                    'turnos',
                    'instalacion'
                ],
                name='unique_servicio_prestamo'
            )
        ]

    def __str__(self):
        return f"{self.cueanexo} - {self.servicio}"

    # =========================
    # 🔥 VALIDACIONES
    # =========================
    def clean(self):
        super().clean()

        # 🔴 VALIDACIÓN DE CAMPOS OBLIGATORIOS (seguridad extra)
        if not self.total or self.total < 0:
            raise ValidationError({
                'total': 'El total debe ser mayor o igual a 0.'
            })

        # 🔴 VALIDACIÓN DE DUPLICADO
        if all([
            self.cueanexo,
            self.mes,
            self.anio,
            self.servicio,
            self.turnos,
            self.instalacion
        ]):

            qs = ServicioPrestamo.objects.filter(
                cueanexo=self.cueanexo,
                mes=self.mes,
                anio=self.anio,
                servicio=self.servicio,
                turnos=self.turnos,
                instalacion=self.instalacion
            )

            # excluir si es edición
            if self.pk:
                qs = qs.exclude(pk=self.pk)

            if qs.exists():
                raise ValidationError({
                    '__all__': '⚠️ Ya existe este Préstamo para este CUE, Mes, Año, Servicio, Turno e Instalación.'
                })

    # =========================
    # 🔥 GUARDA SEGURA
    # =========================
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    # =========================
    # 🔥 JSON PARA FRONTEND
    # =========================
    def toJSON(self):
        item = model_to_dict(self)

        item['cueanexo'] = self.cueanexo
        item['mes'] = self.mes
        item['anio'] = self.anio

        item['servicio'] = self.servicio.nom_servicio if self.servicio else ''
        item['turnos'] = self.turnos.nom_turno if self.turnos else ''
        item['instalacion'] = self.instalacion

        item['total'] = self.total

        return item


class InformePedagogico(models.Model):
    cueanexo = models.CharField(max_length=9, verbose_name='Cueanexo')
    mes = models.CharField(max_length=25, choices=MESES_CHOICES, verbose_name='Mes')
    anio = models.IntegerField(validators=[MinValueValidator(2025)], verbose_name='Año')

    servicio = models.ForeignKey(
        ServiciosMatBiblio,
        on_delete=models.CASCADE,
        verbose_name='Servicio'
    )

    varones = models.PositiveIntegerField(verbose_name='Varones')
    total = models.PositiveIntegerField(verbose_name='Total')

    class Meta:
        verbose_name = 'Informe_Pedagogico'
        verbose_name_plural = 'Informes_Pedagogicos'
        db_table = 'informe_pedagogico'

        # 🔥 EVITA DUPLICADOS EN BASE DE DATOS
        constraints = [
            models.UniqueConstraint(
                fields=[
                    'cueanexo',
                    'mes',
                    'anio',
                    'servicio'
                ],
                name='unique_informe_pedagogico'
            )
        ]

    def __str__(self):
        return f"{self.cueanexo} - {self.servicio}"

    # =========================
    # 🔥 VALIDACIONES
    # =========================
    def clean(self):
        super().clean()

        # 🔴 VALIDACIÓN 1: total >= varones
        if self.varones is not None and self.total is not None:
            if self.total < self.varones:
                raise ValidationError({
                    'total': 'El Total no puede ser menor que Varones.'
                })

        # 🔴 VALIDACIÓN 2: DUPLICADO
        if all([
            self.cueanexo,
            self.mes,
            self.anio,
            self.servicio
        ]):

            qs = InformePedagogico.objects.filter(
                cueanexo=self.cueanexo,
                mes=self.mes,
                anio=self.anio,
                servicio=self.servicio
            )

            # excluir si es edición
            if self.pk:
                qs = qs.exclude(pk=self.pk)

            if qs.exists():
                raise ValidationError({
                    '__all__': '⚠️ Ya existe un Informe Pedagógico para este CUE, Mes, Año y Servicio.'
                })

    # =========================
    # 🔥 GUARDA SEGURA
    # =========================
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    # =========================
    # 🔥 JSON PARA FRONTEND
    # =========================
    def toJSON(self):
        item = model_to_dict(self)

        item['cueanexo'] = self.cueanexo
        item['mes'] = self.mes
        item['anio'] = self.anio

        item['servicio'] = self.servicio.nom_servicio if self.servicio else ''

        item['varones'] = self.varones
        item['total'] = self.total

        return item

class AsistenciaUsuarios(models.Model):
    cueanexo = models.CharField(max_length=9, verbose_name='Cueanexo')
    mes = models.CharField(max_length=25, choices=MESES_CHOICES, verbose_name='Mes')
    anio = models.IntegerField(validators=[MinValueValidator(2025)], verbose_name='Año')

    nivel = models.CharField(max_length=50, choices=NIVELES_CHOICES, verbose_name='Nivel')
    usuario = models.CharField(max_length=50, choices=USUARIOS_CHOICES, verbose_name='Usuarios')

    varones = models.IntegerField(verbose_name='Varones')
    total = models.IntegerField(verbose_name='Total')

    class Meta:
        verbose_name = 'Asistencia_Usuario'
        verbose_name_plural = 'Asistencias_Usuarios'
        db_table = 'asistencia_usuario'

        # 🔥 EVITA DUPLICADOS EN BASE DE DATOS
        constraints = [
            models.UniqueConstraint(
                fields=[
                    'cueanexo',
                    'mes',
                    'anio',
                    'nivel',
                    'usuario'
                ],
                name='unique_asistencia_usuarios'
            )
        ]

    def __str__(self):
        return f"{self.cueanexo} - {self.nivel}: {self.usuario}"

    # =========================
    # 🔥 VALIDACIONES
    # =========================
    def clean(self):
        super().clean()

        # 🔴 VALIDACIÓN 1: total >= varones
        if self.varones is not None and self.total is not None:
            if self.total < self.varones:
                raise ValidationError({
                    'total': 'El Total no puede ser menor que Varones.'
                })

        # 🔴 VALIDACIÓN 2: DUPLICADO
        if all([
            self.cueanexo,
            self.mes,
            self.anio,
            self.nivel,
            self.usuario
        ]):

            qs = AsistenciaUsuarios.objects.filter(
                cueanexo=self.cueanexo,
                mes=self.mes,
                anio=self.anio,
                nivel=self.nivel,
                usuario=self.usuario
            )

            # excluir si es edición
            if self.pk:
                qs = qs.exclude(pk=self.pk)

            if qs.exists():
                raise ValidationError({
                    '__all__': '⚠️ Ya existe un registro de Asistencia para este CUE, Mes, Año, Nivel y Usuario.'
                })

    # =========================
    # 🔥 GUARDA SEGURA
    # =========================
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    # =========================
    # 🔥 JSON PARA FRONTEND
    # =========================
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
    cueanexo = models.CharField(max_length=9, verbose_name='Cueanexo')
    mes = models.CharField(max_length=25, choices=MESES_CHOICES, verbose_name='Mes')
    anio = models.IntegerField(validators=[MinValueValidator(2025)], verbose_name='Año')

    escuela = models.CharField(max_length=255, verbose_name='Escuela')

    matricula = models.PositiveIntegerField(verbose_name='Matricula')
    docentes = models.PositiveIntegerField(verbose_name='Docentes')
    matricdisc = models.PositiveIntegerField(verbose_name='Discapacidad')
    etnia = models.PositiveIntegerField(verbose_name='Etnia')

    class Meta:
        verbose_name = 'Institucion_Servicio'
        verbose_name_plural = 'Instituciones_Servicios'
        db_table = 'institucion_servicio'

        # 🔥 EVITA DUPLICADOS A NIVEL BASE DE DATOS
        constraints = [
            models.UniqueConstraint(
                fields=[
                    'cueanexo',
                    'mes',
                    'anio',
                    'escuela'
                ],
                name='unique_institucion_servicio'
            )
        ]

    def __str__(self):
        return f"{self.escuela}"

    # =========================
    # 🔥 VALIDACIONES
    # =========================
    def clean(self):
        super().clean()

        # 🔴 VALIDACIÓN 1: valores no negativos
        numeric_fields = {
            'matricula': self.matricula,
            'docentes': self.docentes,
            'matricdisc': self.matricdisc,
            'etnia': self.etnia,
        }

        for field, value in numeric_fields.items():
            if value is not None and value < 0:
                raise ValidationError({
                    field: 'Este campo no puede ser negativo.'
                })

        # 🔴 VALIDACIÓN 2: duplicados
        if all([
            self.cueanexo,
            self.mes,
            self.anio,
            self.escuela
        ]):

            qs = InstitucionesPrestaServicios.objects.filter(
                cueanexo=self.cueanexo,
                mes=self.mes,
                anio=self.anio,
                escuela=self.escuela
            )

            # excluir si es edición
            if self.pk:
                qs = qs.exclude(pk=self.pk)

            if qs.exists():
                raise ValidationError({
                    '__all__': '⚠️ Ya existe esta Institución registrada para este CUE, Mes y Año.'
                })

    # =========================
    # 🔥 GUARDA SEGURA
    # =========================
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    # =========================
    # 🔥 JSON PARA FRONTEND
    # =========================
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
    cueanexo = models.CharField(max_length=9, verbose_name='Cueanexo')
    mes = models.CharField(max_length=25, choices=MESES_CHOICES, verbose_name='Mes')
    anio = models.IntegerField(validators=[MinValueValidator(2025)], verbose_name='Año')

    material = models.ForeignKey(
        TipoMaterialBiblio,
        on_delete=models.CASCADE,
        verbose_name='Material'
    )

    procesos = models.CharField(
        max_length=255,
        choices=PROCESOS_CHOICES,
        verbose_name='Procesos'
    )

    total = models.PositiveIntegerField(verbose_name='Total')

    class Meta:
        verbose_name = 'Proceso_Tecnico'
        verbose_name_plural = 'Procesos_Tecnicos'
        db_table = 'proceso_tecnico'

        # 🔥 EVITA DUPLICADOS A NIVEL BASE DE DATOS
        constraints = [
            models.UniqueConstraint(
                fields=[
                    'cueanexo',
                    'mes',
                    'anio',
                    'material',
                    'procesos'
                ],
                name='unique_procesos_tecnicos'
            )
        ]

    def __str__(self):
        return f"{self.cueanexo} - {self.material}: {self.procesos}"

    # =========================
    # 🔥 VALIDACIONES
    # =========================
    def clean(self):
        super().clean()

        # 🔴 VALIDACIÓN 1: total no negativo
        if self.total is not None and self.total < 0:
            raise ValidationError({
                'total': 'El total no puede ser negativo.'
            })

        # 🔴 VALIDACIÓN 2: duplicados
        if all([
            self.cueanexo,
            self.mes,
            self.anio,
            self.material,
            self.procesos
        ]):

            qs = ProcesosTecnicos.objects.filter(
                cueanexo=self.cueanexo,
                mes=self.mes,
                anio=self.anio,
                material=self.material,
                procesos=self.procesos
            )

            # excluir si es edición
            if self.pk:
                qs = qs.exclude(pk=self.pk)

            if qs.exists():
                raise ValidationError({
                    '__all__': '⚠️ Ya existe este Proceso Técnico para este CUE, Mes, Año, Material y Proceso.'
                })

    # =========================
    # 🔥 GUARDA SEGURA
    # =========================
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    # =========================
    # 🔥 JSON PARA FRONTEND
    # =========================
    def toJSON(self):
        item = model_to_dict(self)

        item['cueanexo'] = self.cueanexo
        item['mes'] = self.mes
        item['anio'] = self.anio

        item['material'] = self.material.nom_material if self.material else ''
        item['procesos'] = self.procesos

        item['total'] = self.total

        return item


class Aguapey(models.Model):
    cueanexo = models.CharField(max_length=9, verbose_name='Cueanexo')
    mes = models.CharField(max_length=25, choices=MESES_CHOICES, verbose_name='Mes')
    anio = models.IntegerField(validators=[MinValueValidator(2025)], verbose_name='Año')

    total_mes = models.PositiveIntegerField(verbose_name='Total Mes')
    total_base = models.PositiveIntegerField(verbose_name='Total Base')
    total_usuarios = models.PositiveIntegerField(verbose_name='Total Usuarios')

    observaciones = models.TextField(max_length=255, verbose_name='Observaciones')

    class Meta:
        verbose_name = 'Aguapey'
        verbose_name_plural = 'Aguapeys'
        db_table = 'aguapey'

        # 🔥 EVITA DUPLICADOS EN BASE DE DATOS
        constraints = [
            models.UniqueConstraint(
                fields=[
                    'cueanexo',
                    'mes',
                    'anio'
                ],
                name='unique_aguapey'
            )
        ]

    def __str__(self):
        return f"{self.cueanexo} - {self.total_mes}: {self.total_base}"

    # =========================
    # 🔥 VALIDACIONES
    # =========================
    def clean(self):
        super().clean()

        # 🔴 VALIDACIÓN 1: valores no negativos
        numeric_fields = {
            'total_mes': self.total_mes,
            'total_base': self.total_base,
            'total_usuarios': self.total_usuarios,
        }

        for field, value in numeric_fields.items():
            if value is not None and value < 0:
                raise ValidationError({
                    field: 'Este campo no puede ser negativo.'
                })

        # 🔴 VALIDACIÓN 2: coherencia lógica (opcional pero útil)
        if (
            self.total_usuarios is not None and
            self.total_base is not None and
            self.total_usuarios > self.total_base
        ):
            raise ValidationError({
                'total_usuarios': 'Los usuarios no pueden superar el total base.'
            })

        # 🔴 VALIDACIÓN 3: DUPLICADOS
        if all([
            self.cueanexo,
            self.mes,
            self.anio
        ]):

            qs = Aguapey.objects.filter(
                cueanexo=self.cueanexo,
                mes=self.mes,
                anio=self.anio
            )

            # excluir si es edición
            if self.pk:
                qs = qs.exclude(pk=self.pk)

            if qs.exists():
                raise ValidationError({
                    '__all__': '⚠️ Ya existe un registro de Aguapey para este CUE, Mes y Año.'
                })

    # =========================
    # 🔥 GUARDA SEGURA
    # =========================
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    # =========================
    # 🔥 JSON PARA FRONTEND
    # =========================
    def toJSON(self):
        item = model_to_dict(self)

        item['cueanexo'] = self.cueanexo
        item['mes'] = self.mes
        item['anio'] = self.anio

        item['total_mes'] = self.total_mes
        item['total_base'] = self.total_base
        item['total_usuarios'] = self.total_usuarios

        item['observaciones'] = self.observaciones

        return item


class DestinoFondos(models.Model):
    cod_fondo=models.IntegerField(verbose_name='Codigo')
    nom_fondo=models.CharField(max_length=255, verbose_name='Nombre')
    
    def __str__(self):
        return self.nom_fondo
    
    class Meta:
        verbose_name='DestinoFondo'
        verbose_name_plural='DestinosFondos'
        db_table='destino_fondos'
    
    def toJSON(self):
        item = model_to_dict(self)
        item['cod_fondo'] = self.cod_fondo
        item['nom_fondo'] = self.nom_fondo
        return item



class RegistroDestinoFondos(models.Model):
    cueanexo = models.CharField(max_length=9, verbose_name='Cueanexo')
    mes = models.CharField(max_length=25, verbose_name='Mes')
    anio = models.IntegerField(verbose_name='Año')

    destino = models.ForeignKey(
        DestinoFondos,
        on_delete=models.CASCADE,
        verbose_name='Destino'
    )

    descripcion = models.CharField(max_length=255, verbose_name='Descripcion')
    cantidad = models.PositiveIntegerField(verbose_name='Cantidad')

    class Meta:
        verbose_name = 'RegistroDestinoFondo'
        verbose_name_plural = 'RegistroDestinosFondos'
        db_table = 'registro_destino_fondos'

        # 🔥 EVITA DUPLICADOS EN BASE DE DATOS
        constraints = [
            models.UniqueConstraint(
                fields=[
                    'cueanexo',
                    'mes',
                    'anio',
                    'destino'
                ],
                name='unique_registro_destino_fondos'
            )
        ]

    def __str__(self):
        return f"{self.cueanexo} {self.mes} {self.anio} - {self.destino}"

    # =========================
    # 🔥 VALIDACIONES
    # =========================
    def clean(self):
        super().clean()

        # 🔴 VALIDACIÓN 1: cantidad no negativa
        if self.cantidad is not None and self.cantidad < 0:
            raise ValidationError({
                'cantidad': 'La cantidad no puede ser negativa.'
            })

        # 🔴 VALIDACIÓN 2: duplicados
        if all([
            self.cueanexo,
            self.mes,
            self.anio,
            self.destino
        ]):

            qs = RegistroDestinoFondos.objects.filter(
                cueanexo=self.cueanexo,
                mes=self.mes,
                anio=self.anio,
                destino=self.destino
            )

            # excluir si es edición
            if self.pk:
                qs = qs.exclude(pk=self.pk)

            if qs.exists():
                raise ValidationError({
                    '__all__': '⚠️ Ya existe un registro para este CUE, Mes, Año y Destino.'
                })

    # =========================
    # 🔥 GUARDA SEGURA
    # =========================
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    # =========================
    # 🔥 JSON PARA FRONTEND
    # =========================
    def toJSON(self):
        item = model_to_dict(self)

        item['cueanexo'] = self.cueanexo
        item['mes'] = self.mes
        item['anio'] = self.anio

        item['destino'] = self.destino.nom_fondo if self.destino else ''
        item['descripcion'] = self.descripcion
        item['cantidad'] = self.cantidad

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
    
    def is_editable(self):
        return self.estado != "ENVIADO"
    
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



class NoDocentesMensual(models.Model):
    id = models.IntegerField(primary_key=True)
    cueanexo = models.CharField(max_length=9)
    cuof = models.CharField(max_length=10)
    cuof_anexo = models.CharField(max_length=10, null=True, blank=True)
    ptaid = models.CharField(max_length=20)
    apellidos = models.CharField(max_length=100)
    nombres = models.CharField(max_length=100)
    ndoc = models.CharField(max_length=15)
    cuil = models.CharField(max_length=15)
    f_nac = models.DateField(null=True, blank=True)
    denom_cargo = models.CharField(max_length=100)
    categ = models.CharField(max_length=50)
    gpo = models.CharField(max_length=50)
    apart = models.CharField(max_length=50)
    f_desde = models.DateField(null=True, blank=True)
    f_hasta = models.DateField(null=True, blank=True)
    regional = models.CharField(max_length=100)
    localidad = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'nodocentes_mensual_view'
        verbose_name = "No_Docente_Mensual"
        verbose_name_plural = "No_Docentes_Mensuales"

    def __str__(self):
        return f"{self.apellidos}, {self.nombres} - {self.denom_cargo}"
    
    def toJSON(self):
        item = model_to_dict(self)
        item['id'] = self.id 
        item['cueanexo'] = self.cueanexo
        item['cuof'] = self.cuof
        item['cuof_anexo'] = self.cuof_anexo
        item['ptaid'] = self.ptaid
        item['apellidos'] = self.apellidos
        item['nombres'] = self.nombres
        item['ndoc'] = self.ndoc
        item['cuil'] = self.cuil
        item['f_nac'] = self.f_nac
        item['denom_cargo'] = self.denom_cargo
        item['categ'] = self.categ
        item['gpo'] = self.gpo
        item['apart'] = self.apart
        item['f_desde'] = self.f_desde
        item['f_hasta'] = self.f_hasta
        item['regional'] = self.regional
        item['localidad'] = self.localidad
        return item


    
class DocentePonMensual(models.Model):
    id = models.IntegerField(primary_key=True)  # Generado por row_number() en la vista
    cueanexo = models.CharField(max_length=50)
    cuof = models.CharField(max_length=50)
    cuof_anexo = models.CharField(max_length=50)
    ptaid = models.CharField(max_length=50)
    apellidos = models.CharField(max_length=100)
    nombres = models.CharField(max_length=100)
    n_doc = models.CharField(max_length=20)
    cuil = models.CharField(max_length=20)
    f_nac = models.DateField()
    sit_rev = models.CharField(max_length=50)
    nivel = models.CharField(max_length=50)
    ceic = models.CharField(max_length=50)
    denom_cargo = models.CharField(max_length=100)
    f_desde = models.DateField()
    f_hasta = models.DateField()
    regional = models.CharField(max_length=100)
    localidad = models.CharField(max_length=100)
    carga_horaria=models.IntegerField()

    class Meta:
        managed = False 
        verbose_name = "Docente_Mensual"
        verbose_name_plural = "Docentes_Mensuales"
        db_table = 'docentespon_mensual_view'

    def __str__(self):
        return f"{self.apellidos} {self.nombres} - {self.denom_cargo}"

    def toJSON(self):
        item = model_to_dict(self)
        item['id'] = self.id
        item['cueanexo'] = self.cueanexo
        item['cuof'] = self.cuof
        item['cuof_anexo'] = self.cuof_anexo
        item['ptaid'] = self.ptaid
        item['apellidos'] = self.apellidos
        item['nombres'] = self.nombres
        item['n_doc'] = self.n_doc
        item['cuil'] = self.cuil
        item['f_nac'] = self.f_nac
        item['sit_rev'] = self.sit_rev
        item['nivel'] = self.nivel
        item['ceic'] = self.ceic
        item['denom_cargo'] = self.denom_cargo
        item['f_desde'] = self.f_desde
        item['f_hasta'] = self.f_hasta
        item['regional'] = self.regional
        item['localidad'] = self.localidad
        item['carga_horaria']=self.carga_horaria
        return item


class FocalLicDocentes(models.Model):    
    ptaid = models.CharField(max_length=9, blank=True, null=True, verbose_name='ptaid')
    cuil = models.CharField(max_length=11, blank=True, null=True, verbose_name='cuil')
    ptatipo = models.CharField(max_length=255, blank=True, null=True, verbose_name='ptatipo')
    lic_desde = models.DateField(blank=True, null=True, verbose_name='lic_desde')
    lic_hasta = models.DateField(blank=True, null=True, verbose_name='lic_hasta')
    hs_cat=models.IntegerField(blank=True, null=True, verbose_name='hs_cat')
    desc_lic = models.CharField(max_length=255, blank=True, null=True, verbose_name='desc_lic')
    lic_hs=models.IntegerField(blank=True,null=True,verbose_name='lic_hs')
    cuof = models.CharField(max_length=7, blank=True, null=True, verbose_name='cuof')
    cuof_anexo = models.CharField(max_length=7, blank=True, null=True, verbose_name='cuof_anexo')
    
    class Meta:
        managed = False 
        verbose_name = "Focal_Lic_Docente"
        verbose_name_plural = "Focales_Lic_Docentes"
        db_table = 'focal_lic_docentes'
    
    def __str__(self):
        return f"{self.cuil} - {self.ptatipo}"
    
    def toJSON(self):
        item = model_to_dict(self)
        item['ptaid'] = self.ptaid
        item['cuil'] = self.cuil
        item['ptatipo'] = self.ptatipo
        item['lic_desde'] = self.lic_desde
        item['lic_hasta'] = self.lic_hasta
        item['hs_cat'] = self.hs_cat
        item['desc_lic'] = self.desc_lic
        item['lic_hs'] = self.lic_hs
        item['cuof'] = self.cuof
        item['cuof_anexo'] = self.cuof_anexo
        return item
    
T_DOC_CHOICES = [
    ('DNI', 'DNI'),
    ('LC', 'LC'),
    ('LE', 'LE'),    
]

SIT_REVISTA_CHOICES = [
    ('TITULAR', 'TITULAR'),
    ('INTERINO', 'INTERINO'),
    ('SUPLENTE', 'SUPLENTE'),
    ('CONTRATADO', 'CONTRATADO'),
]

CARGO_CHOICES = [
    ('BIBLIOTECARIO', 'BIBLIOTECARIO'),
    ('DIRECTOR BIBLIOTECA 1RA', 'DIRECTOR BIBLIOTECA 1RA'),
    ('DIRECTOR BIBLIOTECA 2DA', 'DIRECTOR BIBLIOTECA 2DA'),
    ('DIRECTOR BIBLIOTECA 3RA', 'DIRECTOR BIBLIOTECA 3RA'),
    ('DIRECTOR BIBLIOTECA CENTRAL', 'DIRECTOR BIBLIOTECA CENTRAL'),
    ('VICEDIRECTOR BIBLIOTECA', 'BICEDIRECTOR BIBLIOTECA'),
]

class TiposLicenciasPermisos(models.Model):
    id = models.AutoField(primary_key=True)
    tipo_licencia = models.CharField(max_length=255, verbose_name='Tipo de Licencia')
    
    
    class Meta:
        verbose_name = 'Tipo_Licencia_Permiso'
        verbose_name_plural = 'Tipos_Licencias_Permisos'
        db_table = 'tipos_licencias_permisos'
    
    def __str__(self):
        return self.tipo_licencia
    
    def toJSON(self):
        item = model_to_dict(self)
        item['id'] = self.id
        item['tipo_licencia'] = self.tipo_licencia
        return item

class TiposSituacionLaboral(models.Model):
    id = models.AutoField(primary_key=True)
    tipo_situacion = models.CharField(max_length=255, verbose_name='Tipo de Situación Laboral')
    
    class Meta:
        verbose_name = 'Tipo_Situacion_Laboral'
        verbose_name_plural = 'Tipos_Situaciones_Laborales'
        db_table = 'tipos_situacion_laboral'
    
    def __str__(self):
        return self.tipo_situacion
    
    def toJSON(self):
        item = model_to_dict(self)
        item['id'] = self.id
        item['tipo_situacion'] = self.tipo_situacion
        return item


class BibliotecariosCue(models.Model):
    cueanexo = models.CharField(max_length=9, verbose_name='cueanexo')
    cuil = models.CharField(max_length=11, verbose_name='cuil')

    t_doc = models.CharField(max_length=3, choices=T_DOC_CHOICES, verbose_name='t_doc')
    n_doc = models.CharField(max_length=8, verbose_name='n_doc')

    apellidos = models.CharField(max_length=255, verbose_name='apellidos')
    nombres = models.CharField(max_length=255, verbose_name='nombres')

    f_nac = models.DateField(verbose_name='f_nac')

    cargo = models.CharField(max_length=255, choices=CARGO_CHOICES, verbose_name='cargo')
    situacion_revista = models.CharField(max_length=255, choices=SIT_REVISTA_CHOICES, verbose_name='situacion_revista')

    f_ingreso = models.DateField(verbose_name='f_ingreso')
    f_hasta = models.DateField(default=date(2039, 12, 31), verbose_name='f_hasta')

    turno = models.ForeignKey(turno, on_delete=models.CASCADE, verbose_name='turno')

    cuof = models.CharField(max_length=4, blank=True, null=True, verbose_name='cuof')
    cuof_anexo = models.CharField(max_length=4, blank=True, null=True, verbose_name='cuof_anexo')

    mes = models.CharField(max_length=25, choices=MESES_CHOICES, verbose_name='mes')
    anio = models.IntegerField(validators=[MinValueValidator(2025)], verbose_name='anio')

    licencia_permiso = models.ForeignKey(
        TiposLicenciasPermisos,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        verbose_name='Licencia_Permiso'
    )

    f_desde_lic = models.DateField(blank=True, null=True)
    f_hasta_lic = models.DateField(blank=True, null=True)

    observaciones = models.TextField(max_length=255, blank=True, null=True)

    situacion_laboral = models.ForeignKey(
        TiposSituacionLaboral,
        on_delete=models.CASCADE,
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = "Bibliotecario_Cue"
        verbose_name_plural = "Bibliotecarios_Cues"
        db_table = 'bibliotecarios_cue'

        # 🔥 EVITA DUPLICADOS CRÍTICOS
        constraints = [
            models.UniqueConstraint(
                fields=[
                    'cueanexo',
                    'n_doc',
                    'mes',
                    'anio'
                ],
                name='unique_bibliotecario_cue'
            )
        ]

    def __str__(self):
        return f"{self.n_doc} - {self.apellidos}, {self.nombres}"

    # =========================
    # 🔥 VALIDACIONES
    # =========================
    def clean(self):
        super().clean()

        # 🔴 VALIDACIÓN 1: fechas coherentes
        if self.f_ingreso and self.f_hasta:
            if self.f_ingreso > self.f_hasta:
                raise ValidationError({
                    'f_hasta': 'La fecha hasta no puede ser menor que la fecha de ingreso.'
                })

        if self.f_desde_lic and self.f_hasta_lic:
            if self.f_desde_lic > self.f_hasta_lic:
                raise ValidationError({
                    'f_hasta_lic': 'La fecha hasta de licencia no puede ser menor que la fecha desde.'
                })

        # 🔴 VALIDACIÓN 2: duplicados (REGISTRO PERSONAL POR PERIODO)
        if all([
            self.cueanexo,
            self.n_doc,
            self.mes,
            self.anio
        ]):

            qs = BibliotecariosCue.objects.filter(
                cueanexo=self.cueanexo,
                n_doc=self.n_doc,
                mes=self.mes,
                anio=self.anio
            )

            if self.pk:
                qs = qs.exclude(pk=self.pk)

            if qs.exists():
                raise ValidationError({
                    '__all__': '⚠️ Ya existe este bibliotecario registrado para este CUE, Mes y Año.'
                })

    # =========================
    # 🔥 GUARDA SEGURA
    # =========================
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    # =========================
    # 🔥 JSON PARA FRONTEND
    # =========================
    def toJSON(self):
        item = model_to_dict(self)

        item['cueanexo'] = self.cueanexo
        item['cuil'] = self.cuil

        item['t_doc'] = self.t_doc
        item['n_doc'] = self.n_doc

        item['apellidos'] = self.apellidos
        item['nombres'] = self.nombres

        item['f_nac'] = self.f_nac
        item['cargo'] = self.cargo
        item['situacion_revista'] = self.situacion_revista

        item['f_ingreso'] = self.f_ingreso
        item['f_hasta'] = self.f_hasta

        item['turno'] = self.turno.nom_turno if self.turno else ''

        item['cuof'] = self.cuof
        item['cuof_anexo'] = self.cuof_anexo

        item['mes'] = self.mes
        item['anio'] = self.anio

        item['licencia_permiso'] = self.licencia_permiso.tipo_licencia if self.licencia_permiso else None

        item['f_desde_lic'] = self.f_desde_lic
        item['f_hasta_lic'] = self.f_hasta_lic

        item['observaciones'] = self.observaciones

        item['situacion_laboral'] = (
            self.situacion_laboral.tipo_situacion
            if self.situacion_laboral else None
        )

        return item


################################
#           RESUMENES          #
################################
class VMaterialBiblioDynamic(models.Model):
    id = models.IntegerField(primary_key=True)  # 👈 CLAVE

    cueanexo = models.CharField(max_length=20)
    mes = models.CharField(max_length=20)
    anio = models.IntegerField()

    cod_servicio = models.IntegerField()
    nom_servicio = models.CharField(max_length=255)
    nom_turno = models.CharField(max_length=255)

    materiales = models.JSONField()
    total_general = models.IntegerField()

    class Meta:
        managed = False
        db_table = "pem.v_material_bibliografico_resumen"

    


class VServicioReferenciaResumen(models.Model):
    cueanexo = models.CharField(max_length=20)
    mes = models.CharField(max_length=20)
    anio = models.IntegerField()

    cod_servicio = models.IntegerField()
    nom_servicio = models.CharField(max_length=255)
    nom_turno = models.CharField(max_length=255)

    total_v = models.IntegerField()
    total_t = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'v_material_biblio_dynamic'


class VServicioReferenciaVirtualResumen(models.Model):
    cueanexo = models.CharField(max_length=20)
    mes = models.CharField(max_length=20)
    anio = models.IntegerField()

    cod_servicio = models.IntegerField()
    nom_servicio = models.CharField(max_length=255)
    nom_turno = models.CharField(max_length=255)

    total_v = models.IntegerField()
    total_t = models.IntegerField()

    class Meta:
        managed = False
        db_table = "v_servicio_referencia_virtual_resumen"
    

class InformePedagogicoResumen(models.Model):
    cueanexo = models.CharField(max_length=20)
    mes = models.CharField(max_length=20)
    anio = models.IntegerField()

    nom_servicio = models.CharField(max_length=255)

    varones_total = models.IntegerField()
    total_total = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'v_informe_pedagogico_resumen'


class AsistenciaUsuariosResumen(models.Model):
    cueanexo = models.CharField(max_length=20)
    mes = models.CharField(max_length=20)
    anio = models.IntegerField()
    nivel = models.CharField(max_length=100)
    usuario = models.CharField(max_length=50)
    total = models.PositiveIntegerField()
    varones = models.PositiveIntegerField()

    class Meta:
        managed = False
        db_table = 'pem.v_asistencia_usuarios_resumen'


class InstitucionesServiciosResumen(models.Model):
    cueanexo = models.CharField(max_length=20)
    mes = models.CharField(max_length=20)
    anio = models.IntegerField()
    escuela = models.CharField(max_length=255)
    matricula = models.IntegerField()
    docentes = models.IntegerField()
    matricdisc = models.IntegerField()
    etnia = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'pem.v_instituciones_servicios'


class ProcesosTecnicosResumen(models.Model):
    cueanexo = models.CharField(max_length=20)
    mes = models.CharField(max_length=20)
    anio = models.IntegerField()
    nom_material = models.CharField(max_length=150)
    procesos = models.CharField(max_length=150)
    total = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'pem.v_procesos_tecnicos_resumen'