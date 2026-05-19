from django.db import models
from django.core.exceptions import ValidationError
from apps.consultasge.models import CapaUnicaOfertas
from apps.bnhpersonas.models import NomencladorCeic as Ceic


##############################
# PERSONAL DOCENTE
##############################
class Personal(models.Model):
    id = models.AutoField(primary_key=True)
    cuil = models.CharField(max_length=11, unique=True)
    apellido = models.CharField(max_length=100, blank=True)
    nombres = models.CharField(max_length=100, blank=True)

    class Meta:
        db_table = 'personal_docente'
        ordering = ['apellido', 'nombres']

    def __str__(self):
        return f'{self.cuil}: {self.apellido}, {self.nombres}'


##############################
# CARGA DOCENTES
##############################
class DocenteFrenteGrado(models.Model):

    cueanexo = models.ForeignKey(
        CapaUnicaOfertas,
        to_field='cueanexo',
        db_column='cueanexo',
        on_delete=models.PROTECT
    )

    nom_est = models.CharField(max_length=200, blank=True)
    oferta = models.CharField(max_length=100, blank=True)

    grado_anio = models.PositiveSmallIntegerField()

    seccion = models.CharField(max_length=10)
    turno = models.CharField(max_length=20)

    cuil_docente = models.ForeignKey(
        Personal,
        to_field='cuil',
        db_column='cuil',
        on_delete=models.PROTECT
    )

    cargo = models.ForeignKey(
        Ceic,
        to_field='c_ceic',
        db_column='c_ceic',
        on_delete=models.PROTECT,
        related_name='docentes_frente_grado'
    )

    sit_revista = models.CharField(max_length=3)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'docente_frente_grado'
        ordering = ['cueanexo', 'grado_anio', 'seccion', 'turno']

    def save(self, *args, **kwargs):
        """
        Auto completa datos de escuela desde CapaUnicaOfertas
        """
        if self.cueanexo:
            self.nom_est = self.cueanexo.nom_est
            self.oferta = self.cueanexo.oferta

        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.cueanexo} - {self.grado_anio}°{self.seccion} {self.turno} - {self.cuil_docente.apellido}, {self.cuil_docente.nombres} ({self.cargo.descripcion})'

    def clean(self):

        oferta = (
            self.oferta.upper()
            if self.oferta
            else ''
        )

        grado = self.grado_anio
        seccion = self.seccion.strip().upper()

        # VALIDACIÓN GLOBAL
        if grado < 0 or grado > 7:
            raise ValidationError({
                'grado_anio': 'El grado/año debe estar entre 0 y 7.'
            })

        # INICIAL
        if 'INICIAL' in oferta:

            if not (0 <= grado <= 5):
                raise ValidationError({
                    'grado_anio': 'Inicial permite 0 a 5.'
                })

            if not ('A' <= seccion <= 'Z'):
                raise ValidationError({
                    'seccion': 'Inicial permite A a Z.'
                })

        # PRIMARIA
        elif 'PRIMARIA' in oferta:

            if not (1 <= grado <= 7):
                raise ValidationError({
                    'grado_anio': 'Primaria permite 1 a 7.'
                })

            if not ('A' <= seccion <= 'Z'):
                raise ValidationError({
                    'seccion': 'Primaria permite A a Z.'
                })

        # SECUNDARIA
        elif 'SECUNDARIA' in oferta:

            if not (1 <= grado <= 6):
                raise ValidationError({
                    'grado_anio': 'Secundaria permite 1 a 6.'
                })

            try:
                num = int(seccion.replace('a', '').replace('A', ''))
            except:
                raise ValidationError({
                    'seccion': 'Secundaria usa formato 1a a 25a.'
                })

            if not (1 <= num <= 25):
                raise ValidationError({
                    'seccion': 'Secundaria permite 1a a 25a.'
                })