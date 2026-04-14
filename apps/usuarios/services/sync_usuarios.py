from django.db import connection, transaction
from django.utils import timezone
from django.core.cache import cache
from django.db import close_old_connections

from apps.usuarios.models import (
    UsuariosVisualizador,
    PerfilUsuario,
    NivelAcceso,
    Rol,
    SyncControl,
    SyncLog,
    SyncEstado,
    UsuarioRechazadoLog
)

from apps.usuarios.constants import CACHE_PROGRESS_KEY, CACHE_CANCEL_KEY


def lock_proceso():
    from datetime import timedelta

    with transaction.atomic():
        estado, _ = SyncEstado.objects.select_for_update().get_or_create(
            proceso="sync_usuarios"
        )

        if estado.en_ejecucion and estado.ultima_ejecucion:
            if timezone.now() - estado.ultima_ejecucion > timedelta(minutes=30):
                estado.en_ejecucion = False

        if estado.en_ejecucion:
            return False

        estado.en_ejecucion = True
        estado.ultima_ejecucion = timezone.now()
        estado.save()
        return True


def unlock_proceso():
    SyncEstado.objects.filter(proceso="sync_usuarios").update(
        en_ejecucion=False,
        ultima_ejecucion=timezone.now()
    )


def valid_cuil(cuil, doc):
    try:
        return cuil.split("-")[1].lstrip("0") == doc.lstrip("0")
    except Exception:
        return False


def sync_usuarios_directores():

    if not lock_proceso():
        yield {"estado": "error", "msg": "Ya en ejecución"}
        return

    cache.set(CACHE_CANCEL_KEY, False, timeout=3600)
    close_old_connections()

    SyncLog.objects.create()

    usernames_vistos = set()

    try:
        nivel = NivelAcceso.objects.get(tacceso="Director/a")
        rol = Rol.objects.get(nombre="Director")

        # =========================
        # OBTENER DATOS
        # =========================
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    resploc_cuitcuil,
                    apellido_resp,
                    nombre_resp,
                    resploc_email,
                    resploc_telefono,
                    resploc_doc
                FROM public.v_capa_unica_ofertas_ant
            """)

            cols = [c[0] for c in cursor.description]
            rows = cursor.fetchall()

        total = len(rows)

        cache.set(CACHE_PROGRESS_KEY, {
            "estado": "procesando",
            "total": total,
            "procesados": 0
        }, timeout=3600)

        yield {"estado": "inicio", "total": total}

        procesados = 0

        # =========================
        # LOOP PRINCIPAL
        # =========================
        for i, row in enumerate(rows, start=1):

            # 🔴 CANCELACIÓN
            if i % 10 == 0:
                if cache.get(CACHE_CANCEL_KEY):
                    cache.set(CACHE_PROGRESS_KEY, {
                        "estado": "cancelado",
                        "total": total,
                        "procesados": procesados
                    }, timeout=3600)

                    yield {"estado": "cancelado"}
                    return

            data = dict(zip(cols, row))
            username = None

            try:
                cuil = data.get("resploc_cuitcuil")
                doc = str(data.get("resploc_doc") or "").strip()

                if not cuil or not doc:
                    raise ValueError("Campos vacíos")

                if not valid_cuil(cuil, doc):
                    raise ValueError("CUIL inválido")

                username = cuil.replace("-", "")
                usernames_vistos.add(username)

                with transaction.atomic():

                    obj = UsuariosVisualizador.objects.filter(username=username).first()

                    if not obj:
                        obj = UsuariosVisualizador.objects.create(
                            username=username,
                            apellido=data["apellido_resp"],
                            nombres=data["nombre_resp"],
                            correo=data["resploc_email"],
                            telefono=data["resploc_telefono"],
                            nivelacceso=nivel,
                            activo=True,
                            is_staff=True,
                            is_superuser=False,
                        )

                        obj.set_password(doc)
                        obj.save()

                        PerfilUsuario.objects.update_or_create(
                            usuario=obj,
                            defaults={"rol": rol}
                        )

                        estado = "creado"

                    else:
                        cambios = False

                        if obj.apellido != data["apellido_resp"]:
                            obj.apellido = data["apellido_resp"]
                            cambios = True

                        if obj.nombres != data["nombre_resp"]:
                            obj.nombres = data["nombre_resp"]
                            cambios = True

                        if obj.correo != data["resploc_email"]:
                            obj.correo = data["resploc_email"]
                            cambios = True

                        if obj.telefono != data["resploc_telefono"]:
                            obj.telefono = data["resploc_telefono"]
                            cambios = True

                        if cambios:
                            obj.save()
                            estado = "actualizado"
                        else:
                            estado = "sin_cambios"

                        PerfilUsuario.objects.update_or_create(
                            usuario=obj,
                            defaults={"rol": rol}
                        )

                procesados = i

                # ✅ EVENTO STREAM
                yield {
                    "tipo": "fila",
                    "username": username,
                    "estado": estado,
                    "n": i
                }

            except Exception as e:

                UsuarioRechazadoLog.objects.create(
                    username=username or "unknown",
                    payload=data,
                    motivo=str(e)
                )

                yield {
                    "tipo": "fila",
                    "username": username or "unknown",
                    "estado": "error",
                    "msg": str(e),
                    "n": i
                }

            # 📊 PROGRESO
            cache.set(CACHE_PROGRESS_KEY, {
                "estado": "procesando",
                "total": total,
                "procesados": procesados
            }, timeout=3600)

            # 🔌 liberar conexiones
            if i % 20 == 0:
                close_old_connections()

        # =========================
        # FINAL
        # =========================
        SyncControl.objects.update_or_create(
            nombre="directores",
            defaults={"last_sync": timezone.now()}
        )

        cache.set(CACHE_PROGRESS_KEY, {
            "estado": "finalizado",
            "total": total,
            "procesados": total
        }, timeout=3600)

        yield {"estado": "finalizado", "total": total}

    except Exception as e:

        cache.set(CACHE_PROGRESS_KEY, {
            "estado": "error",
            "error": str(e)
        }, timeout=3600)

        yield {"estado": "error", "msg": str(e)}
        raise

    finally:
        unlock_proceso()
        close_old_connections()