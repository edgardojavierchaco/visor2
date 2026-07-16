import datetime
import json
import threading
import time
import uuid
from functools import wraps

from django.core.cache import cache
from django.db import close_old_connections, connections, transaction
from django.http import JsonResponse
from django.utils import timezone

from .models import (
    FechaActualizacionPadronInterno,
    usuario_es_admin_padron,
)
from .permisos import padron_interno_admin_required_json, padron_interno_required_json

MATERIALIZADAS_DB = "default"
MATERIALIZADAS_DATABASE_NAME = "visualizador"
MATERIALIZADAS_SCHEMA = "padroninterno"
REFRESH_LOCK_NAME = "padroninterno_refresh_materializadas"

MATERIALIZED_VIEWS_PADRONINTERNO = (
    ("padroninterno", "mv_localizaciones"),
    ("padroninterno", "mv_establecimientos"),
    ("padroninterno", "mv_ofertaslocales"),
    ("padroninterno", "mv_responsables"),
    ("padroninterno", "mv_localizacion_domicilios"),
    ("padroninterno", "mv_localizacion_historial"),
    ("padroninterno", "mv_establecimiento_historial"),
    ("padroninterno", "mv_oferta_historial"),
    ("padroninterno", "mv_oferta_titulos"),
)

PADRON_REFRESH_JOB_TIMEOUT = 30 * 60
PADRON_REFRESH_JOB_CACHE_PREFIX = "padroninterno_refresh_job"


class RefreshMaterializadasError(Exception):
    status_code = 500


class RefreshMaterializadasLockError(RefreshMaterializadasError):
    status_code = 409


def json_methods_required(*allowed_methods):
    allowed_methods = tuple(method.upper() for method in allowed_methods)

    def _decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.method.upper() not in allowed_methods:
                return JsonResponse(
                    {"status": "error", "message": "Metodo no permitido."},
                    status=405,
                )
            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return _decorator


def _job_cache_key(job_id):
    return f"{PADRON_REFRESH_JOB_CACHE_PREFIX}:{job_id}"


def _estado_base_job(job_id):
    total = len(MATERIALIZED_VIEWS_PADRONINTERNO)
    return {
        "status": "queued",
        "job_id": str(job_id),
        "step": 0,
        "total": total,
        "percent": 0,
        "current_view": "",
        "message": "Refresh de materializadas en cola.",
        "started_monotonic": time.monotonic(),
    }


def _actualizar_estado_job(job_id, **updates):
    key = _job_cache_key(job_id)
    state = cache.get(key) or _estado_base_job(job_id)
    state.update(updates)
    cache.set(key, state, PADRON_REFRESH_JOB_TIMEOUT)
    return state


def _estado_job_para_respuesta(state):
    response = {
        key: value
        for key, value in state.items()
        if key != "started_monotonic"
    }
    started_monotonic = state.get("started_monotonic")
    if started_monotonic and "elapsed_seconds" not in response:
        response["elapsed_seconds"] = round(time.monotonic() - started_monotonic, 2)
    return response


def _mensaje_error_refresh(exc):
    pgerror = getattr(exc, "pgerror", None)
    if pgerror:
        return str(pgerror).strip()

    diag = getattr(exc, "diag", None)
    if diag:
        message_primary = getattr(diag, "message_primary", None)
        if message_primary:
            return str(message_primary).strip()

    return str(exc)


def _limpiar_caches_filtros_padron():
    from . import views_establecimientos, views_localizaciones, views_responsables

    for module in (views_establecimientos, views_localizaciones, views_responsables):
        cache_clear = getattr(getattr(module, "_get_filter_options", None), "cache_clear", None)
        if cache_clear:
            cache_clear()


def _ejecutar_refresh_materializadas_job(job_id, nueva_fecha):
    started_at = time.monotonic()
    locked = False
    total = len(MATERIALIZED_VIEWS_PADRONINTERNO)

    close_old_connections()
    try:
        _actualizar_estado_job(
            job_id,
            status="running",
            step=0,
            total=total,
            percent=0,
            current_view="",
            message="Verificando materializadas...",
        )

        with connections[MATERIALIZADAS_DB].cursor() as cursor:
            cursor.execute("SELECT current_database();")
            database_name = cursor.fetchone()[0]
            if database_name != MATERIALIZADAS_DATABASE_NAME:
                raise RefreshMaterializadasError(
                    f"Refresh abortado: la conexion '{MATERIALIZADAS_DB}' apunta a "
                    f"'{database_name}', no a '{MATERIALIZADAS_DATABASE_NAME}'."
                )

            cursor.execute(
                "SELECT pg_try_advisory_lock(hashtext(%s));",
                [REFRESH_LOCK_NAME],
            )
            locked = bool(cursor.fetchone()[0])
            if not locked:
                _actualizar_estado_job(
                    job_id,
                    status="locked",
                    step=0,
                    total=total,
                    percent=0,
                    current_view="",
                    message="Ya hay un refresh de materializadas en ejecucion.",
                    elapsed_seconds=round(time.monotonic() - started_at, 2),
                )
                return

            missing_views = []
            for schema_name, view_name in MATERIALIZED_VIEWS_PADRONINTERNO:
                regclass_name = f"{schema_name}.{view_name}"
                cursor.execute("SELECT to_regclass(%s);", [regclass_name])
                if cursor.fetchone()[0] is None:
                    missing_views.append(regclass_name)

            if missing_views:
                raise RefreshMaterializadasError(
                    "Refresh abortado: faltan materializadas: " + ", ".join(missing_views)
                )

            for index, (schema_name, view_name) in enumerate(MATERIALIZED_VIEWS_PADRONINTERNO, start=1):
                qualified_name = f"{schema_name}.{view_name}"
                _actualizar_estado_job(
                    job_id,
                    status="running",
                    step=index - 1,
                    total=total,
                    percent=round(((index - 1) * 100) / total),
                    current_view=qualified_name,
                    message=f"Refrescando {qualified_name}...",
                )
                cursor.execute(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {qualified_name};")
                cursor.execute(f"ANALYZE {qualified_name};")
                _actualizar_estado_job(
                    job_id,
                    status="running",
                    step=index,
                    total=total,
                    percent=round((index * 100) / total),
                    current_view=qualified_name,
                    message=f"{qualified_name} refrescada.",
                )

            FechaActualizacionPadronInterno.objects.update_or_create(
                id=1,
                defaults={"fecha": nueva_fecha},
            )

            _limpiar_caches_filtros_padron()

            refresh_metadata = {
                "database": database_name,
                "schema": MATERIALIZADAS_SCHEMA,
                "refreshed_views": total,
                "elapsed_seconds": round(time.monotonic() - started_at, 2),
            }
            _actualizar_estado_job(
                job_id,
                status="success",
                step=total,
                total=total,
                percent=100,
                current_view="",
                message="Fecha actualizada y materializadas refrescadas correctamente.",
                refresh=refresh_metadata,
                elapsed_seconds=refresh_metadata["elapsed_seconds"],
            )
    except Exception as exc:
        _actualizar_estado_job(
            job_id,
            status="error",
            message=_mensaje_error_refresh(exc),
            elapsed_seconds=round(time.monotonic() - started_at, 2),
        )
    finally:
        if locked:
            try:
                with connections[MATERIALIZADAS_DB].cursor() as cursor:
                    cursor.execute(
                        "SELECT pg_advisory_unlock(hashtext(%s));",
                        [REFRESH_LOCK_NAME],
                    )
            except Exception:
                pass
        close_old_connections()

# Contexto compartido por pantallas del padron para mostrar la fecha vigente.
def get_contexto_fecha_padron(request):
    # Se usa id=1 como registro unico de configuracion de fecha.
    obj_fecha = FechaActualizacionPadronInterno.objects.filter(id=1).first()

    return {
        "padron_ultima_fecha": obj_fecha.fecha if obj_fecha else None,
        "padron_fecha_version": obj_fecha.fecha.isoformat() if obj_fecha and obj_fecha.fecha else "",
        "padron_is_admin": usuario_es_admin_padron(request.user),
    }


@padron_interno_required_json
@json_methods_required("GET")
def estado_fecha_padron(request):
    obj_fecha = FechaActualizacionPadronInterno.objects.filter(id=1).first()
    fecha_iso = obj_fecha.fecha.isoformat() if obj_fecha and obj_fecha.fecha else ""

    return JsonResponse({
        "status": "success",
        "fecha_iso": fecha_iso,
        "version": fecha_iso,
    })


@transaction.non_atomic_requests
@padron_interno_admin_required_json
@json_methods_required("POST")
def actualizar_fecha_padron(request):
    # Endpoint JSON: solo acepta POST porque modifica la fecha persistida.
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Método no permitido."}, status=405)

    # Aunque el usuario este logueado, solo Administrador puede actualizarla.
    if not usuario_es_admin_padron(request.user):
        return JsonResponse({"status": "error", "message": "No autorizado."}, status=403)

    try:
        # La fecha llega desde el frontend en formato datetime-local.
        data = json.loads(request.body.decode("utf-8") or "{}")
        nueva_fecha_str = data.get("fecha")

        if not nueva_fecha_str:
            return JsonResponse({"status": "error", "message": "Fecha requerida."}, status=400)

        # Convierte el string a datetime aware para respetar timezone de Django.
        nueva_fecha = timezone.make_aware(
            datetime.datetime.strptime(nueva_fecha_str, "%Y-%m-%dT%H:%M")
        )

        job_id = uuid.uuid4()
        cache.set(_job_cache_key(job_id), _estado_base_job(job_id), PADRON_REFRESH_JOB_TIMEOUT)
        thread = threading.Thread(
            target=_ejecutar_refresh_materializadas_job,
            args=(str(job_id), nueva_fecha),
            daemon=True,
        )
        thread.start()

        return JsonResponse(
            {
                "status": "accepted",
                "job_id": str(job_id),
                "message": "Refresh de materializadas iniciado.",
            },
            status=202,
        )
    except (json.JSONDecodeError, ValueError):
        # Errores esperados: JSON invalido o fecha con formato incorrecto.
        return JsonResponse({"status": "error", "message": "Formato de fecha inválido."}, status=400)
    except Exception as exc:
        # Cualquier otro error se informa al frontend como falla del servidor.
        return JsonResponse({"status": "error", "message": str(exc)}, status=500)


@padron_interno_admin_required_json
@json_methods_required("GET")
def progreso_actualizar_fecha_padron(request, job_id):
    state = cache.get(_job_cache_key(job_id))
    if not state:
        return JsonResponse({"status": "error", "message": "Job no encontrado."}, status=404)

    return JsonResponse(_estado_job_para_respuesta(state))
