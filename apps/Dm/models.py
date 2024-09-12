import uuid 
from django.conf import settings
from django.db import models
from django.db.models import Count

User = settings.AUTH_USER_MODEL

class ModelBase(models.Model):
    id=models.UUIDField(default=uuid.uuid4, primary_key=True, db_index=True, editable=False)
    tiempo=models.DateTimeField(auto_now_add=True)
    actualizar=models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract=True
        
        

class CanalMensaje(ModelBase):
    canal=models.ForeignKey('Canal', on_delete=models.CASCADE)
    usuario=models.ForeignKey(User, on_delete=models.CASCADE)
    texto=models.TextField()
    
    class Meta:
        app_label='Dm'
    

class CanalUsuario(ModelBase):
    canal=models.ForeignKey('Canal',on_delete=models.SET_NULL, null=True)
    usuario=models.ForeignKey(User, on_delete=models.CASCADE)
    

class CanalQuerySet(models.QuerySet):
    def solo_uno(self):
        return self.annotate(num_usuarios = Count('usuarios').filter(num_usuarios=1))
        
    def solo_dos(self):
        return self.annotate(num_usuarios = Count('usuarios').filter(num_usuarios=2))

class CanalManager(models.Manager):
    def get_queryset(self, *args, **kwargs):
        return CanalQuerySet(self.model, using=self._db)

class Canal(ModelBase):
    usuario = models.ManyToManyField(User, blank=True, through=CanalUsuario)
    
    objects=CanalManager()