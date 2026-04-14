from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse, StreamingHttpResponse
from django.views.decorators.http import require_POST
from django.core.cache import cache
from django.views.decorators.csrf import csrf_protect
from django.conf import settings

from apps.usuarios.models import SyncLog, SyncControl, UsuarioRechazadoLog
from apps.usuarios.tasks import sync_usuarios_task
from apps.usuarios.constants import CACHE_PROGRESS_KEY, CACHE_CANCEL_KEY

import openpyxl
import redis
import time
import json


# =========================
# 🔌 REDIS (GLOBAL)
# =========================
r = redis.from_url(settings.REDIS_URL, decode_responses=True)


# =========================================
# 📊 DASHBOARD
# =========================================
@staff_member_required
def estado_sync(request):

    logs = SyncLog.objects.all().order_by("-inicio")[:20]
    control = SyncControl.objects.filter(nombre="directores").first()

    return render(request, "usuarios/sync/estado_sync.html", {
        "logs": logs,
        "control": control
    })


# =========================================
# 🚀 INICIAR SYNC
# =========================================
@staff_member_required
def iniciar_sync(request):

    progreso = cache.get(CACHE_PROGRESS_KEY)

    if progreso and progreso.get("estado") == "procesando":
        return JsonResponse({"status": "ya_en_ejecucion"})

    # reset cancel flag
    cache.set(CACHE_CANCEL_KEY, False, timeout=3600)

    task = sync_usuarios_task.delay()

    return JsonResponse({
        "status": "iniciado",
        "task_id": task.id
    })


# =========================================
# 📈 PROGRESO
# =========================================
@staff_member_required
def progreso_sync(request):

    data = cache.get(CACHE_PROGRESS_KEY, {
        "estado": "idle",
        "procesados": 0,
        "total": 0
    })

    return JsonResponse(data)


# =========================================
# 📥 EXPORTAR EXCEL
# =========================================
@staff_member_required
def exportar_rechazados_excel(request):

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Rechazados"

    ws.append(["Username", "Motivo", "Payload", "Fecha"])

    qs = UsuarioRechazadoLog.objects.all().order_by("-created_at")[:1000]

    for obj in qs:
        ws.append([
            obj.username,
            obj.motivo,
            str(obj.payload),
            obj.created_at.strftime("%Y-%m-%d %H:%M:%S")
        ])

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    response["Content-Disposition"] = 'attachment; filename="usuarios_rechazados.xlsx"'

    wb.save(response)
    return response


# =========================
# 🧹 LIMPIAR HISTORIAL
# =========================
@staff_member_required
@require_POST
def limpiar_historial(request):
    SyncLog.objects.all().delete()
    return JsonResponse({"status": "ok"})


# =========================
# ⛔ CANCELAR SYNC
# =========================
@staff_member_required
@csrf_protect
@require_POST
def cancelar_sync(request):

    cache.set(CACHE_CANCEL_KEY, True, timeout=3600)

    cache.set(CACHE_PROGRESS_KEY, {
        "estado": "cancelando"
    }, timeout=3600)

    # 🔥 importante para SSE
    r.set("sync_estado", "cancelado")

    return JsonResponse({"status": "cancel_requested"})


# =========================
# 📡 STREAM SSE
# =========================
@staff_member_required
def sync_stream(request):

    def event_stream():
        last_index = 0

        while True:
            try:
                items = r.lrange("sync_stream", last_index, -1)

                if items:
                    for item in items:
                        yield f"data: {item}\n\n"
                        last_index += 1

                # 🔥 cortar automáticamente
                estado = r.get("sync_estado")
                if estado in ["finalizado", "error", "cancelado"]:
                    yield f"data: {json.dumps({'estado': estado})}\n\n"
                    break

                time.sleep(0.5)

            except GeneratorExit:
                # cliente cerró conexión
                break

    response = StreamingHttpResponse(
        event_stream(),
        content_type="text/event-stream"
    )

    response["Cache-Control"] = "no-cache"
    return response