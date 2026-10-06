# -*- coding: utf-8 -*-
"""Consultas y validaciones de cargos BNH utilizables en Educación Especial."""

import re
import unicodedata

from django.conf import settings
from apps.bnhpersonas.models import RegistroActividades


def cargos_especiales_docente(cuil, cueanexo):
    """Devuelve cargos BNH validados de modalidad ESPECIAL para un docente/CUE."""
    cuil = re.sub(r"\D", "", str(cuil or ""))
    cueanexo = re.sub(r"\D", "", str(cueanexo or ""))
    filtros = {
        "persona__cuil": str(cuil or "").strip(),
        "cueanexo": str(cueanexo or "").strip(),
        "eliminado": False,
        "modalidad__descrip_modalidad__iexact": "ESPECIAL",
    }
    if getattr(settings, "ESPECIAL_REQUIERE_CARGO_VALIDADO", True):
        filtros["validacion"] = "VALIDADO"
    return (
        RegistroActividades.objects
        .select_related("persona", "modalidad", "ceic", "sit_revista", "nivel_curricular")
        .filter(**filtros)
        .order_by("id")
    )


def cargo_especial_valido(cuil, cueanexo, cargo_id):
    return cargos_especiales_docente(cuil, cueanexo).filter(pk=cargo_id).first()


def texto_cargo(cargo):
    """Texto corto y estable para mostrar un cargo en formularios e historial."""
    ceic = getattr(getattr(cargo, "ceic", None), "descripcion", "") or "Sin CEIC"
    revista = getattr(getattr(cargo, "sit_revista", None), "descrip_sitrev", "") or "Sin situación"
    nivel = getattr(getattr(cargo, "nivel_curricular", None), "descripcion", "") or "Sin oferta"
    turno = cargo.turno or "Sin turno"
    return f"{ceic} · {nivel} · {turno} · {revista}"


def _normalizar_comparacion(valor):
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r"[^a-z0-9]+", " ", texto.casefold()).strip()
    return texto


def _ofertas_equivalentes(oferta_seccion, nivel_cargo):
    seccion = _normalizar_comparacion(oferta_seccion)
    cargo = _normalizar_comparacion(nivel_cargo)
    for prefijo in ("especial ", "especial - "):
        if seccion.startswith(prefijo):
            seccion = seccion[len(prefijo):].strip()
        if cargo.startswith(prefijo):
            cargo = cargo[len(prefijo):].strip()
    return bool(seccion and cargo) and (seccion == cargo or seccion in cargo or cargo in seccion)


def comparar_cargos_con_seccion(cargos, seccion):
    """Clasifica cargos del docente contra oferta y turno de una sección."""
    turno_seccion = _normalizar_comparacion(getattr(seccion.turno, "descripcion", seccion.turno))
    resultado = []
    for cargo in cargos:
        nivel = getattr(getattr(cargo, "nivel_curricular", None), "descripcion", "")
        turno = _normalizar_comparacion(cargo.turno)
        oferta_ok = _ofertas_equivalentes(seccion.oferta, nivel)
        turno_ok = bool(turno_seccion and turno and turno_seccion == turno)
        if oferta_ok and turno_ok:
            estado = "coincide"
        elif oferta_ok:
            estado = "oferta_coincide_turno_difiere"
        else:
            estado = "oferta_difiere"
        resultado.append({"cargo": cargo, "oferta_ok": oferta_ok, "turno_ok": turno_ok, "estado": estado})
    return resultado


def comparar_cargo_con_seccion(cargo, seccion):
    """Devuelve la comparación de un cargo individual contra una sección."""
    for item in comparar_cargos_con_seccion([cargo], seccion):
        return item
    return None


def rol_desde_situacion_revista(cargo):
    """Mapea la situación de revista BNH al rol operativo de Especial."""
    descripcion = _normalizar_comparacion(
        getattr(getattr(cargo, "sit_revista", None), "descrip_sitrev", "")
    )
    if "suplente" in descripcion:
        return "suplente"
    if "interino" in descripcion or "interina" in descripcion:
        return "interino"
    if "titular" in descripcion:
        return "titular"
    return None
