from django.core.management.base import BaseCommand
from apps.mapas.views_ai import entrenar_modelo

class Command(BaseCommand):
    help = 'Reentrena el modelo de machine learning'

    def handle(self, *args, **kwargs):
        entrenar_modelo()
        self.stdout.write(self.style.SUCCESS('Modelo reentrenado exitosamente'))