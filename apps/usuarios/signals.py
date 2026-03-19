from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import UsuariosVisualizador, PerfilUsuario, Rol


@receiver(post_save, sender=UsuariosVisualizador)
def crear_o_actualizar_perfil(sender, instance, created, **kwargs):

    # 🔹 normalización PRO
    nivel = getattr(instance.nivelacceso, 'tacceso', '')
    nivel = nivel.strip().lower()
    nivel = nivel.replace('á', 'a')

    # 🔹 mapa de roles
    roles_map = {
        'administrador': ('Administrador', 'all'),
        'gestor': ('Gestor', 'all'),
        'regional': ('Regional', 'regional'),
        'director/a': ('Director', 'propio'),
        'funcionario': ('Ministro', 'all'),
    }

    # 🔹 roles especiales funcionario
    if nivel == 'funcionario':
        roles_funcionario = [
            ('Ministro', 'all'),
            ('Subsecretario', 'all'),
            ('Director General', 'all'),
            ('Director de Nivel', 'nivel')
        ]

        for nombre, categoria in roles_funcionario:
            Rol.objects.get_or_create(
                nombre=nombre,
                defaults={'categoria_acceso': categoria}
            )

        nombre_rol, categoria = ('Ministro', 'all')

    else:
        nombre_rol, categoria = roles_map.get(
            nivel,
            ('Usuario', 'propio')
        )

    # 🔹 crear o traer rol
    rol, _ = Rol.objects.get_or_create(
        nombre=nombre_rol,
        defaults={'categoria_acceso': categoria}
    )

    # 🔹 perfil SIN duplicados
    perfil, creado = PerfilUsuario.objects.get_or_create(
        usuario=instance,
        defaults={'rol': rol}
    )

    # 🔹 actualizar si cambió
    if not creado and perfil.rol != rol:
        perfil.rol = rol
        perfil.save()