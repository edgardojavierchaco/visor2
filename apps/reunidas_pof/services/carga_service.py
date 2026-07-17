from ..models import ReunidaPof
from .niveles_service import (
    normalizar_nivel,
    obtener_anio_activo,
    obtener_lista_niveles,
    obtener_nivel_activo,
    obtener_nombre_nivel,
)


ORDEN_NIVELES_CARGA = [
    "PRIMARIA",
    "SECUNDARIA",
    "SECUNDARIA_TECNICA",
    "INICIAL",
    "ADULTOS",
    "TERCIARIO",
    "BIBLIOTECA",
    "ESPECIAL",
    "FISICA",
]


def obtener_anios_reunidas_disponibles():
    return [
        str(anio)
        for anio in ReunidaPof.objects.order_by("-anio").values_list("anio", flat=True).distinct()
        if anio is not None
    ]


def construir_contexto_carga(request):
    """
    Construye el contexto minimo para la pantalla definitiva de carga de Reunida.

    - Mantiene la seleccion contextual de anio y nivel cuando llegan por GET.
    - Entrega solo los catalogos necesarios para validar una cabecera de Reunida.
    - No resuelve Proyecto Especial porque ese flujo usa su vista especializada.
    """
    nivel_activo = obtener_nivel_activo(request)
    tiene_contexto = bool(request.GET.get("anio") and request.GET.get("nivel"))
    anios_reunida = obtener_anios_reunidas_disponibles()

    anio_reunida_activo = obtener_anio_activo(request, permitir_vacio=True)
    if anio_reunida_activo not in anios_reunida:
        anio_reunida_activo = anios_reunida[0] if anios_reunida else ""

    return {
        "anio_activo": anio_reunida_activo,
        "anios_reunida": anios_reunida,
        "niveles": obtener_lista_niveles(orden=ORDEN_NIVELES_CARGA),
        "nivel_activo": nivel_activo,
        "nivel_codigo": nivel_activo if tiene_contexto else "",
    }


def validar_cabecera_reunida(anio, nivel):
    errores = {}
    anio_texto = str(anio or "").strip()

    if not anio_texto:
        errores["anio"] = ["El año es obligatorio."]
    elif not anio_texto.isdigit() or len(anio_texto) != 4:
        errores["anio"] = ["El año debe tener 4 dígitos numéricos."]

    nivel_normalizado = normalizar_nivel(nivel)
    if not nivel_normalizado:
        errores["nivel"] = ["El nivel ingresado no es válido."]

    if errores:
        return {
            "ok": False,
            "mensaje": "Hay errores en la Cabecera de Reunida.",
            "errores": errores,
        }

    reunida = ReunidaPof.objects.filter(anio=int(anio_texto), nivel=nivel_normalizado).first()
    if not reunida:
        return {
            "ok": False,
            "mensaje": "No existe una Reunida POF para ese año y nivel. Primero debe crearla.",
            "errores": {"reunida": ["No existe una Reunida POF para ese año y nivel."]},
        }

    return {
        "ok": True,
        "mensaje": "Cabecera de Reunida validada.",
        "reunida": {
            "id": reunida.id,
            "anio": reunida.anio,
            "nivel": reunida.nivel,
            "nivel_nombre": obtener_nombre_nivel(reunida.nivel, reunida.get_nivel_display()),
        },
    }
