from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import UsuariosVisualizador, Rol
import unicodedata


# -----------------------------------
# 🔹 NORMALIZACIÓN ROBUSTA
# -----------------------------------

def normalizar(texto):
    texto = (texto or '').strip().lower()
    return unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('ascii')


# -----------------------------------
# 🔹 SIGNAL OPTIMIZADO
# -----------------------------------

@receiver(post_save, sender=UsuariosVisualizador)
def preparar_roles(sender, instance, created, update_fields=None, **kwargs):

    # ⚡ Evitar ejecución innecesaria
    if not created and update_fields and 'nivelacceso' not in update_fields:
        return

    nivel_raw = getattr(instance.nivelacceso, 'tacceso', '')
    nivel = normalizar(nivel_raw)

    # -----------------------------------
    # 🔹 Mapa base
    # -----------------------------------

    roles_map = {
        'administrador': ('Administrador', 'all'),
        'gestor': ('Gestor', 'all'),
        'regional': ('Regional', 'regional'),
        'director/a': ('Director', 'propio'),
    }

    # -----------------------------------
    # 🔹 FUNCIONARIO
    # -----------------------------------

    if nivel == 'funcionario':

        roles_funcionario = [
            ('Ministro', 'all'),
            ('Subsecretario', 'all'),
            ('Director General', 'all'),
            ('Director de Nivel Inicial', 'nivel'),
            ('Director de Nivel Primario', 'nivel'),
            ('Director de Nivel Secundario', 'nivel'),
            ('Director de Nivel Superior', 'nivel'),
            ('Director de Modalidad Adultos', 'modalidad'),
            ('Director de Modalidad Rural', 'modalidad'),
            ('Director de Modalidad Especial', 'modalidad'),
            ('Director de Modalidad Contexto', 'modalidad'),
            ('Director de Servicios Complementarios', 'modalidad'),
        ]

        # ⚡ Crear solo si no existen
        existentes = set(Rol.objects.values_list('nombre', flat=True))

        nuevos = [
            Rol(nombre=nombre, categoria_acceso=categoria)
            for nombre, categoria in roles_funcionario
            if nombre not in existentes
        ]

        if nuevos:
            Rol.objects.bulk_create(nuevos)

        return  # 🔥 importante cortar acá

    # -----------------------------------
    # 🔹 OTROS NIVELES
    # -----------------------------------

    nombre_rol, categoria = roles_map.get(
        nivel,
        ('Usuario', 'propio')
    )

    Rol.objects.get_or_create(
        nombre=nombre_rol,
        defaults={'categoria_acceso': categoria}
    )