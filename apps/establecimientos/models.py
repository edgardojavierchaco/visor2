from django.db import models

class PadronActualizar(models.Model):
    """
    Modelo que representa la información actualizada del padrón de establecimientos educativos.

    Atributos:
        id_establecimiento (IntegerField): Identificador único del establecimiento.
        id_localizacion (IntegerField): Identificador de la localización del establecimiento.
        cueanexo (TextField): Código único de establecimiento anexo.
        nom_est (CharField): Nombre del establecimiento.
        nro_est (CharField): Número del establecimiento.
        anio_creac_establec (CharField): Año de creación del establecimiento.
        fecha_creac_establec (CharField): Fecha de creación del establecimiento.
        region (CharField): Región geográfica del establecimiento.
        udt (CharField): Código UDT (Unidad de Decisión Territorial).
        cui (CharField): Código único de identificación.
        cua (CharField): Código CUA (Clave Única de Autorización).
        cuof (CharField): Código CUOF (Clave Única de Oferta Formativa).
        sector (CharField): Sector educativo (público o privado).
        ambito (CharField): Ámbito educativo.
        ref_loc (CharField): Referencia local del establecimiento.
        calle (CharField): Dirección del establecimiento.
        numero (CharField): Número de la dirección.
        localidad (CharField): Localidad donde se encuentra el establecimiento.
        departamento (CharField): Departamento geográfico del establecimiento.
        cod_postal (CharField): Código postal del establecimiento.
        categoria (CharField): Categoría del establecimiento.
        estado_est (CharField): Estado del establecimiento.
        estado_loc (CharField): Estado de la localización.
        telefono_cod_area (CharField): Código de área del teléfono.
        telefono_nro (CharField): Número de teléfono del establecimiento.
        per_funcionamiento (CharField): Período de funcionamiento del establecimiento.
        email_loc (CharField): Correo electrónico de la localización.
        sitio_web (CharField): Sitio web del establecimiento.
        cooperadora (CharField): Indicación de si tiene cooperadora.
        sede (BooleanField): Indicación de si es sede.
        permanencia (CharField): Tipo de permanencia del establecimiento.
        sede_adm (BooleanField): Indicación de si es sede administrativa.
        resploc_apellido (CharField): Apellido del responsable local.
        resploc_nombre (CharField): Nombre del responsable local.
        resploc_telefono (CharField): Teléfono del responsable local.
        resploc_doc (IntegerField): Documento del responsable local.
        resploc_email (CharField): Correo electrónico del responsable local.
        resploc_nacimiento (DateField): Fecha de nacimiento del responsable local.
        resploc_cuitcuil (CharField): CUIT/CUIL del responsable local.
        arancel (SmallIntegerField): Arancel del establecimiento (si aplica).
    """
    id_establecimiento = models.IntegerField(blank=True, null=True)
    id_localizacion = models.IntegerField(blank=True, null=True)
    cueanexo = models.TextField(max_length=9,blank=True, null=True)
    nom_est = models.CharField(max_length=255, blank=True, null=True, name="nom_est")
    nro_est = models.CharField(max_length=4, blank=True, null=True, name="nro_est")
    anio_creac_establec = models.CharField(max_length=4, blank=True, null=True, name="anio_creac_establec")
    fecha_creac_establec = models.CharField(max_length=255, blank=True, null=True, name="fecha_creac_establec")
    region = models.CharField(max_length=25, blank=True, null=True, name="region")
    udt = models.CharField(max_length=4, blank=True, null=True, name="udt")
    cui = models.CharField(max_length=15, blank=True, null=True, name="cui")
    cua = models.CharField(max_length=15, blank=True, null=True, name="cua")
    cuof = models.CharField(max_length=4, blank=True, null=True, name="cuof")
    sector = models.CharField(max_length=25, blank=True, null=True, name="sector")
    ambito = models.CharField(max_length=50, blank=True, null=True, name="ambito")
    ref_loc = models.CharField(max_length=255, blank=True, null=True, name="ref_loc")
    calle = models.CharField(max_length=255, blank=True, null=True, name="calle")
    numero = models.CharField(max_length=255, blank=True, null=True, name="numero")
    localidad = models.CharField(max_length=255, blank=True, null=True, name="localidad")
    departamento = models.CharField(max_length=255, blank=True, null=True, name="departamento")
    cod_postal = models.CharField(max_length=255, blank=True, null=True, name="cod_postal")
    categoria = models.CharField(max_length=255, blank=True, null=True, name="categoria")
    estado_est = models.CharField(max_length=25, blank=True, null=True, name="estado_est")
    estado_loc = models.CharField(max_length=25, blank=True, null=True, name="estado_loc")
    telefono_cod_area = models.CharField(max_length=10, blank=True, null=True, name="telefono_cod_area")
    telefono_nro = models.CharField(max_length=15, blank=True, null=True, name="telefono_nro")
    per_funcionamiento = models.CharField(max_length=255, blank=True, null=True, name="per_funcionamiento")
    email_loc = models.CharField(max_length=255, blank=True, null=True, name="email_loc")
    sitio_web = models.CharField(max_length=255, blank=True, null=True, name="sitio_web")
    cooperadora = models.CharField(max_length=255, blank=True, null=True, name="cooperadora")
    sede = models.BooleanField(blank=True, null=True, name="sede")
    permanencia = models.CharField(max_length=255, blank=True, null=True, name="permanencia")
    sede_adm = models.BooleanField(blank=True, null=True, name="sede_adm")
    resploc_apellido = models.CharField(max_length=255, blank=True, null=True, name="resploc_apellido")
    resploc_nombre = models.CharField(max_length=255, blank=True, null=True, name="resploc_nombre")
    resploc_telefono = models.CharField(max_length=255, blank=True, null=True, name="resploc_telefono")
    resploc_doc = models.IntegerField(blank=True, null=True, name="resploc_doc")
    resploc_email = models.CharField(max_length=255, blank=True, null=True, name="resploc_email")
    resploc_nacimiento = models.DateField(blank=True, null=True, name="resploc_nacimiento")
    resploc_cuitcuil = models.CharField(max_length=13, blank=True, null=True, name="resploc_cuitcuil")
    arancel = models.SmallIntegerField(blank=True, null=True, name="arancel")

    def __str__(self):
        """
        Retorna una representación en cadena del objeto PadronActualizar.

        Returns:
            str: El CUE anexo seguido del nombre del establecimiento.
        """
        
        return f"{self.cueanexo} - {self.nom_est}"
    
    class Meta:
        managed = False
        verbose_name = 'Padron_Actualizar'
        verbose_name_plural = 'Padrones_Actualizaciones'
        ordering = ['id_establecimiento', 'id_localizacion','cueanexo']
        db_table = 'padron_actualizar'


class PadronOfertas(models.Model):
    """
    Modelo que representa las ofertas educativas asociadas a un establecimiento.

    Atributos:
        cueanexo (IntegerField): Código único del establecimiento anexo.
        id_establecimiento (CharField): Identificador del establecimiento.
        id_localizacion (CharField): Identificador de la localización del establecimiento.
        id_oferta_local (CharField): Identificador único de la oferta educativa.
        nom_est (CharField): Nombre del establecimiento.
        acronimo_oferta (CharField): Acrónimo de la oferta educativa.
        oferta (CharField): Descripción de la oferta educativa.
        nro_est (CharField): Número del establecimiento.
        ambito (CharField): Ámbito educativo.
        sector (CharField): Sector educativo (público o privado).
        region_loc (CharField): Región geográfica de la localización.
        ref_loc (CharField): Referencia local del establecimiento.
        calle (CharField): Dirección del establecimiento.
        numero (CharField): Número de la dirección.
        localidad (CharField): Localidad donde se encuentra el establecimiento.
        departamento (CharField): Departamento geográfico del establecimiento.
        estado_loc (CharField): Estado de la localización.
        est_oferta (CharField): Estado de la oferta educativa.
        estado_est (CharField): Estado del establecimiento.
        jornada (CharField): Tipo de jornada educativa.
    """
    cueanexo = models.IntegerField(blank=True, null=True, name='cueanexo')
    id_establecimiento = models.CharField(blank=True, null=True, name='id_establecimiento')
    id_localizacion = models.CharField(blank=True, null=True, name='id_localizacion')
    id_oferta_local = models.CharField(primary_key=True)
    nom_est = models.CharField(blank=True, null=True, name='nom_est')
    acronimo_oferta = models.CharField(blank=True, null=True, name='acronimo_oferta')
    oferta = models.CharField(blank=True, null=True, name='oferta')
    nro_est = models.CharField(blank=True, null=True, name='nro_est')
    ambito = models.CharField(blank=True, null=True, name='ambito')
    sector = models.CharField(blank=True, null=True, name='sector')
    region_loc = models.CharField(blank=True, null=True, name='region_loc')
    ref_loc = models.CharField(blank=True, null=True, name='ref_loc')
    calle = models.CharField(blank=True, null=True, name='calle')
    numero = models.CharField(blank=True, null=True, name='numero')
    localidad = models.CharField(blank=True, null=True, name='localidad')
    departamento = models.CharField(blank=True, null=True, name='departamento')
    estado_loc = models.CharField(blank=True, null=True, name='estado_loc')
    est_oferta = models.CharField(blank=True, null=True, name='est_oferta')
    estado_est = models.CharField(blank=True, null=True, name='estado_est')
    jornada = models.CharField(blank=True, null=True, name='jornada')

    class Meta:
        managed = False
        db_table = 'padron_ofertas'
        ordering = ['cueanexo']

    def __str__(self):
        return f'CUE: {self.cueanexo}, Establecimiento: {self.nom_est}'
