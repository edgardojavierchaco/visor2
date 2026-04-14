import redis
import json
import os
from celery import shared_task
from django.db import close_old_connections
from apps.usuarios.services.sync_usuarios import sync_usuarios_directores

r = redis.from_url(
    os.environ.get("REDIS_URL"),
    decode_responses=True
)


@shared_task(bind=True, acks_late=True)
def sync_usuarios_task(self):

    close_old_connections()

    # 🔥 limpiar stream anterior
    r.delete("sync_stream")
    r.set("sync_estado", "procesando")

    def push_event(data):
        r.rpush("sync_stream", json.dumps(data))
        r.ltrim("sync_stream", -1000, -1)  # evitar crecimiento infinito

    try:
        push_event({"estado": "procesando", "msg": "inicio"})

        for u in sync_usuarios_directores():

            # eventos generales (inicio, fin, error, cancelado)
            if "tipo" not in u:
                push_event(u)
                continue

            # eventos por fila
            push_event({
                "tipo": "fila",
                "username": u.get("username"),
                "estado": u.get("estado"),
                "msg": u.get("msg", ""),
                "n": u.get("n")
            })

        push_event({"estado": "finalizado"})
        r.set("sync_estado", "finalizado")

        return {"ok": True}

    except Exception as e:
        r.set("sync_estado", "error")
        push_event({"estado": "error", "msg": str(e)})
        raise

    finally:
        close_old_connections()