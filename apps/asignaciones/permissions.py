from apps.supervisa2.models.supervisor import Supervisor2
from apps.usuarios.models import UsuariosVisualizador

def es_supervisor(user):
    return Supervisor2.objects.filter(usuario=user.username).exists()

def es_regional(user):
    return (
        user.is_authenticated
        and UsuariosVisualizador.objects.filter(
            username=user.username,
            activo=True,
            nivelacceso__tacceso__iexact='Regional'
        ).exists()
    )