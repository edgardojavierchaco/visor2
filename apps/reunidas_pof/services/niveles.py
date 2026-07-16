import unicodedata


MATRIZ_COMPATIBILIDAD_REUNIDA = {
    "INICIAL": {
        "ofertas": {"INICIAL"},
        "ceic": {"INICIAL"},
    },
    "PRIMARIA": {
        "ofertas": {"EEP"},
        "ceic": {"PRIMARIO"},
    },
    "SECUNDARIA": {
        "ofertas": {"EES", "EET/EFP"},
        "ceic": {"SECUNDARIO"},
    },
    "SECUNDARIA_TECNICA": {
        "ofertas": {"EES", "EET/EFP"},
        "ceic": {"TÉCNICA"},
    },
    "ESPECIAL": {
        "ofertas": {"EEESPEC"},
        "ceic": {"ESPECIAL"},
    },
    "ADULTOS": {
        "ofertas": {"EPA"},
        "ceic": {"ADULTO"},
    },
    "FISICA": {
        "ofertas": {"CEF", "BIBLIO/CEF"},
        "ceic": {"EDUCACIÓN FÍSICA"},
    },
    "BIBLIOTECA": {
        "ofertas": {"BIBLIOTECAS", "BIBLIO/CEF"},
        "ceic": {"BIBLIOTECAS"},
    },
    "TERCIARIO": {
        "ofertas": {"SUPERIOR"},
        "ceic": {"SUPERIOR", "ARTÍSTICA"},
    },
}


OFERTAS_PADRON_POR_NOMENCLATURA = {
    "INICIAL": {
        "Común - Jardín maternal",
        "Común - Jardín de infantes",
        "Común - Domiciliaria-hospitalaria. Nivel Inicial",
    },
    "EEP": {
        "EEP",
        "Común - Primaria de 7 años",
        "Común - Domiciliaria-hospitalaria. Nivel Primario/EGB",
    },
    "EES": {
        "EES",
        "Adultos - Secundaria Completa",
        "Común - Secundaria Completa req. 7 años",
    },
    "EET/EFP": {
        "EET",
        "EFP",
        "Adultos - Formación Profesional",
    },
    "EEESPEC": {
        "EEESPEC",
        "Especial - Cursos/Talleres de la Escuela Especial",
        "Especial - Domiciliaria-hospitalaria. Nivel Inicial",
        "Especial - Domiciliaria-hospitalaria. Nivel Primario/EGB",
        "Especial - Educacion integral para adolescentes y jovenes",
        "Especial - Integración",
        "Especial - Jardín de infantes",
        "Especial - Jardín maternal",
        "Especial - Primaria de 7 años",
        "Especial - Taller de Educación Integral para Adolescentes y Jóvenes/Secundario Especial (ex Talleres de Secundaria/Polimodal)",
    },
    "EPA": {
        "Adultos - Primaria",
    },
    "BIBLIO/CEF": {
        "Común - Servicios complementarios",
    },
    "SUPERIOR": {
        "Común - SNU",
        "Común - Ciclos de Enseñanza Artística",
        "Común - Cursos de Capacitación de SNU",
        "Común - Cursos y Talleres de Artística",
    },
}


def normalizar_texto(valor):
    """
    Normaliza texto solo para comparar compatibilidad de niveles y ofertas.

    - Tolera mayúsculas, minúsculas, tildes y espacios accidentales.
    - No modifica los datos reales; devuelve una clave comparable en mayúsculas.
    - Mantiene caracteres de puntuación útiles como la barra de BIBLIO/CEF.
    """
    texto = str(valor or "").strip().upper()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(caracter for caracter in texto if unicodedata.category(caracter) != "Mn")
    return " ".join(texto.split())


def _normalizar_clave(valor):
    return normalizar_texto(valor)


def _conjunto_normalizado(valores):
    return {_normalizar_clave(valor) for valor in valores}


def obtener_nomenclaturas_oferta_para_reunida(nivel_reunida):
    """
    Devuelve las nomenclaturas de padrón compatibles con una Reunida.

    - Centraliza el criterio de oferta permitida por nivel de cabecera.
    - Devuelve un conjunto vacío si el nivel no es reconocido.
    - Para TERCIARIO, la oferta permitida queda asociada a SUPERIOR.
    """
    nivel = _normalizar_clave(nivel_reunida)
    if nivel not in MATRIZ_COMPATIBILIDAD_REUNIDA:
        return set()
    return set(MATRIZ_COMPATIBILIDAD_REUNIDA[nivel]["ofertas"])


def obtener_niveles_ceic_para_reunida(nivel_reunida):
    """
    Devuelve los niveles CEIC compatibles con una Reunida.

    - Centraliza el criterio de CEIC admitido por nivel de cabecera.
    - Devuelve un conjunto vacío si el nivel no es reconocido.
    - Para TERCIARIO admite CEIC SUPERIOR y ARTÍSTICA.
    """
    nivel = _normalizar_clave(nivel_reunida)
    if nivel not in MATRIZ_COMPATIBILIDAD_REUNIDA:
        return set()
    return set(MATRIZ_COMPATIBILIDAD_REUNIDA[nivel]["ceic"])


def clasificar_oferta_padron(oferta, *alternativas):
    """
    Clasifica una oferta del padrón en su nomenclatura central de compatibilidad.

    - Usa texto normalizado para reconocer acrónimos, variantes con tildes o espacios.
    - Revisa la oferta principal y alternativas reales del padrón, como acrónimo o tipo de oferta.
    - Devuelve la nomenclatura permitida por la matriz central.
    - Devuelve cadena vacía si la oferta no está contemplada.
    """
    for valor in (oferta, *alternativas):
        oferta_normalizada = _normalizar_clave(valor)
        if not oferta_normalizada:
            continue
        for nomenclatura, ofertas in OFERTAS_PADRON_POR_NOMENCLATURA.items():
            if oferta_normalizada in _conjunto_normalizado(ofertas):
                return nomenclatura
    return ""


def oferta_es_compatible_con_reunida(oferta, nivel_reunida, *alternativas):
    """
    Indica si una oferta del padrón es compatible con la Reunida indicada.

    - Primero clasifica la oferta, acrónimo o alternativa en una nomenclatura central.
    - Luego compara contra las nomenclaturas permitidas para la cabecera.
    - SECUNDARIA y SECUNDARIA_TECNICA comparten EES, EET y EFP como ofertas sugeridas.
    - BIBLIO/CEF es compatible con FISICA y BIBLIOTECA.
    """
    nomenclatura = clasificar_oferta_padron(oferta, *alternativas)
    if not nomenclatura:
        return False

    return nomenclatura in obtener_nomenclaturas_oferta_para_reunida(nivel_reunida)


def nivel_ceic_es_compatible_con_reunida(nivel_ceic, nivel_reunida):
    """
    Indica si un nivel CEIC es compatible con la Reunida indicada.

    - Compara texto normalizado para tolerar diferencias de escritura.
    - TERCIARIO acepta CEIC SUPERIOR y ARTÍSTICA.
    - No altera datos persistidos ni depende de base de datos.
    """
    nivel_ceic_normalizado = _normalizar_clave(nivel_ceic)
    return nivel_ceic_normalizado in _conjunto_normalizado(
        obtener_niveles_ceic_para_reunida(nivel_reunida)
    )
