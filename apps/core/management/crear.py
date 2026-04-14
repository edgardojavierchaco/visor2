from django.core.management.base import BaseCommand
from apps.usuarios.models import UsuariosVisualizador, NivelAcceso

class Command(BaseCommand):
    def handle(self, *args, **options):
        # Obtener o crear el nivel de acceso deseado
        nivel_acceso, _ = NivelAcceso.objects.get_or_create(tacceso='Administrador')
        
        # Crear el superusuario con el nivel de acceso adecuado
        UsuariosVisualizador.objects.create_superuser(
            username='225685230',
            password='22568523',
            apellido='GOMEZ',
            nombres='EDGARDO JAVIER',
            correo='edgardojavierchaco@gmail.com',
            telefono='3624202292',
            nivelacceso=nivel_acceso
        )
