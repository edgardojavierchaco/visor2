from django.conf import settings
from django.db import models

class Room(models.Model):
    name=models.CharField(max_length=100, unique=True, verbose_name='nombre')
    user=models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='rooms_joined',blank=True)
    manager_assigned = models.ForeignKey('Manager', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_rooms')
     
    def __str__(self):
        return self.name

class Message(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='Usuario')
    room = models.ForeignKey(Room, on_delete=models.CASCADE, verbose_name='Sala')
    message = models.CharField(verbose_name='Mensaje')
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='Enviado')
    
    def __str__(self):
        return self.message
    
class Manager(models.Model):
    user=models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    is_available= models.BooleanField(default=True)
    
    def __int__(self):
        return self.user