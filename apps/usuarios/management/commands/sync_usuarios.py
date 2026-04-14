from django.core.management.base import BaseCommand
from apps.usuarios.services.sync_usuarios import sync_usuarios_directores


class Command(BaseCommand):
    help = "Ejecuta sincronización de usuarios"

    def handle(self, *args, **options):
        self.stdout.write("🚀 Iniciando sync...")

        resultado = sync_usuarios_directores()

        self.stdout.write(self.style.SUCCESS(f"✅ Sync finalizado: {resultado}"))