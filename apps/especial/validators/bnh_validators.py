# -*- coding: utf-8 -*-
"""Validaciones puras y auxiliares del formato BNH de Educación Especial."""

import re
import unicodedata


def normalizar_texto(valor, *, solo_letras=False):
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    texto = "".join(caracter for caracter in texto if not unicodedata.combining(caracter))
    texto = texto.upper().replace("'", "").replace("’", "").replace(".", "")
    if solo_letras:
        texto = re.sub(r"[^A-ZÁÉÍÓÚÜÑ\s]", "", texto)
    return " ".join(texto.split())


def compactar_texto(valor):
    return re.sub(r"[^A-Z0-9]", "", normalizar_texto(valor))


def validar_documento(cd_tipo_documento, nro_documento):
    """Devuelve el documento normalizado o lanza ValueError."""

    tipo = int(cd_tipo_documento) if cd_tipo_documento is not None else None
    documento = str(nro_documento or "").strip().upper()
    if tipo == 11:
        return ""
    if tipo == 12:
        return documento
    if tipo == 13:
        if documento and not re.fullmatch(r"[A-Z0-9]+", documento):
            raise ValueError("El documento extranjero contiene caracteres inválidos.")
        return documento
    if tipo in {1, 2, 3, 4, 5}:
        if not documento.isdigit():
            raise ValueError("El documento debe contener sólo números.")
        if tipo == 1:
            if len(documento) > 8:
                raise ValueError("El DNI debe tener como máximo 8 dígitos.")
            documento = documento.zfill(8)
        return documento
    if not documento:
        raise ValueError("Falta el documento para el tipo seleccionado.")
    return documento


def validar_cueanexo(cueanexo, padrón_rows, provincias_ids):
    """Valida CUE-Anexo contra las filas activas de Padrón."""

    cue = re.sub(r"\D", "", str(cueanexo or ""))
    if len(cue) != 9:
        raise ValueError("El CUE-Anexo debe tener 9 dígitos.")
    if int(cue[:2]) not in {int(item) for item in provincias_ids}:
        raise ValueError("El prefijo provincial del CUE-Anexo no es válido.")
    if not padrón_rows:
        raise ValueError("El CUE-Anexo no existe o no está activo en Padrón.")
    return cue


def validar_combinaciones_especiales(alumno_id, inscripciones):
    """Aplica las incompatibilidades R6/R7 para un alumno."""

    ofertas = [normalizar_texto(item["oferta"]) for item in inscripciones]
    niveles = set()
    tiene_adultos = False
    tiene_formacion_profesional_adultos = False
    for oferta in ofertas:
        if "INICIAL" in oferta:
            niveles.add("inicial")
        elif "PRIMARIA" in oferta:
            niveles.add("primaria")
        elif "SECUNDARIA" in oferta:
            niveles.add("secundaria")
        if "ADULT" in oferta:
            tiene_adultos = True
        if "FORMACION PROFESIONAL" in oferta and "ADULT" in oferta:
            tiene_formacion_profesional_adultos = True

    if len(niveles) > 1:
        raise ValueError(f"Alumno {alumno_id}: aparece en más de un nivel de Especial.")
    if tiene_adultos and niveles and not tiene_formacion_profesional_adultos:
        raise ValueError(f"Alumno {alumno_id}: combinación Especial/Adultos inválida.")
    if tiene_formacion_profesional_adultos and "inicial" in niveles:
        raise ValueError(f"Alumno {alumno_id}: Formación Profesional de Adultos con Inicial.")
