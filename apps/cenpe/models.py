from decimal import Decimal
from django.db import models
from apps.usuarios.models import UsuariosVisualizador
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
import re
from datetime import date

class CeicPuntos(models.Model):
    """
    Modelo que representa los puntos CEIC asignados a un nivel educativo.

    Atributos:
        nivel (str): Nivel educativo al que pertenece.
        ceic_id (int): ID único para CEIC.
        descripcion_ceic (str): Descripción detallada del CEIC.
        estado (bool): Estado activo o inactivo del registro.
        puntos (int): Puntos asignados para el nivel y CEIC específicos.
    """
    
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
    """
    Modelo para representar los diferentes tipos de documentos de identidad.

    Atributos:
        c_tipo (int): Código único para el tipo de documento.
        descripcion_doc (str): Descripción del tipo de documento.
    """
    
    c_tipo = models.IntegerField(primary_key=True, verbose_name='c_tipo')
    descripcion_doc = models.CharField(max_length=255, verbose_name='Descripción Doc')
    
    class Meta:
        db_table='documento_tipo'
        managed=False
        
    def __str__(self):
        return self.descripcion_doc
    

class grado_tipo(models.Model):
    """
    Modelo para representar los tipos de grados académicos.

    Atributos:
        c_grado (int): Código único del grado académico.
        descripcion_grado (str): Descripción del grado académico.
    """
    
    c_grado = models.IntegerField(primary_key=True, verbose_name='c_grado')
    descripcion_grado = models.CharField(max_length=255, verbose_name='Descripción Grado')
    
    class Meta:
        db_table='grado_tipo'
        managed=False
        
    def __str__(self):
        return self.descripcion_grado
    

class provincia_tipo(models.Model):
    """
    Modelo que representa las diferentes provincias.

    Atributos:
        c_provincia (int): Código único para la provincia.
        descripcion_prov (str): Descripción de la provincia.
    """
    
    c_provincia = models.IntegerField(primary_key=True, verbose_name='c_provincia')
    descripcion_prov = models.CharField(max_length=255, verbose_name='Descripción Prov')
    
    class Meta:
        db_table = 'provincia_tipo'
        managed = False
        
    def __str__(self):
        return self.descripcion_prov

    
    
class localidad_tipo(models.Model):
    """
    Modelo que representa las diferentes localidades.

    Atributos:
        c_localidad (int): Código único de la localidad.
        descripcion_loc (str): Descripción de la localidad.
        c_departamento (int): Código del departamento asociado.
        descripcion_dpto (str): Descripción del departamento.
        c_provincia (ForeignKey): Relación con el modelo `provincia_tipo`.
    """
    
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
    """
    Modelo para representar los diferentes países.

    Atributos:
        c_pais (int): Código único del país.
        descripcion_pais (str): Nombre del país.
    """
    
    c_pais=models.IntegerField(primary_key=True, verbose_name='c_pais')
    descripcion_pais=models.CharField(max_length=255, verbose_name='Descripción País')
    
    class Meta:
        db_table='pais'
        managed=False
        
    def __str__(self):
        return self.descripcion_pais
    
    
class nacionalidad(models.Model):
    """
    Modelo para representar las diferentes nacionalidades.

    Atributos:
        c_nacionalidad (int): Código único de la nacionalidad.
        descripcion_nacional (str): Descripción de la nacionalidad.
        c_pais (ForeignKey): Relación con el modelo `pais`.
    """
    
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
        ordering=['niv_sis']
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
    usuario =models.CharField(max_length=9,verbose_name='Usuario') 
    apellidos = models.CharField(max_length=255, null=False, blank=False, verbose_name='Apellidos')
    nombres = models.CharField(max_length=255, null=False, blank=False, verbose_name='Nombres')
    pais_nac = models.ForeignKey(pais,on_delete=models.CASCADE, verbose_name='País Nacimiento')
    nacionalidad = models.ForeignKey(nacionalidad,on_delete=models.CASCADE, verbose_name='Nacionalidad')
    t_doc=models.ForeignKey(documento_tipo,on_delete=models.CASCADE, verbose_name='Tipo Documento')
    dni = models.CharField(max_length=8, null=False, blank=False, verbose_name='Documento N°')
    cuil = models.CharField(max_length=11, null=False, blank=False, verbose_name='Cuil')    
    sexo = models.ForeignKey(sexo_tipo,on_delete=models.CASCADE, verbose_name='Sexo')
    estado_civil = models.ForeignKey(Estado_Civil_Cenpe,on_delete=models.CASCADE, verbose_name='Estado Civil')
    nivel_form = models.ForeignKey(Nivel_Formacion_Cenpe,on_delete=models.CASCADE, verbose_name='Nivel Formación')    
    telfijo = models.CharField(max_length=10, null=True, blank=True, verbose_name='Teléfono Fijo')
    celular = models.CharField(max_length=10, null=False, blank=False, verbose_name='Teléfono Móvil')
    prov_nac = models.CharField(max_length=150, null=False, blank=False, verbose_name='Provincia Nacimiento')
    loc_nac = models.CharField(max_length=150, null=False, blank=False, verbose_name='Ciudad Nacimiento')
    f_nac = models.DateField(verbose_name='Fecha de Nacimiento')
    prov_resid = models.CharField(max_length=150, null=False, blank=False, verbose_name='Provincia Residencia')
    loc_resid = models.CharField(max_length=150, null=False, blank=False, verbose_name='Localidad Residencia')
    calle = models.CharField(max_length=255, null=True, blank=True, verbose_name='Calle')
    nro = models.CharField(max_length=8, null=True, blank=True, verbose_name='Número')
    mz = models.CharField(max_length=8, null=True, blank=True, verbose_name='Manzana')
    pc = models.CharField(max_length=8, null=True, blank=True, verbose_name='Parcela')
    casa = models.CharField(max_length=8, null=True, blank=True, verbose_name='Casa')
    piso = models.CharField(max_length=8, null=True, blank=True, verbose_name='Piso')
    uf = models.CharField(max_length=8, null=True, blank=True, verbose_name='UF')
    barrio = models.CharField(max_length=255, null=True, blank=True, verbose_name='Barrio')
    id_jurisdiccional=models.BigIntegerField(null=True, blank=True, verbose_name='Id_jurisdiccional')

    class Meta:
        verbose_name = 'Personal Cenpe'
        verbose_name_plural = 'Personales Cenpe'
        db_table = 'datos_personal_cenpe'
        managed = True

    def __str__(self):
        return f'{self.cuil}: {self.apellidos} {self.nombres}'
    
    def clean(self):
        # Validar que apellidos y nombres solo contengan letras, tildes, apostrofes y estén en mayúsculas
        allowed_chars = re.compile(r"^[A-ZÁÉÍÓÚÑ' ]+$")

        for field_name in ['apellidos', 'nombres']:
            value = getattr(self, field_name)
            if not allowed_chars.match(value):
                raise ValidationError({field_name: _('Solo se permiten letras mayúsculas, espacios, tildes y apóstrofes.')})

        # Validar que CUIL comience con 20, 27, 23 o 24
        if not re.match(r'^(20|27|23|24)\d{9}$', self.cuil):
            raise ValidationError({'cuil': _('El CUIL debe comenzar con 20, 27, 23 o 24 y contener 11 dígitos.')})

        # Validar que los dígitos de CUIL coincidan con el DNI
        if self.dni and self.cuil:
            if self.cuil[2:10] != self.dni.zfill(8):
                raise ValidationError({'cuil': _('Los dígitos del CUIL deben coincidir con el DNI.')})

        # Convertir calle y barrio a mayúsculas y permitir solo tildes y apóstrofes
        allowed_address_chars = re.compile(r"^[A-ZÁÉÍÓÚÑ' ]*$")

        for field_name in ['calle', 'barrio']:
            value = getattr(self, field_name)
            if value and not allowed_address_chars.match(value.upper()):
                raise ValidationError({field_name: _('Solo se permiten letras mayúsculas, espacios, tildes y apóstrofes.')})


    def save(self, *args, **kwargs):
        # Convertir apellidos, nombres, calle y barrio a mayúsculas
        if not self.pk:  # Solo cargar los datos automáticamente cuando se crea el objeto
            user = kwargs.pop('user', None)
            if user:
                self.usuario = user.username                
        if self.calle:
            self.calle = self.calle.upper()
        if self.barrio:
            self.barrio = self.barrio.upper()
        if not self.usuario and 'UsuariosVisualizador' in kwargs:
            self.usuario = kwargs.pop('UsuariosVisualizador')
        self.id_jurisdiccional = int(
            f"22{self.cuil}"
        )
        
        # Realizar la limpieza y validaciones
        self.full_clean()
        super().save(*args, **kwargs)
        

class Academica_Cenpe(models.Model):
    usuario = models.CharField(max_length=9, verbose_name='Usuario')
    titulo=models.CharField(max_length=255, null=False, blank=False, verbose_name='Nombre Título')
    tipo_form=models.ForeignKey(Tipo_Formacion_Cenpe,on_delete=models.CASCADE, verbose_name='Tipo Formación')
    nivel_form=models.ForeignKey(Nivel_Formacion_Cenpe,on_delete=models.CASCADE, verbose_name='Nivel Formación')
    tipo_inst=models.ForeignKey(Tipo_Institucion_Cenpe,on_delete=models.CASCADE, verbose_name='Tipo Institución')
    gestion_inst=models.ForeignKey(Gestion_Institucion_Cenpe,on_delete=models.CASCADE, verbose_name='Tipo Gestión')    
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
        if not self.pk:  # Solo cargar los datos automáticamente cuando se crea el objeto
            user = kwargs.pop('user', None)
            if user:
                self.usuario = user.username                
        
        if not self.usuario and 'UsuariosVisualizador' in kwargs:
            self.usuario = kwargs.pop('UsuariosVisualizador')
        super().save(*args, **kwargs)


class SituacionRevista(models.Model):
    sit_rev=models.CharField(max_length=100, null=False, blank=False, verbose_name='Situación Revista')
    
    class Meta:
        verbose_name = 'Situacion Revista'
        verbose_name_plural = 'Situaciones Revistas'
        db_table = 'situacion_revista'
        managed = True
        
    def __str__(self):
        return self.sit_rev


class funciones(models.Model):
    funcion=models.CharField(max_length=100, verbose_name='funcion')
    
    class Meta:
        verbose_name = 'Funcion'
        verbose_name_plural = 'Funciones'
        db_table = 'funciones'
        ordering = ['funcion']
        managed = True
        
    def __str__(self):
        return self.funcion

class condicionactividad(models.Model):
    cond_act=models.CharField(max_length=255, verbose_name='Condición Actividad')
    
    class Meta:
        verbose_name = 'Condicion Actividad'
        verbose_name_plural = 'Condiciones Actividades'
        db_table = 'condicion_actividad'
        ordering=['cond_act']
        managed = True
        
    def __str__(self):
        return self.cond_act

class Categoria_Cueanexo(models.Model):
    nom_categoria=models.CharField(max_length=50, verbose_name='Categoría')
    
    def __str__(self):
        return self.nom_categoria

class TipoJornada_Cueanexo(models.Model):
    tipo_jornada=models.CharField(max_length=100, verbose_name='Jornada')
    
    def __str__(self):
        return self.tipo_jornada

class Zona_Cueanexo(models.Model):
    tipo_zona=models.CharField(max_length=255, verbose_name='Zona')
    
    class Meta:
        ordering=['tipo_zona']
    
    def __str__(self):
        return self.tipo_zona

   
class CargosHoras_Cenpe(models.Model):
    usuario =models.CharField(max_length=9, verbose_name='Usuario')
    cueanexo=models.CharField(max_length=9, null=False, blank=False, verbose_name='Cueanexo')
    categoria=models.CharField(max_length=50, verbose_name='Categoría')
    jornada=models.CharField(max_length=50, verbose_name='Jornada')
    zona=models.CharField(max_length=150, verbose_name='Zona')
    nivel_cargohora=models.CharField(max_length=255, verbose_name='Nivel_Cargo_Hora')
    cargos_horas=models.CharField(max_length=255, verbose_name='Cargo_Horas')
    cant_horas=models.DecimalField(max_digits=4,decimal_places=2, verbose_name='Cantidad_Horas')
    lunes=models.BooleanField(default=False, verbose_name='Lunes')
    martes=models.BooleanField(default=False, verbose_name='Martes')
    miercoles=models.BooleanField(default=False, verbose_name='Miercoles')
    jueves=models.BooleanField(default=False, verbose_name='Jueves')
    viernes=models.BooleanField(default=False, verbose_name='Viernes')
    situacion_revista=models.CharField(max_length=150, verbose_name='Situacion_Revista')
    funciones=models.CharField(max_length=255, verbose_name='Funciones')
    condicion_actividad=models.CharField(max_length=255, verbose_name='Condicion_Actividad')
    fecha_desde=models.DateField(verbose_name='Fecha_desde')
    fecha_hasta=models.DateField(default=date(2060,12,31), verbose_name='Fecha_hasta')
    cuof=models.SmallIntegerField(null=False, blank=False, verbose_name='CUOF')
    cuof_anexo=models.SmallIntegerField(null=False, blank=False, verbose_name='CUOF_Anexo')
           
    def __str__(self):
        return f"{self.usuario}-{self.cueanexo}: {self.cargos_horas}"
    
    def save(self, *args, **kwargs):
        if not self.pk:  # Solo cargar los datos automáticamente cuando se crea el objeto
            user = kwargs.pop('user', None)
            if user:
                self.usuario = user.username                
        
        if not self.usuario and 'UsuariosVisualizador' in kwargs:
            self.usuario = kwargs.pop('UsuariosVisualizador')
        super().save(*args, **kwargs)

class PadronCenpe(models.Model):
    cueanexo=models.IntegerField(verbose_name='cueanexo')
    id_establecimiento=models.CharField(verbose_name='id_establecimiento')
    id_localizacion=models.CharField(verbose_name='id_localizacion')
    id_oferta_local=models.CharField(verbose_name='id_oferta_local')
    nom_est=models.CharField(verbose_name='nom_est')
    acronimo_oferta=models.CharField(verbose_name='acronimo_oferta')
    oferta=models.CharField(verbose_name='oferta')
    nro_est=models.CharField(verbose_name='nro_est')
    ambito=models.CharField(verbose_name='ambito')
    sector=models.CharField(verbose_name='sector')
    region_loc=models.CharField(verbose_name='region_loc')
    ref_loc=models.CharField(verbose_name='ref_loc')
    calle=models.CharField(verbose_name='calle')
    numero=models.CharField(verbose_name='numero')
    localidad=models.CharField(verbose_name='localidad')
    departamento=models.CharField(verbose_name='departamento')
    estado_loc=models.CharField(verbose_name='estado_loc')
    est_oferta=models.CharField(verbose_name='est_oferta')
    estado_est=models.CharField(verbose_name='estado_est')
    jornada=models.CharField(verbose_name='jornada')
    
    class Meta:
        verbose_name = 'Padron_Cenpe'
        verbose_name_plural = 'Padrones_Cenpe'
        db_table = 'padron_actualizar'
        managed = False
    
    def __str__(self):
        return f"{self.cueanexo}" 
    
    
        
    