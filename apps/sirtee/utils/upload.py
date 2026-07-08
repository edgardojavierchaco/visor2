import os
import re
import uuid
from datetime import date


def upload_hallazgo(instance, filename):
    """
    Ruta:
    sirtee/hallazgos/<año>/<mes>/<hallazgo_id>/<uuid>_<nombre>.ext
    """

    hoy = date.today()

    nombre, extension = os.path.splitext(filename)

    # Normaliza el nombre para evitar caracteres problemáticos
    nombre = re.sub(
        r"[^a-zA-Z0-9_-]",
        "_",
        nombre
    )

    # Evita nombres vacíos
    if not nombre:
        nombre = "archivo"


    nombre_final = (
        f"{uuid.uuid4().hex}_"
        f"{nombre}"
        f"{extension.lower()}"
    )


    # Protección cuando el hallazgo todavía no tiene ID
    hallazgo_id = (
        instance.hallazgo_id
        if instance.hallazgo_id
        else "pendiente"
    )


    return (
        f"sirtee/"
        f"hallazgos/"
        f"{hoy.year}/"
        f"{hoy.month:02d}/"
        f"{hallazgo_id}/"
        f"{nombre_final}"
    )