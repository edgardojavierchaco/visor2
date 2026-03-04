from django.db import models
from django.conf import settings


class Ticket(models.Model):

    ESTADOS = (
        ("abierto","Abierto"),
        ("en_proceso","En proceso"),
        ("respondido","Respondido"),
        ("cerrado","Cerrado"),
    )

    escuela_cueanexo = models.CharField(max_length=9, name='cueanexo')

    region = models.CharField(max_length=10, name='region')

    gestor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="tickets_asignados"
    )

    asunto = models.CharField(max_length=200)

    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default="abierto"
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True)

    fecha_actualizacion = models.DateTimeField(auto_now=True)

    cerrado = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.id} - {self.asunto}"


class TicketMensaje(models.Model):

    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name="mensajes"
    )

    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    mensaje = models.TextField()

    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Mensaje ticket {self.ticket.id}"


class TicketAdjunto(models.Model):

    mensaje = models.ForeignKey(
        TicketMensaje,
        on_delete=models.CASCADE,
        related_name="adjuntos"
    )

    archivo = models.FileField(upload_to="tickets_adjuntos/")

    fecha = models.DateTimeField(auto_now_add=True)


class TicketHistorial(models.Model):

    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE
    )

    accion = models.CharField(max_length=200)

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )

    fecha = models.DateTimeField(auto_now_add=True)