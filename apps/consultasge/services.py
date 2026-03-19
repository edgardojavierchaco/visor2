# apps/consultasge/services.py
from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Q
from django.core.exceptions import PermissionDenied
from .models import Consulta, Adjunto, SLA_HORAS_DEFAULT
from .models_padron import CapaUnicaOfertas
from apps.usuarios.models_regional import RegionalUsuariosAgentes
from apps.usuarios.models import UsuarioCueanexo
from .utils import horas_habiles_transcurridas, TURNOS, progreso_sla, estado_sla, validar_consulta_regional

# --------------------------
# Obtener gestor activo para una región
# --------------------------
def obtener_gestor_por_region(region):
    gestor = RegionalUsuariosAgentes.objects.filter(region_loc=region).first()
    if not gestor:
        return None

    # ⚡ Si gestor.usuario ya es un string, devolverlo directamente
    if isinstance(gestor.usuario, str):
        return gestor.usuario
    # ⚡ Si gestor.usuario es un objeto User, devolver su username
    return getattr(gestor.usuario, 'username', None)

# --------------------------
# Crear nueva consulta
# --------------------------
def crear_consulta(director, cueanexo, asunto, mensaje, categoria=None, archivos=None):
    # 🔒 Validar que el usuario tenga ese cueanexo
    if not UsuarioCueanexo.objects.filter(
        usuario=director,
        cueanexo=cueanexo
    ).exists():
        raise PermissionDenied("No tiene acceso a ese establecimiento.")
    
    # 🔎 Escuela
    try:
        escuela = CapaUnicaOfertas.objects.get(cueanexo=cueanexo)
    except CapaUnicaOfertas.DoesNotExist:
        raise PermissionDenied("No se encontró la escuela asociada al cueanexo.")

    sla = categoria.sla_horas if categoria else SLA_HORAS_DEFAULT
    gestor_username = obtener_gestor_por_region(escuela.region_loc)

    consulta = Consulta.objects.create(
        usuario=director,
        cueanexo=cueanexo,
        escuela=escuela.nom_est,
        region=escuela.region_loc,
        asunto=asunto,
        mensaje=mensaje,
        categoria=categoria,
        estado=Consulta.Estado.PENDIENTE,
        fecha_limite=timezone.now() + timedelta(hours=sla),
        gestor_asignado=gestor_username
    )

    # Adjuntos
    if archivos:
        for archivo in archivos:
            Adjunto.objects.create(consulta=consulta, archivo=archivo)

    return consulta

# --------------------------
# Cerrar consulta
# --------------------------
def cerrar_consulta(consulta, usuario):
    validar_consulta_regional(consulta, usuario)
    consulta.cerrar()
    return consulta

# --------------------------
# Obtener progreso SLA
# --------------------------
def obtener_progreso_sla(consulta, usuario):
    return progreso_sla(consulta, usuario)

# --------------------------
# Obtener estado SLA
# --------------------------
def obtener_estado_sla(consulta):
    return estado_sla(consulta)

# --------------------------
# Notificaciones del usuario
# --------------------------
def notificaciones_usuario(usuario):
    consultas = Consulta.objects.filter(usuario=usuario)
    stats = consultas.aggregate(
        pendientes=Count('id', filter=Q(estado=Consulta.Estado.PENDIENTE)),
        en_proceso=Count('id', filter=Q(estado=Consulta.Estado.EN_PROCESO)),
        vencidas=Count('id', filter=Q(
            fecha_limite__lt=timezone.now(),
            estado__in=[Consulta.Estado.PENDIENTE, Consulta.Estado.EN_PROCESO]
        ))
    )
    return {
        "pendientes": stats['pendientes'],
        "en_proceso": stats['en_proceso'],
        "vencidas": stats['vencidas'],
        "activas": stats['pendientes'] + stats['en_proceso']
    }

# --------------------------
# Filtrar consultas vencidas
# --------------------------
def consultas_vencidas(queryset):
    ahora = timezone.now()
    return queryset.filter(
        fecha_limite__lt=ahora,
        estado__in=[Consulta.Estado.PENDIENTE, Consulta.Estado.EN_PROCESO]
    )