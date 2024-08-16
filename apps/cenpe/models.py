from django.db import models
from apps.usuarios.models import UsuariosVisualizador

class CeicPuntos(models.Model):
    nivel = models.CharField(max_length=255, verbose_name='Nivel')
    ceic_id = models.IntegerField(primary_key=True, verbose_name='ciec_id')
    descripcion_ceic = models.CharField(max_length=255, verbose_name='Descripción Ceic')
    estado = models.BooleanField(verbose_name='Estado')
    puntos = models.IntegerField(verbose_name='Puntos')

    class Meta:
        db_table = 'ceic_puntos'
        managed = False  

    def __str__(self):
        return f'{self.descripcion_ceic} ({self.nivel})'
    

class documento_tipo(models.Model):
    c_tipo = models.IntegerField(primary_key=True, verbose_name='c_tipo')
    descripcion_doc = models.CharField(max_length=255, verbose_name='Descripción Doc')
    
    class Meta:
        db_table='documento_tipo'
        managed=False
        
    def __str__(self):
        return self.descripcion_doc
    

class grado_tipo(models.Model):
    c_grado = models.IntegerField(primary_key=True, verbose_name='c_grado')
    descripcion_grado = models.CharField(max_length=255, verbose_name='Descripción Grado')
    
    class Meta:
        db_table='grado_tipo'
        managed=False
        
    def __str__(self):
        return self.descripcion_grado
    

class provincia_tipo(models.Model):
    c_provincia = models.IntegerField(primary_key=True, verbose_name='c_provincia')
    descripcion_prov = models.CharField(max_length=255, verbose_name='Descripción Prov')
    
    class Meta:
        db_table = 'provincia_tipo'
        managed = False
        
    def __str__(self):
        return self.descripcion_prov

    
    
class localidad_tipo(models.Model):
    c_localidad=models.IntegerField(primary_key=True,verbose_name='c_localidad')
    descripcion_loc=models.CharField(max_length=255, verbose_name='Descripción Loc')
    c_departamento=models.IntegerField(verbose_name='c_departamento')
    descripcion_dpto=models.CharField(max_length=255, verbose_name='Descripción Dpto')
    c_provincia=models.ForeignKey(provincia_tipo, db_column='c_provincia',on_delete=models.CASCADE, verbose_name='c_provincia')
    
    class Meta:
        db_table='localidad_tipo'
        managed=False
        
    def __str__(self):
        return f'{self.descripcion_loc} ({self.descripcion_dpto})'


class pais(models.Model):
    c_pais=models.IntegerField(primary_key=True, verbose_name='c_pais')
    descripcion_pais=models.CharField(max_length=255, verbose_name='Descripción País')
    
    class Meta:
        db_table='pais'
        managed=False
        
    def __str__(self):
        return self.descripcion_pais
    
    
class nacionalidad(models.Model):
    c_nacionalidad = models.IntegerField(primary_key=True, verbose_name='c_nacionalidad')
    descripcion_nacional=models.CharField(max_length=255, verbose_name='Descripción Nacionalidad')
    c_pais=models.ForeignKey(pais,db_column='c_pais',on_delete=models.CASCADE,verbose_name='c_país')
    
    class Meta:
        db_table='nacionalidad'
        managed=False
        
    def __str__(self):
        return self.descripcion_nacional


class oferta_tipo(models.Model):
    c_oferta=models.IntegerField(primary_key=True, verbose_name='c_oferta')
    descripcion_ofer=models.CharField(max_length=255, verbose_name='Descripción Oferta')
    
    class Meta:
        db_table='oferta_tipo'
        managed=False
        
    def __str__(self):
        return self.descripcion_ofer

    

class orientacion_tipo(models.Model):
    c_orientacion=models.IntegerField(primary_key=True, verbose_name='c_orientación')
    descripcion_orien=models.CharField(max_length=255, verbose_name='Descripción Orientación')
    
    class Meta:
        db_table='orientacion_tipo'
        managed=False
        
    def __str__(self):
        return self.descripcion_orien



class sexo_tipo(models.Model):
    c_sexo=models.IntegerField(primary_key=True, verbose_name='c_sexo')
    descripcion_sex=models.CharField(max_length=255, verbose_name='Descripción Sexo')
    
    class Meta:
        db_table='sexo_tipo'
        managed=False
        
    def __str__(self):
        return self.descripcion_sex


class Nivel_Formacion_Cenpe(models.Model):
    nivel_form=models.CharField(max_length=50, null=False, blank=False,verbose_name='Nivel Formación')
    
    class Meta:
        verbose_name = 'Nivel Formacion'
        verbose_name_plural = 'Niveles Formacion'
        db_table = 'n_form_cenpe'
        managed = True

    def __str__(self):
        return self.nivel_form
    

class Estado_Civil_Cenpe(models.Model):
    descripcion_estciv=models.CharField(max_length=50, null=False, blank=False,verbose_name='Estado Civil')
    
    class Meta:
        verbose_name = 'Estado Civil'
        verbose_name_plural = 'Estados Civiles'
        db_table = 'est_civil_cenpe'
        managed = True

    def __str__(self):
        return self.descripcion_estciv



    
class Tipo_Formacion_Cenpe(models.Model):
    t_form=models.CharField(max_length=20, null=False, blank=False,verbose_name='Tipo Formación')
    
    class Meta:
        verbose_name = 'Tipo Formacion'
        verbose_name_plural = 'Tipos Formacion'
        db_table = 't_form_cenpe'
        managed = True

    def __str__(self):
        return self.t_form



class Tipo_Institucion_Cenpe(models.Model):
    t_inst=models.CharField(max_length=50, null=False, blank=False,verbose_name='Tipo Institución')
    
    class Meta:
        verbose_name = 'Tipo Institucion'
        verbose_name_plural = 'Tipos Instituciones'
        db_table = 't_inst_cenpe'
        managed = True

    def __str__(self):
        return self.t_inst


class Gestion_Institucion_Cenpe(models.Model):
    t_gestion=models.CharField(max_length=50, null=False, blank=False,verbose_name='Tipo Gestión')
    
    class Meta:
        verbose_name = 'Tipo Gestion'
        verbose_name_plural = 'Tipos Gestiones'
        db_table = 't_gestion_cenpe'
        managed = True

    def __str__(self):
        return self.t_gestion


class Estado_Titulo_Cenpe(models.Model):
    estado_titulo=models.CharField(max_length=50, null=False, blank=False,verbose_name='Estado Título')
    
    class Meta:
        verbose_name = 'Estado Titulo'
        verbose_name_plural = 'Estados Titulos'
        db_table = 'est_tit_cenpe'
        managed = True

    def __str__(self):
        return self.estado_titulo


class Nivel_Sistema(models.Model):
    niv_sis=models.CharField(max_length=255, null=False, blank=False,verbose_name='Niveles')
    
    class Meta:
        verbose_name = 'Nivel'
        verbose_name_plural = 'Niveles'
        db_table = 'niv_sis_cenpe'
        managed = True

    def __str__(self):
        return self.niv_sis

class Tipo_Trayectoria(models.Model):
    t_trayecto=models.CharField(max_length=255, null=False, blank=False, verbose_name='Tipo trayecto')
    
    class Meta:
        verbose_name = 'Tipo Trayectoria'
        verbose_name_plural = 'Tipos Trayectorias'
        db_table = 'tipo_trayectoria_cenpe'
        managed = True

    def __str__(self):
        return self.t_trayecto
    
    
class Trayectoria_Ocupacional(models.Model):
    usuario = models.OneToOneField(UsuariosVisualizador, on_delete=models.CASCADE, verbose_name='Usuario')
    ingreso_tray = models.ForeignKey(Tipo_Trayectoria, related_name='ingreso_trayectoria', on_delete=models.CASCADE, verbose_name='Ingresó como')
    actual_tray = models.ForeignKey(Tipo_Trayectoria,  on_delete=models.CASCADE, verbose_name='Actualmente')
    f_ingreso = models.DateField(verbose_name='Fecha Ingreso')
    frente_alumno = models.BooleanField(default=False, verbose_name='Frente Alumnos')
    anios_frentealumn = models.IntegerField(verbose_name='Años Frente Alumno')
    apoyo = models.BooleanField(default=False, verbose_name='Tareas de Apoyo')
    anios_apoyo = models.IntegerField(verbose_name='Años Apoyo')
    func_dir = models.BooleanField(default=False, verbose_name='Funciones Directivas')
    anios_dir = models.IntegerField(verbose_name='Años Dirección')
    act_extraesc = models.BooleanField(verbose_name='Actividad fuera Sistema')
    cant_hs = models.DecimalField(max_digits=5, decimal_places=2, verbose_name='Cantidad horas semanales')

    class Meta:
        verbose_name = 'Trayectoria Ocupacional'
        verbose_name_plural = 'Trayectorias Ocupacionales'
        db_table = 'trayectoria_ocupacional_cenpe'
        managed = True

    def __str__(self):
        return self.usuario.username if self.usuario else 'Sin Usuario'


class Datos_Personal_Cenpe(models.Model):
    usuario = models.CharField(max_length=11, verbose_name='usuario')
    apellidos = models.CharField(max_length=255, null=False, blank=False, verbose_name='Apellidos')
    nombres = models.CharField(max_length=255, null=False, blank=False, verbose_name='Nombres')
    pais_nac = models.ForeignKey(pais,on_delete=models.CASCADE, verbose_name='País Nacimiento')
    nacionalidad = models.ForeignKey(nacionalidad,on_delete=models.CASCADE, verbose_name='Nacionalidad')
    cuil = models.CharField(max_length=11, null=False, blank=False, verbose_name='Cuil')
    t_doc=models.ForeignKey(documento_tipo,on_delete=models.CASCADE, verbose_name='Tipo Documento')
    dni = models.CharField(max_length=9, null=False, blank=False, verbose_name='Documento N°')
    sexo = models.ForeignKey(sexo_tipo,on_delete=models.CASCADE, verbose_name='Sexo')
    estado_civil = models.ForeignKey(Estado_Civil_Cenpe,on_delete=models.CASCADE, verbose_name='Estado Civil')
    nivel_form = models.ForeignKey(Nivel_Formacion_Cenpe,on_delete=models.CASCADE, verbose_name='Nivel Formación')
    telfijo = models.CharField(max_length=20, null=True, blank=True, verbose_name='Teléfono Fijo')
    celular = models.CharField(max_length=20, null=False, blank=False, verbose_name='Teléfono Móvil')
    prov_nac = models.ForeignKey(provincia_tipo, related_name='provincia_nacimiento', on_delete=models.CASCADE, verbose_name='Prov Nacimiento')
    loc_nac = models.ForeignKey(localidad_tipo,related_name='localidad_nacimiento', on_delete=models.CASCADE, verbose_name='Localidad Nacimiento')
    f_nac = models.DateField(verbose_name='Fecha de Nacimiento')
    prov_resid = models.ForeignKey(provincia_tipo,on_delete=models.CASCADE, verbose_name='Prov Residencia')
    loc_resid = models.ForeignKey(localidad_tipo,on_delete=models.CASCADE, verbose_name='Localidad Residencia')
    calle = models.CharField(max_length=255, null=True, blank=True, verbose_name='Calle')
    nro = models.CharField(max_length=8, null=True, blank=True, verbose_name='Número')
    mz = models.CharField(max_length=8, null=True, blank=True, verbose_name='Manzana')
    pc = models.CharField(max_length=8, null=True, blank=True, verbose_name='Pc')
    casa = models.CharField(max_length=8, null=True, blank=True, verbose_name='Casa')
    piso = models.CharField(max_length=8, null=True, blank=True, verbose_name='Piso')
    uf = models.CharField(max_length=8, null=True, blank=True, verbose_name='UF')

    class Meta:
        verbose_name = 'Personal Cenpe'
        verbose_name_plural = 'Personales Cenpe'
        db_table = 'datos_personal_cenpe'
        managed = True

    def __str__(self):
        return f'{self.cuil}: {self.apellidos} {self.nombres}'

    def save(self, *args, **kwargs):
        if not self.usuario and 'UsuariosVisualizador' in kwargs:
            self.usuario = kwargs.pop('UsuariosVisualizador')
        super().save(*args, **kwargs)
        

class Academica_Cenpe(models.Model):
    usuario = models.OneToOneField(UsuariosVisualizador, on_delete=models.CASCADE, verbose_name='Usuario')
    titulo=models.CharField(max_length=255, null=False, blank=False, verbose_name='Nombre Título')
    tipo_form=models.ForeignKey(Tipo_Formacion_Cenpe,on_delete=models.CASCADE, verbose_name='Tipo Formación')
    nivel_form=models.ForeignKey(Nivel_Formacion_Cenpe,on_delete=models.CASCADE, verbose_name='Nivel Formación')
    tipo_inst=models.ForeignKey(Tipo_Institucion_Cenpe,on_delete=models.CASCADE, verbose_name='Tipo Gestión')
    gestion_inst=models.ForeignKey(Gestion_Institucion_Cenpe,on_delete=models.CASCADE, verbose_name='Tipo Gestión')
    estado_tit=models.ForeignKey(Estado_Titulo_Cenpe,on_delete=models.CASCADE, verbose_name='Estado Titulación')
    reg_nro=models.CharField(max_length=100, null=True, blank=True, verbose_name='Registro N°')
    f_egreso=models.DateField(verbose_name='Fecha egreso')

    class Meta:
        verbose_name = 'Academica'
        verbose_name_plural = 'Academicas'
        db_table = 'academica_cenpe'
        managed = True

    def __str__(self):
        return self.titulo

    def save(self, *args, **kwargs):
        if not self.usuario and 'user' in kwargs:
            self.usuario = kwargs.pop('user')
        super().save(*args, **kwargs)


