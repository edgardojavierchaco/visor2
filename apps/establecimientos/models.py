from django.db import models

class PadronActualizar(models.Model):
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
        return f"{self.cueanexo} - {self.nom_est}"
    
    class Meta:
        managed = False
        verbose_name = 'Padron_Actualizar'
        verbose_name_plural = 'Padrones_Actualizaciones'
        ordering = ['id_establecimiento', 'id_localizacion','cueanexo']
        db_table = 'padron_actualizar'


class PadronOfertas(models.Model):
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
