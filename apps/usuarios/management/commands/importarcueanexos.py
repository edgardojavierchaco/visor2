# apps/usuarios/management/commands/importar_cueanexos.py

from django.core.management.base import BaseCommand
from django.db import connection
from apps.usuarios.models import UsuarioCueanexo, UsuariosVisualizador
import re


def limpiar_cuil(cuil):
    return re.sub(r"\D", "", str(cuil))


class Command(BaseCommand):
    help = "Importa relación usuario (CUIL) - cueanexo desde v_capa_unica_ofertas"

    def handle(self, *args, **kwargs):

        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT
                    cueanexo,
                    resploc_cuitcuil
                FROM public.v_capa_unica_ofertas
                WHERE resploc_cuitcuil IS NOT NULL
            """)

            rows = cursor.fetchall()

        creados = 0
        sin_usuario = 0
        existentes = 0

        for cueanexo, cuiles_raw in rows:

            if not cuiles_raw:
                continue

            cueanexo = str(cueanexo).strip()

            # 🔥 separar lista
            lista_cuiles = [
                limpiar_cuil(c)
                for c in str(cuiles_raw).split(",")
                if limpiar_cuil(c)
            ]

            usuario_encontrado = None

            # 🔥 buscar el PRIMER usuario válido
            for cuil in lista_cuiles:
                try:
                    usuario_encontrado = UsuariosVisualizador.objects.get(username=cuil)
                    break
                except UsuariosVisualizador.DoesNotExist:
                    continue

            # ❌ si ninguno existe → skip
            if not usuario_encontrado:
                sin_usuario += 1
                continue

            # ✔ crear relación
            obj, created = UsuarioCueanexo.objects.get_or_create(
                cueanexo=cueanexo,
                defaults={"usuario": usuario_encontrado}
            )

            if created:
                creados += 1
            else:
                existentes += 1

        # 📊 resumen
        self.stdout.write(self.style.SUCCESS(f"✔ Nuevos creados: {creados}"))
        self.stdout.write(self.style.WARNING(f"⚠ Ya existentes: {existentes}"))
        self.stdout.write(self.style.WARNING(f"⚠ Sin usuario válido: {sin_usuario}"))