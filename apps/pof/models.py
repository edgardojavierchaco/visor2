from django.core.validators import RegexValidator
from django.db import models
from django.forms import model_to_dict
from django.core.exceptions import ValidationError

# Validador para solo dígitos
only_digits = RegexValidator(regex=r'^\d+$', message='Este campo debe contener solo dígitos.')

class Categoria(models.Model):
    id=models.AutoField(primary_key=True, verbose_name='id')
    denom_categoria=models.CharField(max_length=50, blank=False, null=False, verbose_name='denominacion_categoria')
    
    class Meta:
        verbose_name='Categoria'
        verbose_name_plural='Categorias'
        db_table='Categoria_pof'
    
    def __str__(self):
        return self.denom_categoria
    
    def toJSON(self):
        item=model_to_dict(self)
        item['denom_categoria']=self.denom_categoria
        return item


class Jornada(models.Model):
    id=models.AutoField(primary_key=True, verbose_name='id')
    denom_jornada=models.CharField(max_length=50, blank=False, null=False, verbose_name='denominacion_jornada')
    
    class Meta:
        verbose_name='Jornada'
        verbose_name_plural='Jornadas'
        db_table='Jornadas_pof'
    
    def __str__(self):
        return self.denom_jornada
    
    def toJSON(self):
        item=model_to_dict(self)
        item['denom_jornada']=self.denom_jornada
        return item


class Ambito(models.Model):
    id=models.AutoField(primary_key=True, verbose_name='id')
    denom_ambito=models.CharField(max_length=50, blank=False, null=False, verbose_name='denominacion_ambito')
    
    class Meta:
        verbose_name='Ambito'
        verbose_name_plural='Ambitos'
        db_table='Ambito_pof'
    
    def __str__(self):
        return self.denom_ambito
    
    def toJSON(self):
        item=model_to_dict(self)
        item['denom_ambito']=self.denom_ambito
        return item


class Sector(models.Model):
    id=models.AutoField(primary_key=True, verbose_name='id')
    denom_sector=models.CharField(max_length=50, blank=False, null=False, verbose_name='denominacion_sector')
    
    class Meta:
        verbose_name='Sector'
        verbose_name_plural='Sectores'
        db_table='Sector_pof'
    
    def __str__(self):
        return self.denom_sector
    
    def toJSON(self):
        item=model_to_dict(self)
        item['denom_sector']=self.denom_sector
        return item


class Zona(models.Model):
    id=models.AutoField(primary_key=True, verbose_name='id')
    denom_zona=models.CharField(max_length=255, blank=False, null=False, verbose_name='denominacion_zona')
    
    class Meta:
        verbose_name='Zona'
        verbose_name_plural='Zonas'
        db_table='Zonas_pof'
    
    def __str__(self):
        return self.denom_zona
    
    def toJSON(self):
        item=model_to_dict(self)
        item['denom_zona']=self.denom_zona
        return item


class Nivel(models.Model):
    id=models.AutoField(primary_key=True, verbose_name='id')
    denom_nivel=models.CharField(max_length=50, blank=False, null=False, verbose_name='denominacion_nivel')
    
    class Meta:
        verbose_name='Nivel'
        verbose_name_plural='Niveles'
        db_table='Nivel_pof'
    
    def __str__(self):
        return self.denom_nivel
    
    def toJSON(self):
        item=model_to_dict(self)
        item['denom_nivel']=self.denom_nivel
        return item

class CargosHoras(models.Model):
    id=models.AutoField(primary_key=True, verbose_name='id')
    nivel=models.ForeignKey(Nivel, on_delete=models.CASCADE, verbose_name='nivel')
    ceic=models.IntegerField(default=0, blank=False, null=False, verbose_name='ceic')
    denom_cargoshoras=models.CharField(max_length=255, blank=False, null=False, verbose_name='denominacion_cargoshoras')
    estado=models.BooleanField(verbose_name='estado')
    puntos=models.IntegerField(verbose_name='puntos')
    
    class Meta:
        verbose_name='CargoHoras'
        verbose_name_plural='CargosHoras'
        db_table='CargosHoras_pof'
    
    def __str__(self):
        return f"{self.ceic}-{self.denom_cargoshoras}"
    
    def toJSON(self):
        item=model_to_dict(self)
        item['nivel']=self.nivel.denom_nivel
        item['ceic']=self.ceic
        item['denom_cargoshoras']=self.denom_cargoshoras
        item['estado']=self.estado
        item['puntos']=self.puntos
        return item
    
    
class Modalidad(models.Model):
    id=models.AutoField(primary_key=True, verbose_name='id')
    denom_modalidad=models.CharField(max_length=50, blank=False, null=False, verbose_name='denominacion_modalidad')
    
    class Meta:
        verbose_name='Modalidad'
        verbose_name_plural='Modalidades'
        db_table='Modalidad_pof'
    
    def __str__(self):
        return self.denom_modalidad
    
    def toJSON(self):
        item=model_to_dict(self)
        item['denom_modalidad']=self.denom_modalidad
        return item


class Departamento(models.Model):
    denom_departamento = models.CharField(max_length=255, verbose_name='denominacion_departamento')

    class Meta:
        verbose_name='Departamento'
        verbose_name_plural='Departamentos'
        db_table='Dptos_pof'
        
    def __str__(self):
        return self.denom_departamento
    
    def toJSON(self):
        item=model_to_dict(self)
        item['denom_departamento']=self.denom_departamento
        return item
    

class DepartamentoLocalidad(models.Model):
    id=models.AutoField(primary_key=True, verbose_name='id')
    denom_localidad=models.CharField(max_length=255, blank=False, null=False, verbose_name='denominacion_localidad')
    departamento=models.ForeignKey(Departamento, on_delete=models.CASCADE, related_name='localidades')
        
    class Meta:
        verbose_name='DepartamentoLocalidad'
        verbose_name_plural='DepartamentosLocalidades'
        db_table='DptosLoc_pof'
    
    def __str__(self):
        return self.denom_localidad
    
    def toJSON(self):
        item=model_to_dict(self)
        item['denom_localidad']=self.denom_localidad
        item['departamento']=self.departamento
        return item


class Regional(models.Model):
    id=models.AutoField(primary_key=True, verbose_name='id')
    denom_regional=models.CharField(max_length=50, blank=False, null=False, verbose_name='denominacion_regional')
        
    class Meta:
        verbose_name='Regional'
        verbose_name_plural='Regionales'
        db_table='Regionales_pof'
    
    def __str__(self):
        return self.denom_regional
    
    def toJSON(self):
        item=model_to_dict(self)
        item['denom_regional']=self.denom_regional
        return item
    
    
class UnidadServicio(models.Model):
    cue=models.CharField(max_length=7, blank=False, null=False, validators=[only_digits],verbose_name='Cue')
    anexo=models.CharField(max_length=2, blank=False, null=False, validators=[only_digits],verbose_name='Anexo')
    cueanexo=models.CharField(max_length=9, verbose_name='Cueanexo')
    cuof=models.IntegerField(default=0,verbose_name='Cuof')
    cuof_anexo=models.IntegerField(default=0, verbose_name='Cuof_Anexo')
    cui = models.CharField(max_length=9, blank=False, null=False, validators=[only_digits], verbose_name='Cui')
    nivel=models.ForeignKey(Nivel, on_delete=models.CASCADE, verbose_name='Nivel')   
    modalidad=models.ForeignKey(Modalidad, on_delete=models.CASCADE, verbose_name='Modalidad') 
    sector=models.ForeignKey(Sector, on_delete=models.CASCADE, verbose_name='Sector')
    ambito=models.ForeignKey(Ambito, on_delete=models.CASCADE, verbose_name='Ambito')
    zona=models.ForeignKey(Zona, on_delete=models.CASCADE, verbose_name='Zona')
    categoria=models.ForeignKey(Categoria, on_delete=models.CASCADE, verbose_name='Categoria')
    jornada=models.ForeignKey(Jornada, on_delete=models.CASCADE, verbose_name='Jornada')
    region=models.ForeignKey(Regional, on_delete=models.CASCADE, verbose_name='Regional')
    nom_est=models.CharField(max_length=255, verbose_name='Nombre')
    ubicacion=models.CharField(max_length=255, blank=False, null=False, verbose_name='Ubicacion')
    nro=models.IntegerField(default=0, blank=False, null=False, verbose_name='Nro')
    departamento=models.ForeignKey(Departamento, on_delete=models.CASCADE, verbose_name='Departamento')
    localidad=models.ForeignKey(DepartamentoLocalidad, on_delete=models.CASCADE, verbose_name='Localidad')
    
    class Meta:       
        verbose_name='Unidad_Servicio'
        verbose_name_plural='Unidades_Servicios'
        db_table='UnidadesServicio_pof'
    
    def __str__(self):
        return f"{self.cue}-{self.nom_est}"   
    
    
    def toJSON(self):
        item=model_to_dict(self)
        item['cue']=self.cue
        item['anexo']=self.anexo
        item['cueanexo']=self.cueanexo
        item['cuof']=self.cuof
        item['cuof_anexo']=self.cuof_anexo
        item['cui']=self.cui
        item['nivel']=self.nivel.denom_nivel
        item['modalidad']=self.modalidad.denom_modalidad
        item['sector']=self.sector.denom_sector
        item['ambito']=self.ambito.denom_ambito
        item['zona']=self.zona.denom_zona
        item['categoria']=self.categoria.denom_categoria
        item['jornada']=self.jornada.denom_jornada
        item['region']=self.region.denom_regional
        item['nom_est']=self.nom_est
        item['ubicacion']=self.ubicacion
        item['nro']=self.nro
        item['departamento']=self.departamento.denom_departamento
        item['localidad']=self.localidad.denom_localidad
        return item
    
    def save(self, *args, **kwargs):
        self.full_clean()
        self.cueanexo=f"{self.cue}{self.anexo}"
        # Convertir nom_est y ubicacion a mayúsculas antes de guardar
        self.nom_est = self.nom_est.upper()
        self.ubicacion = self.ubicacion.upper()
        super(UnidadServicio, self).save(*args, **kwargs)
    
class AsignacionPof(models.Model):
    unidad = models.ForeignKey(UnidadServicio, on_delete=models.CASCADE, verbose_name='Unidad_Servicio')
    cant_cargos = models.IntegerField(default=0, verbose_name='Cantidad_Cargos')
    cant_horas=models.IntegerField(default=0, verbose_name='Cantidad_Horas')
    
    def toJSON(self):
        item = model_to_dict(self)
        item['unidad'] = f"{self.unidad.cueanexo} {self.unidad.nom_est}"
        item['cant_cargos'] = self.cant_cargos
        item['cant_horas'] = self.cant_horas
        item['det'] = [i.toJSON() for i in self.detalleasignacionpof_set.all()]
        return item
    
    class Meta:
        verbose_name = 'Asignacion'
        verbose_name_plural = 'Asignaciones'
        ordering = ['unidad']
        db_table='AsignacionPof'
    

class DetalleAsignacionPof(models.Model):
    asignacion=models.ForeignKey(AsignacionPof, on_delete=models.CASCADE, verbose_name='Asignacion')
    cargos=models.ForeignKey(CargosHoras,on_delete=models.CASCADE, verbose_name='Cargos')
    cant_car=models.IntegerField(default=0, blank=False, null=False, verbose_name='Cant_cargos')
    cant_hs=models.IntegerField(default=0, blank=False, null=False, verbose_name='Cant_horas')
    
    def __str__(self):
        return f"{self.cargos.ceic} {self.cargos.denom_cargoshoras}"
    
    def toJSON(self):
        item = model_to_dict(self)
        item['asignacion_id'] = self.asignacion.id
        item['cargos'] = self.cargos.denom_cargoshoras
        item['cant_car'] = self.cant_car
        item['cant_hs'] = self.cant_hs
        return item
    
    class Meta:
        verbose_name='Detalle_Unidad_Cargo'
        verbose_name_plural='Detalles_Unidades_Cargos'
        ordering=['cargos']
        db_table='Detalle_Asignacion_Pof'


