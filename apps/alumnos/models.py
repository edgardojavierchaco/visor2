from django.db import models

class documentoTipo(models.Model):
    c_tdoc=models.AutoField(primary_key=True, name='c_tdoc')
    descrip_doc=models.CharField(max_length=150, blank=False, null=False, name='descrip_doc')
    
    def __str__(self):
        return self.descrip_doc

class sexo(models.Model):
    c_sexo=models.AutoField(primary_key=True, name='c_sexo')
    descrip_sex=models.CharField(max_length=100, blank=False, null=False, name='descrip_sex')
    
    def __str__(self):
        return self.descrip_sex

class pais(models.Model):
    id=models.AutoField(primary_key=True, name='id')
    descrip_pais=models.CharField(max_length=255, blank=False, null=False, name='descrip_pais')
    c_pais=models.IntegerField(blank=False, null=False, name='c_pais')
    
    def __str__(self):
        return self.descrip_pais

class nacionalidad(models.Model):
    id=models.AutoField(primary_key=True, name='id')
    descrip_nacionalidad=models.CharField(max_length=255, blank=False, null=False, name='descrip_nacionalidad')
    c_nacionalidad=models.IntegerField(blank=False, null=False, name='c_nacionalidad')
    c_paisnacional=models.ForeignKey(pais, on_delete=models.CASCADE, name='c_pais')
    
    def __str__(self):
        return self.descrip_nacionalidad


class provincia(models.Model):
    id=models.AutoField(primary_key=True, name='id')
    descrip_prov=models.CharField(max_length=255, blank=False, null=False, name='descrip_prov')
    c_prov=models.IntegerField(blank=False, null=False, name='c_prov')
    
    
    def __str__(self):
        return self.descrip_prov

class localidad(models.Model):
    id=models.AutoField(primary_key=True, name='id')
    descrip_loc=models.CharField(max_length=255, blank=False, null=False, name='descrip_loc')
    c_loc=models.IntegerField(blank=False, null=False, name='c_loc')
    c_dep=models.IntegerField(blank=False, null=False, name='c_dep')
    descrip_dep=models.CharField(max_length=255, blank=False, null=False, name='descrip_dep')
    c_provloc=models.ForeignKey(provincia, on_delete=models.CASCADE, name='c_prov')
    
    def __str__(self):
        return self.descrip_loc

class oferta(models.Model):
    id=models.AutoField(primary_key=True, name='id')
    descrip_oferta=models.CharField(max_length=255, blank=False, null=False, name='descrip_oferta')
    edad_desde=models.IntegerField(blank=False, null=False, name='edad_desde')
    edad_hasta=models.IntegerField(blank=False, null=False, name='edad_hasta')
    
    def __str__(self):
        return self.descrip_oferta


class grados(models.Model):
    id=models.AutoField(primary_key=True, name='id')
    descrip_grado=models.CharField(max_length=255, blank=False, null=False, name='descrip_grado')
    c_grado=models.IntegerField(blank=False, null=False, name='c_grado')
    
    def __str__(self):
        return self.descrip_grado
