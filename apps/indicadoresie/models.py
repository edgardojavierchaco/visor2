from tabnanny import verbose
from django.db import models
from django.forms import model_to_dict
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator

# =====================================================================
# 1. TUS MODELOS DE SIEMPRE (No se toca nada)
# =====================================================================

class SIESegimiento(models.Model):    
    agente = models.CharField(max_length=100, verbose_name='Agente')
    escuela = models.CharField(max_length=100, verbose_name='Escuela')
    cueanexo = models.CharField(max_length=9, verbose_name='Cueanexo')
    region = models.CharField(max_length=50, verbose_name='Regional')
    nivel = models.CharField(max_length=50, verbose_name='Nivel')
    sieant = models.IntegerField(verbose_name='Sie_anterior', db_column='SIE2024')
    sieact = models.IntegerField(verbose_name='Sie_actual', db_column='SIE2025')
    dni_agente = models.CharField(max_length=8, verbose_name='DNI')
    id = models.AutoField(primary_key=True)
    
    class Meta:
        managed = False
        verbose_name = 'sie_seguimiento'
        verbose_name_plural = 'sies_seguimientos'
        db_table = 'sie_seguimiento'
    
    def __str__(self):
        return f'{self.agente} - {self.cueanexo}{self.escuela}'
    
    def toJSON(self):
        item = model_to_dict(self)
        item['agente'] = self.agente
        item['escuela'] = self.escuela
        item['cueanexo'] = self.cueanexo
        item['region'] = self.region
        item['nivel'] = self.nivel
        item['sieant'] = self.sieant
        item['sieact'] = self.sieact
        item['dni_agente'] = self.dni_agente
        item['id'] = self.id
        return item
    
class SeguimientoSIE2025(models.Model):    
    nivel = models.CharField(max_length=50, verbose_name='Nivel')
    region = models.CharField(max_length=50, verbose_name='Regional')
    agente = models.CharField(max_length=100, verbose_name='agente')
    localidad = models.CharField(max_length=100, verbose_name='localidad')
    cue = models.CharField(max_length=20, verbose_name='Cue')
    anexo = models.CharField(max_length=10, verbose_name='Anexo')
    grado = models.CharField(max_length=30, verbose_name='Grado')
    seccion = models.CharField(max_length=30, verbose_name='Sección')
    turno_nombre = models.CharField(max_length=50, verbose_name='Turno')
    ciclo_lectivo = models.CharField(max_length=10, verbose_name='Ciclo')
    estado_inscripcion = models.CharField(max_length=50, verbose_name='Estado')
    nro_documento = models.CharField(max_length=20, verbose_name='DNI')
    apellidos = models.CharField(max_length=100, verbose_name='Apellidos')
    nombres = models.CharField(max_length=50, verbose_name='Nombres')
    discapacidad = models.CharField(max_length=100, blank=True, null=True, verbose_name='Discapacidad')
    comunidad_aborigen = models.CharField(max_length=50, blank=True, null=True, verbose_name='Comunidad')
    id = models.AutoField(primary_key=True)
    
    class Meta:
        db_table = 'seguimiento_sie_2025'
        managed = False  
        verbose_name = 'seguimiento_sie'
        verbose_name_plural = 'seguimientos_sies'

    def __str__(self):
        return f"{self.apellidos}, {self.nombres} ({self.nro_documento})"   
    
    def toJSON(self):
        item = model_to_dict(self)
        return item

class InformeSGE(models.Model):    
    id_excel = models.CharField(max_length=100, blank=True, null=True)
    cueanexo = models.CharField(max_length=20, blank=True, null=True)
    agente = models.CharField(max_length=150, blank=True, null=True)
    nombre = models.CharField(max_length=250, blank=True, null=True)
    tipo_oferta = models.CharField(max_length=100, blank=True, null=True)
    sector = models.CharField(max_length=50, blank=True, null=True)
    ambito = models.CharField(max_length=50, blank=True, null=True)
    regional = models.CharField(max_length=50, blank=True, null=True)
    cue = models.CharField(max_length=20, blank=True, null=True)
    anexo = models.CharField(max_length=10, blank=True, null=True)
    escuela_cod_tel = models.CharField(max_length=50, blank=True, null=True)
    escuela_tel = models.CharField(max_length=50, blank=True, null=True)
    escuela_email = models.CharField(max_length=150, blank=True, null=True)
    responsable_apellido = models.CharField(max_length=100, blank=True, null=True)
    responsable_nombre = models.CharField(max_length=100, blank=True, null=True)
    telefono_responsable = models.CharField(max_length=50, blank=True, null=True)
    sge_2025 = models.CharField(max_length=50, blank=True, null=True)
    sge_2026 = models.CharField(max_length=50, blank=True, null=True)
    inscriptos_2025 = models.CharField(max_length=50, blank=True, null=True)
    inscriptos_2026 = models.CharField(max_length=50, blank=True, null=True)
    
    id = models.AutoField(primary_key=True)
    
    class Meta:
        managed = False  
        db_table = 'sie_seguimiento_actualizado2026'
        verbose_name = 'Informe SGE'
        verbose_name_plural = 'Informes SGE'

    def __str__(self):
        return f"{self.nombre} ({self.cueanexo})"

class PadronRegional(models.Model):
    cueanexo = models.CharField(max_length=20, primary_key=True, verbose_name='CUE Anexo')
    nom_est = models.CharField(max_length=255, verbose_name='Establecimiento')
    oferta = models.TextField(blank=True, null=True, verbose_name='Oferta(s)')
    region_loc = models.CharField(max_length=50, blank=True, null=True, verbose_name='Región')
    localidad = models.CharField(max_length=100, blank=True, null=True, verbose_name='Localidad')
    departamento = models.CharField(max_length=100, blank=True, null=True, verbose_name='Departamento')
    sector = models.CharField(max_length=50, blank=True, null=True, verbose_name='Sector')
    ambito = models.CharField(max_length=50, blank=True, null=True, verbose_name='Ámbito')
    
    acronimo = models.TextField(blank=True, null=True)
    etiqueta = models.TextField(blank=True, null=True)
    nro_est = models.CharField(max_length=50, blank=True, null=True)
    ref_loc = models.CharField(max_length=100, blank=True, null=True)
    calle = models.CharField(max_length=255, blank=True, null=True)
    numero = models.CharField(max_length=50, blank=True, null=True)
    estado_loc = models.TextField(blank=True, null=True)
    est_oferta = models.TextField(blank=True, null=True)
    estado_est = models.TextField(blank=True, null=True)
    resploc_cuitcuil = models.CharField(max_length=100, blank=True, null=True)
    resploc_doc = models.TextField(blank=True, null=True)
    apellido_resp = models.TextField(blank=True, null=True)
    nombre_resp = models.TextField(blank=True, null=True)
    resploc_email = models.TextField(blank=True, null=True)
    resploc_telefono = models.TextField(blank=True, null=True)
    sup_tecnico = models.TextField(blank=True, null=True)
    email_suptecnico = models.TextField(blank=True, null=True)
    tel_suptecnico = models.TextField(blank=True, null=True)
    categoria = models.TextField(blank=True, null=True)
    cui_loc = models.TextField(blank=True, null=True)
    cua_loc = models.TextField(blank=True, null=True)
    cuof_loc = models.TextField(blank=True, null=True)
    jornada = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'v_capa_unica_ofertas_ant' 
        verbose_name = 'Padrón Regional'
        verbose_name_plural = 'Padrones Regionales'

    def __str__(self):
        return f"{self.cueanexo} - {self.nom_est}"

class FechaActualizacionSGE(models.Model):
    id = models.IntegerField(primary_key=True)
    fecha = models.DateTimeField(verbose_name='Fecha de Actualización')

    class Meta:
        managed = False
        db_table = '"indicadores"."fecha_actualizacion_sge2026"'
        verbose_name = 'Fecha de Actualización SGE'
        verbose_name_plural = 'Fechas de Actualización SGE'

# =====================================================================
# 2. EL NUEVO SISTEMA DE ROLES (Basado en tu verificación SQL)
# =====================================================================

class RolUsuarioGlobal(models.Model):
    """ Tabla: usuarios_rol (Catálogo de cargos) """
    id = models.IntegerField(primary_key=True)
    nombre = models.CharField(max_length=100) # Ej: 'Ministro', 'Regional', 'Director de Nivel Inicial'
    
    class Meta:
        managed = False
        db_table = 'usuarios_rol'

    def __str__(self):
        return self.nombre

class UsuarioVisualizador(models.Model):
    """ Tabla: Usuario_Visualizador (La tabla del login) """
    id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=150, unique=True, db_column='username') # Tu CUIL
    is_superuser = models.BooleanField()
    is_staff = models.BooleanField()
    
    class Meta:
        managed = False
        db_table = 'Usuario_Visualizador'

    def __str__(self):
        return f"{self.username} (ID: {self.id})"

class UsuarioPerfil(models.Model):
    """ 
    Tabla: usuarios_perfilusuario 
    EL PUENTE: Une el ID del login con el ID del cargo.
    """
    id = models.AutoField(primary_key=True)
    
    # Vinculamos al ID de Usuario_Visualizador usando la columna usuario_id
    usuario = models.OneToOneField(
        UsuarioVisualizador, 
        on_delete=models.DO_NOTHING, 
        db_column='usuario_id', 
        related_name='perfil'
    )
    
    # Vinculamos al ID de usuarios_rol usando la columna rol_id
    rol = models.ForeignKey(
        RolUsuarioGlobal, 
        on_delete=models.DO_NOTHING, 
        db_column='rol_id'
    )

    class Meta:
        managed = False
        db_table = 'usuarios_perfilusuario'

    def __str__(self):
        return f"{self.usuario.username} -> {self.rol.nombre}"