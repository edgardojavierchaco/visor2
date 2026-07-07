from django.db import models

from apps.consultasge.models_padron import CapaUnicaOfertas

from apps.bnhalumnos.models import (
    Alumno    
)
class CicloChoices(models.IntegerChoices):
    CICLO_2024 = 2024, "2024"
    CICLO_2025 = 2025, "2025"
    CICLO_2026 = 2026, "2026"
    CICLO_2027 = 2027, "2027"



class Especial_AlumnoSeccion(models.Model):
    """Modelo que relaciona a un alumno de bnhalumnos con una sección de la Educación
    Especial. (Alumno <-> SeccionEspecial)
    Llama los datos de: bnhalumnos.Alumno y SeccionEspecial
    """
    
    # De no contar con el mismo, concatenar: 
    # apellidos, nombres, c_tipo_documento, nro_documento, fecha_nacimiento, sexo. 
    # Ej: NavarroFabioIgnacio144651081040220031
    id = models.BigAutoField(unique=True, primary_key=True)
    id_alumno = models.ForeignKey(
        Alumno, 
        on_delete=models.CASCADE
    )
    #id_est_ben = models.ForeignKey('EstablecimientoBeneficio', on_delete=models.CASCADE)
    id_seccion = models.ForeignKey(
        'SeccionEspecial', 
        on_delete=models.CASCADE
    )
    fecha_actualizacion = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{Alumno.apellidos}, {Alumno.nombres} - {Alumno.nro_doc} {SeccionEspecial.nombre_seccion}"
    
    class Meta:
        db_table = "especial_alumnoseccion"
        verbose_name = "Alumno de Educación Especial"
        verbose_name_plural = "Alumnos de Educación Especial"
    """
    def save(self, *args, **kwargs):
        if not self.id_persona_jurisdiccional:
            self.id_persona_jurisdiccional = (
                f"{self.apellidos}"
                f"{self.nombres}"
                f"{self.cd_tipo_documento}"
                f"{self.nro_documento}"
                f"{self.fecha_nacimiento.strftime('%d%m%Y')}"
                f"{self.sexo}"
            )
        super().save(*args, **kwargs)
    """
   
   
# ---------------- posiblemente pase a estar en bnhalumnos 
class EstablecimientoBeneficio(models.Model):
    """Este modelo representa los beneficios alimentarios gratuitos de un establecimiento para con el alumno.
    Por ende, si el establecimiento o el alumno desaparecen, esto no puede existir.
    Tabla intermedia entre AlumnoSGE y CapaUnicaOferta, donde está la oferta de ese anexo/ubicación particular.
    """

    id = models.BigAutoField(primary_key=True) 
    id_cueanexo_beneficio = models.ForeignKey(
        CapaUnicaOfertas, 
        on_delete=models.CASCADE
        db_constraint=False
    )
    id_alumno = models.ForeignKey(
        Alumno, 
        on_delete=models.CASCADE
    )
    
    cd_ppi = models.ForeignKey(
        'sino_tipo', 
        on_delete=models.PROTECT, 
        name='cd_ppi', 
        related_name='ppi'
    )    
    beneficio_alimentario_gratuito = models.ForeignKey(
        'beneficio_sino_tipo', 
        on_delete=models.PROTECT, 
        name='beneficio_alimentario_gratuito'
    )
    fuente_financiamiento = models.ForeignKey(
        'fuente_financiamiento_tipo', 
        on_delete=models.PROTECT, 
        name='fuente_financiamiento'
    )
    prestacion_tipo = models.ForeignKey(
        'prestacion_tipo', 
        on_delete=models.PROTECT, 
        name='prestacion_tipo'
    )
    espacio_comedor = models.ForeignKey(
        'espacio_comedor_tipo', 
        on_delete=models.PROTECT, 
        name='espacio_comedor'
    )    
# -------------------------------------------------------------
    
class SeccionEspecial(models.Model):
    """Este modelo representa la sección/cursada en la que cursa los alumnos de la educación especial. 
    Esta sección se encuentra relacionada a un cueanexo.
    Estos datos no se encuentran en el models de 'bnhalumnos'.
    """
    # De no tenerlo, concatenar: 
    # cueanexo + cd_oferta_padron + cd_grado + nombre_seccion + cd_tipo_sección + cd_turno. 
    # Ej: 22111222333
    id = models.CharField(max_length=100, primary_key=True) 
    cueanexo = models.ForeignKey(
        CapaUnicaOfertas, 
        on_delete=models.CASCADE, 
        name='cueanexo'
        db_constraint=False
    )
    cd_tipo_seccion = models.ForeignKey(
        'seccion_tipo', 
        on_delete=models.PROTECT, 
        name='cd_tipo_seccion',
    )
    
    tipo_estructura_especial = models.ForeignKey(
        'CatalogoTipoEstructuraEspecial',
        on_delete=models.PROTECT,
        name='tipo_estructura_especial',
    )
    nombre_seccion = models.CharField(max_length=50, null=False, blank=False)
    descripcion = models.TextField(max_length=255, null= True, blank=True)
    capacidad_total = models.IntegerField(null=False, blank=False)
    ciclo = models.IntegerField(choices=CicloChoices.choices, verbose_name="Ciclo lectivo")
    turno = models.ForeignKey(
        'turno_tipo', 
        on_delete=models.PROTECT
    )
    rango_etario = models.ForeignKey(   #grado
        'CatalogoTipoRangoEtario',
        on_delete=models.PROTECT,
        db_column='rango_etario'
    )
    modalidad = models.ForeignKey(
        'modalidad_dictado_tipo', 
        on_delete=models.PROTECT
    )
    lugar_dictado = models.CharField(max_length=100, null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now_add=True)
    
    # Detalle del grupo
    # areas_disponibles = models.CharField(max_length=150, null=True, blank=True)
    
    
    
# --------------------- MODELOS DE CATÁLOGOS ------------------------
    
    
# Cómo se verá en el catálogo:
# id    estructura                                                                         oferta                               rango
# 0.    Ninguno de los anteriores                                                          -                                    - 
# 1.    CEAT (Centro de estimuación y aprendizaje tempranos)                               JM/JI/Int/Cur-Tall/Educ-Inte         0-3
# 2.    SEAT (Servicio de estimulación y aprendizaje tempranos)                            JM/JI/Int/Cur-Tall/Educ-Inte         0-3
# 3.    SAI (Servicio de apoyo a la Inclusión en los niveles obligatorios y modalidades)   PR/SEC/Int/Cur-Tall/Educ-Inte        4-22
# 4.    CEFOL (Centro de Formación Laboral)                                                PR/SEC/Int/Cur-Tall/Educ-Inte        14-22
# 5.    SEFOL (Servicio de Formación e inclusión Laboral)                                  PR/SEC/Int/Cur-Tall/Educ-Inte        6-22
# 6.    SAEAI (Servicio de aprendizajes específicos y abordaje integral)                   PR/SEC/Int/Cur-Tall/Educ-Inte        3-22
# 7.    CET (Aún no se que significa) (para escuelas privadas)                             JM/JI/PR/SEC/Int/Cur-Tall/Educ-Inte  0-99
# 8.    SAIE (Aún no se que significa) (para escuelas privadas)                            JM/JI/PR/SEC/Int/Cur-Tall/Educ-Inte  0-99
#
class CatalogoTipoEstructuraEspecial(models.Model):
    """Este modelo representa el catálogo de tipos de estructura especial (CEAT, SEAT, SAI, CEFOL, SEFOL, SAEAI), 
    para que se pueda elegir en la creación de la sección especial.
    """
    
    cd_tipoestructuraespecial = models.IntegerField(primary_key=True)
    descripcion = models.CharField(max_length=100, name='descripcion')
    
    class Meta:
        verbose_name='Tipo de estructura especial'
        verbose_name_plural='Tipos de estructuras especiales'
        db_table= 'catalogo_tipo_estructura_especial'
    
    def __str__(self):
        return self.descripcion

# Cómo es la lógica detrás:
#       descr    oferta                                                                     estructura
# 0.    0-3     JM/JI/Integración-CursosyTalleres-EducIntegralAdolescentesJovenes           CEAT Y SEAT
# 1.    4-7     JM/JI/Pri7/Integración-CursosyTalleres-EducIntegralAdolescentesJovenes      SAI-SEFOL-SAEAI
# 2.    8-9     Pri7/Secu7/Integración-CursosyTalleres-EducIntegralAdolescentesJovenes      SAI-SEFOL-SAEAI
# 3.    10-13   Secu7/Integración-CursosyTalleres-EducIntegralAdolescentesJovenes           SAI-SEFOL-SAEAI
# 4.    14-22   Secu7/Integración-CursosyTalleres-EducIntegralAdolescentesJovenes           SAI-SEFOL-SAEAI-CEFOL
# 5.    23-99   Secu7/Integración-CursosyTalleres-EducIntegralAdolescentesJovenes           No definido
class CatalogoTipoRangoEtario(models.Model):
    """Este modelo representa el catálogo de los tipos de rango etario, desde 0 años hasta 99 años, 
    para las secciones dentro de la educación especial.
    """
    
    cd_tiporangoetario = models.IntegerField(primary_key=True)
    descripcion = models.CharField(max_length=100, name='descripcion')
    
    class Meta:
        verbose_name='Tipo de rango etario'
        verbose_name_plural='Tipos de rangos etarios'
        db_table= 'catalogo_tipo_rango_etario'
    
    def __str__(self):
        return self.descripcion


    
    
    
# ------------------------- Modelos que no se encuentran creados en otras apps --------------------------------

class beneficio_sino_tipo(models.Model):
    """Modelo para representar si se da prestación alimentaria en el establecimiento o no."""
    
    beneficio_alimentario_gratuito = models.IntegerField(primary_key=True)
    descripcion = models.CharField(max_length=100, name='descripcion')
    
    class Meta:
        verbose_name='Beneficio Alimentario Gratuito'
        verbose_name_plural='Beneficios Alimentarios Gratuitos'
        db_table='beneficio_sino_tipo'
    
    def __str__(self):
        return self.descripcion    
    

class fuente_financiamiento_tipo(models.Model):
    """Modelo para representar la fuente del financiamiento que recibe la institución para 
    prestar el beneficio alimentario gratuito al alumno, según  el nivel de gestión del que 
    proviene, por ejemplo: Nacional,  Jurisdiccional, Municipal, Escolar, o sus combinaciones"""
    
    fuente_financiamiento = models.IntegerField(primary_key=True)
    descripcion = models.CharField(max_length=100, name='descripcion')

    class Meta:
        verbose_name='fuente de financiamiento'
        verbose_name_plural='fuentes de financiamiento'
        db_table='fuente_financiamiento_tipo'
    
    def __str__(self):
        return self.descripcion    
    
class prestacion_tipo(models.Model):
    """Tipo de beneficio alimentario gratuito que recibe el  alumno, 
    por ejemplo: Desayuno o Merienda, Almuerzo o  Cena, Refuerzo Alimentario, etc."""
    
    prestacion_tipo = models.IntegerField(primary_key=True)
    descripcion = models.CharField(max_length=100, name='descripcion')
    
    class Meta:
        verbose_name='Tipo de prestación alimentaria'
        verbose_name_plural='Tipos de prestación alimentaria'
        db_table='prestacion_tipo'
    
    def __str__(self):
        return self.descripcion        
    
class espacio_comedor_tipo(models.Model):
    """Existencia y tipo de espacio físico destinado a prestar el  servicio de comedor a 
    los alumnos en la institución, por  ejemplo: Sí, cocina y comedor; No; Sin información; etc."""
    
    espacio_comedor = models.IntegerField(primary_key=True)
    descripcion = models.CharField(max_length=100, name='descripcion')

    class Meta:
        verbose_name='Tipo de espacio comedor'
        verbose_name_plural='Tipos de espacio comedor'
        db_table='espacio_comedor_tipo'
    
    def __str__(self):
        return self.descripcion  
    
class sino_tipo(models.Model):
    """Modelo genérico para representar de respuestas Si/No/Sin información."""
    
    cd_sino = models.IntegerField(primary_key=True)
    descripcion = models.CharField(max_length=100, name='descripcion')

    class Meta:
        verbose_name='Si/No/Sin info'
        verbose_name_plural='Si/No/Sin info'
        db_table='sino_tipo'
    
    def __str__(self):
        return self.descripcion  

class seccion_tipo(models.Model):
    """Tipo de sección en la que cursa el alumno (Independiente,  Múltiple, etc.). 
    Aplicable a todas las ofertas de la Educación Común, a cursos de Formación Profesional 
    de Adultos y a cursos/talleres de la Escuela Especial. Para las otras ofertas, 
    usar código -1 (“No corresponde”)."""
    
    cd_tipo_seccion = models.IntegerField(primary_key=True)
    descripcion = models.CharField(max_length=100, name='descripcion')

    class Meta:
        verbose_name='Tipo de sección'
        verbose_name_plural='Tipos de sección'
        db_table='seccion_tipo'
    
    def __str__(self):
        return self.descripcion 
    
class turno_tipo(models.Model):
    """Turno en el que cursa el alumno (Mañana, Tarde, etc.). Aplicable a todas las ofertas 
    de la Educación Común, a  cursos de Formación Profesional de Adultos y a cursos/talleres 
    de la Escuela Especial. Para las otras ofertas, usar código -1 (“No corresponde”)."""
    
    cd_turno = models.IntegerField(primary_key=True)
    descripcion = models.CharField(max_length=100, name='descripcion')
    
    class Meta:
        verbose_name='Turno'
        verbose_name_plural='Turnos'
        db_table= 'turno_tipo'
    
    def __str__(self):
        return self.descripcion 
    
    
class orientacion_tipo(models.Model):
    """Orientación del plan de estudio del Nivel Secundario de la  Educación Común y de Adultos.
    Para los otros niveles y modalidades, usar código -1 (“No  Corresponde”)."""
    
    cd_orientacion = models.IntegerField(primary_key=True)
    descripcion = models.CharField(max_length=100, name='descripcion')
    
    class Meta:
        verbose_name='Orientación'
        verbose_name_plural='Orientaciones'
        db_table= 'orientacion_tipo'
    
    def __str__(self):
        return self.descripcion 

class oferta_tipo(models.Model):
    """Oferta en la que está cursando sus estudios este alumno, según las consideradas en esta toma de datos."""
    
    cd_oferta = models.IntegerField(primary_key=True)
    descripcion = models.CharField(max_length=100, name='descripcion')
    rango_edad_minima = models.IntegerField(name='rango_edad_minima')
    rango_edad_maxima = models.IntegerField(name='rango_edad_maxima')
    
    class Meta:
        verbose_name='Tipo de oferta'
        verbose_name_plural='Tipos de oferta'
        db_table= 'oferta_tipo'
    
    def __str__(self):
        return self.descripcion 

class grado_tipo(models.Model):
    """Año de estudio que está cursando el alumno en Educación  Común o en los planes graduados de Adultos.
    Para Especial y para los planes no graduados de Adultos,  consignar 0 (cero). 
    Los valores están determinados por la oferta y validados por  su duración."""
    
    cd_grado = models.IntegerField(primary_key=True)
    descripcion = models.CharField(max_length=100, name='descripcion')
    
    class Meta:
        verbose_name='Tipo de grado'
        verbose_name_plural='Tipo de grados'
        db_table= 'grado_tipo'
    
    def __str__(self):
        return self.descripcion 

class duraciones_ofertas(models.Model):
    """Duración en años de la oferta que cursa el alumno en Educación Común o 
    en los planes graduados de Adultos. Para Especial y para los planes no 
    graduados de Adultos, consignar 0 (cero)."""
    
    cd_duracion_oferta = models.IntegerField(primary_key=True)
    cd_oferta = models.ForeignKey(
        'oferta_tipo',
        on_delete=models.PROTECT, 
        name='cd_oferta'
    )
    cd_grado = models.ForeignKey(
        'grado_tipo',
        on_delete=models.PROTECT,
        name='cd_grado'
    )
    duracion_anios = models.IntegerField(name='duracion_anios')
    
    class Meta:
        verbose_name='Duración de oferta'
        verbose_name_plural='Duraciones de ofertas'
        db_table= 'duracion_oferta'
    
    def __str__(self):
        return f"{self.cd_oferta} - {self.cd_grado} ({self.duracion_anios} años)"
    
class modalidad_dictado_tipo(models.Model):
    """Modalidad de dictado del plan de estudios (Presencial o A distancia, con sus distintas características)."""
    
    cd_modalidad_dictado = models.IntegerField(primary_key=True)
    descripcion = models.CharField(max_length=100, name='descripcion')
    
    class Meta:
        verbose_name='Tipo de modalidad de cursado'
        verbose_name_plural='Tipos de modalidad de cursado'
        db_table= 'modalidad_dictado_tipo'
    
    def __str__(self):
        return self.descripcion 