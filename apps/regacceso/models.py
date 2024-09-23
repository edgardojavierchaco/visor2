from django.db import models
from apps.usuarios.models import UsuariosVisualizador

class RegistroAcceso(models.Model):
    usuario = models.ForeignKey(UsuariosVisualizador, on_delete=models.CASCADE, name='usuario')
    fecha_acceso = models.DateTimeField(auto_now_add=True, name='fecha_acceso')
    url_acceso = models.CharField(max_length=255, name='url_acceso')
    metodo_http = models.CharField(max_length=10, name='metodo_http')
    ip_usuario = models.CharField(max_length=45, name='ip_usuario')
    agente_usuario = models.CharField(max_length=255, name='agente_usuario')
    tiempo_carga_pagina = models.FloatField(null=True, blank=True, name='tiempo_carga_pagina')
    tiempo_respuesta_servidor = models.FloatField(null=True, blank=True, name='tiempo_respuesta_servidor')

    def __str__(self):
        return f"{self.usuario.username} - {self.fecha_acceso}"
