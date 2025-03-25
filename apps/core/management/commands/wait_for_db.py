import time
from django.db import connections
from django.db.utils import OperationalError
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    def handle(self, *args, **options):
        self.stdout.write('Esperando a que la base de datos esté disponible...')
        db_conn = None
        while not db_conn:
            try:
                db_conn = connections['default']
            except OperationalError:
                self.stdout.write('La base de datos no está disponible, esperando 1 segundo...')
                time.sleep(1)

        self.stdout.write(self.style.SUCCESS('La base de datos está disponible, continuando...'))
        