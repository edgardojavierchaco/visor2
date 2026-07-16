import unicodedata


NIVELES_VALIDOS = {
    "INICIAL": "Inicial",
    "PRIMARIA": "Primaria",
    "SECUNDARIA": "Secundaria",
    "SECUNDARIA_TECNICA": "Secundaria T\u00e9cnica",
    "ESPECIAL": "Educación Especial",
    "FISICA": "Educación Física",
    "ADULTOS": "Adultos",
    "TERCIARIO": "Terciario",
    "BIBLIOTECA": "Biblioteca",
}


def limpiar_texto(valor, max_length=50):
    return str(valor or "").strip()[:max_length]


def normalizar_texto_comparable(valor):
    texto = limpiar_texto(valor).upper()
    return "".join(
        caracter
        for caracter in unicodedata.normalize("NFD", texto)
        if unicodedata.category(caracter) != "Mn"
    )


def normalizar_nivel(valor):
    nivel = limpiar_texto(valor, 30).upper()

    if nivel in NIVELES_VALIDOS:
        return nivel

    nivel_comparable = normalizar_texto_comparable(nivel)

    for codigo, nombre in NIVELES_VALIDOS.items():
        if nivel_comparable == normalizar_texto_comparable(nombre):
            return codigo

    return ""


def es_nivel_valido(valor):
    return bool(normalizar_nivel(valor))


def obtener_nombre_nivel(valor, por_defecto=""):
    return NIVELES_VALIDOS.get(normalizar_nivel(valor), por_defecto)


def obtener_codigo_nivel(valor, por_defecto="PRIMARIA"):
    return normalizar_nivel(valor) or por_defecto


def obtener_nivel_activo(request):
    return normalizar_nivel(request.GET.get("nivel", ""))


def obtener_lista_niveles(incluir_todos=False, orden=None):
    codigos = orden or list(NIVELES_VALIDOS)
    niveles = [(codigo, NIVELES_VALIDOS[codigo]) for codigo in codigos]

    if incluir_todos:
        return [("", "Todos")] + niveles

    return niveles


def obtener_anio_activo(request, por_defecto=2026, permitir_vacio=False):
    anio = limpiar_texto(request.GET.get("anio", ""), 4)

    if anio.isdigit() and len(anio) == 4:
        return anio

    return "" if permitir_vacio else por_defecto
