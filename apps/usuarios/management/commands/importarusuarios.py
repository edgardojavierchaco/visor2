from django.core.management.base import BaseCommand
from django.db import connection
from apps.usuarios.models import UsuariosVisualizador, NivelAcceso, Rol, PerfilUsuario

class Command(BaseCommand):
    help = 'Importa usuarios desde tabla usuarios_nuevos'

    def handle(self, *args, **kwargs):
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    cuil,
                    dni,
                    apellido,
                    nombres,
                    email,
                    telefono,
                    nivel_acceso,
                    rol
                FROM usuarios_nuevos
            """)
            rows = cursor.fetchall()

        creados = 0
        actualizados = 0

        # Mapeo de roles a categoría de acceso
        map_roles = {
            'Ministro': 'all',
            'Subsecretario': 'all',
            'Director General': 'all',
            'Director': 'propio',
            'Regional': 'regional',
            'Administrador': 'all',
            'Gestor': 'all'
        }

        for row in rows:
            cuil, dni, apellido, nombres, email, telefono, nivel_acceso_text, rol_nombre = row

            # --------------------------
            # Nivel de acceso
            # --------------------------
            nivel, _ = NivelAcceso.objects.get_or_create(
                tacceso=nivel_acceso_text
            )

            # --------------------------
            # Rol
            # --------------------------
            if not rol_nombre:
                rol_nombre = 'Usuario'

            categoria = map_roles.get(rol_nombre, 'propio')
            rol, _ = Rol.objects.get_or_create(
                nombre=rol_nombre,
                defaults={'categoria_acceso': categoria}
            )

            # --------------------------
            # Usuario
            # --------------------------
            user, created = UsuariosVisualizador.objects.get_or_create(
                username=cuil,
                defaults={
                    'apellido': apellido.upper(),
                    'nombres': nombres.upper(),
                    'correo': email,
                    'telefono': str(telefono),
                    'nivelacceso': nivel,
                    'activo': True,
                    'is_staff': False,
                    'is_superuser': False,
                }
            )

            # Actualizar datos si el usuario ya existía
            user.apellido = apellido.upper()
            user.nombres = nombres.upper()
            user.correo = email
            user.telefono = str(telefono)
            user.nivelacceso = nivel
            user.activo = True
            user.is_staff = False
            user.is_superuser = False

            # --------------------------
            # Contraseña (dni)
            # --------------------------
            if created or not user.check_password(str(dni)):
                user.set_password(str(dni))

            user.save()

            # --------------------------
            # Perfil + Rol
            # --------------------------
            PerfilUsuario.objects.update_or_create(
                usuario=user,
                defaults={'rol': rol}
            )

            # Contadores
            if created:
                creados += 1
            else:
                actualizados += 1

        self.stdout.write(self.style.SUCCESS(
            f'Usuarios creados: {creados} | actualizados: {actualizados}'
        ))