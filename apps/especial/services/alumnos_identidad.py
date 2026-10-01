# -*- coding: utf-8 -*-
"""Resolución de identidad de alumnos usada exclusivamente por Especial.

Este módulo mantiene desacoplado el flujo de Especial de las vistas de CEF.
Las consultas a BNH son de lectura; la única URL de escritura que se genera
es la pantalla existente de carga/edición de BNH Alumnos.
"""

import re
from urllib.parse import urlencode

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import connections
from django.urls import NoReverseMatch, reverse

from apps.bnhalumnos.models import (
    Alumno,
    normalizar_cuil_opcional,
    normalizar_documento_bnh,
    validar_cuil_con_documento,
)
from apps.bnhpersonas.models import DocumentoTipo, Sexo


SGE_PERSONAS_MATERIALIZADA = "public.personas_alumnos_sge"
SGE_TIPOS_DOCUMENTO_EXTRANJERO = (8, 9, 10)
SGE_TIPO_DOCUMENTO_A_BNH = {
    1: 1,
    2: 2,
    3: 3,
    4: 4,
    5: 5,
    8: 13,
    9: 13,
    10: 13,
    11: 11,
    12: 12,
}


def _solo_digitos(valor):
    return re.sub(r"\D", "", str(valor or ""))


def _entero(valor):
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


def _tipo_documento(tipo_doc):
    if isinstance(tipo_doc, DocumentoTipo):
        return tipo_doc
    tipo_id = _entero(getattr(tipo_doc, "pk", tipo_doc))
    if not tipo_id:
        raise ValidationError("El tipo de documento seleccionado no es válido.")
    resultado = DocumentoTipo.objects.filter(pk=tipo_id).first()
    if not resultado:
        raise ValidationError("El tipo de documento seleccionado no existe.")
    return resultado


def _normalizar_identidad(*, tipo_doc, nro_doc="", cuil=""):
    tipo_doc = _tipo_documento(tipo_doc)
    nro_doc = normalizar_documento_bnh(tipo_doc, nro_doc)
    cuil = normalizar_cuil_opcional(cuil, "CUIL") or ""
    validar_cuil_con_documento(cuil, tipo_doc, nro_doc, "CUIL")
    return tipo_doc, nro_doc or "", cuil


def _alumnos_por_identidad(*, tipo_doc, nro_doc="", cuil=""):
    ids = set()
    if cuil:
        ids.update(Alumno.objects.filter(cuil=cuil).values_list("pk", flat=True))
    if nro_doc:
        ids.update(
            Alumno.objects.filter(
                tipo_doc_id=tipo_doc.pk,
                nro_doc__iexact=nro_doc,
            ).values_list("pk", flat=True)
        )
    if not ids:
        return []
    return list(
        Alumno.objects.filter(pk__in=ids)
        .select_related("tipo_doc", "sexo")
        .order_by("pk")
    )


def _texto(valor):
    return "" if valor is None else str(valor)


def _alumno_por_id(alumno_id):
    alumno_id = _entero(alumno_id)
    if not alumno_id:
        return None
    return (
        Alumno.objects.filter(pk=alumno_id)
        .select_related("tipo_doc", "sexo")
        .first()
    )


def _buscar_alumno_sin_documento(*, apellidos, nombres, fecha_nacimiento, sexo, tipo_doc):
    """Busca solo coincidencias exactas de personas sin número documental."""
    tipo_doc = _tipo_documento(tipo_doc)
    if not (apellidos and nombres and fecha_nacimiento and sexo):
        raise ValidationError(
            "Para buscar un alumno sin número de documento debe completar apellido, nombre, fecha de nacimiento y sexo."
        )
    sexo_id = _entero(getattr(sexo, "pk", sexo))
    candidatos = list(
        Alumno.objects.filter(
            tipo_doc=tipo_doc,
            nro_doc__in=[None, ""],
            apellidos__iexact=str(apellidos).strip(),
            nombres__iexact=str(nombres).strip(),
            fecha_nacimiento=fecha_nacimiento,
            sexo_id=sexo_id,
        )
        .select_related("tipo_doc", "sexo")
        .order_by("pk")
    )
    if len(candidatos) > 1:
        raise ValidationError(
            "Los datos ingresados coinciden con más de un alumno sin documento. No se seleccionó ninguno automáticamente."
        )
    return candidatos[0] if candidatos else None


def _aliases_sge():
    aliases = []
    configurado = str(getattr(settings, "BNHALUMNOS_SGE_DB_ALIAS", "") or "").strip()
    if configurado:
        aliases.append(configurado)
    if "sge_nacion" not in aliases:
        aliases.append("sge_nacion")
    return aliases


def _sge_alias():
    for alias in _aliases_sge():
        if alias not in connections.databases:
            continue
        try:
            with connections[alias].cursor() as cursor:
                cursor.execute("SELECT to_regclass(%s)", [SGE_PERSONAS_MATERIALIZADA])
                if cursor.fetchone()[0]:
                    return alias
        except Exception:
            continue
    return None


def _buscar_personas_sge(*, tipo_doc, nro_doc="", cuil=""):
    condiciones = []
    params = []
    if cuil:
        condiciones.append(
            "REGEXP_REPLACE(COALESCE(p.cuil::text, ''), '[^0-9]', '', 'g') = %s"
        )
        params.append(cuil)
    if tipo_doc and nro_doc:
        tipos_sge = (
            SGE_TIPOS_DOCUMENTO_EXTRANJERO
            if int(tipo_doc.pk) == 13
            else (int(tipo_doc.pk),)
        )
        placeholders = ", ".join(["%s"] * len(tipos_sge))
        if int(tipo_doc.pk) == 1:
            comparacion = (
                "LPAD(REGEXP_REPLACE(COALESCE(p.nro_documento::text, ''), '[^0-9]', '', 'g'), 8, '0') = %s"
            )
        elif int(tipo_doc.pk) in {2, 3, 4, 5}:
            comparacion = (
                "REGEXP_REPLACE(COALESCE(p.nro_documento::text, ''), '[^0-9]', '', 'g') = %s"
            )
        else:
            comparacion = "UPPER(BTRIM(COALESCE(p.nro_documento::text, ''))) = %s"
        condiciones.append(
            f"(p.c_tipo_documento IN ({placeholders}) AND {comparacion})"
        )
        params.extend(tipos_sge)
        params.append(nro_doc)
    if not condiciones:
        return []
    alias = _sge_alias()
    if not alias:
        raise ValidationError(
            "No se pudo consultar la fuente SGE para verificar la identidad del alumno. No se asumió que la persona esté ausente."
        )
    sql = f"""
        SELECT p.id_persona, p.apellido, p.nombre, p.c_tipo_documento,
               p.nro_documento, p.cuil, p.fecha_nacimiento, p.c_sexo,
               p.lugar_nacimiento
        FROM {SGE_PERSONAS_MATERIALIZADA} p
        WHERE {" OR ".join(condiciones)}
        ORDER BY p.id_persona
        LIMIT 3
    """
    try:
        with connections[alias].cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()
    except Exception as exc:
        raise ValidationError(
            "No se pudo consultar la fuente SGE para verificar la identidad del alumno. No se asumió que la persona esté ausente."
        ) from exc


def _persona_sge_payload(fila):
    id_persona, apellido, nombre, tipo_sge, nro_doc, cuil, fecha, sexo, lugar = fila
    tipo_bnh = SGE_TIPO_DOCUMENTO_A_BNH.get(_entero(tipo_sge))
    tipo_obj = DocumentoTipo.objects.filter(pk=tipo_bnh).first() if tipo_bnh else None
    sexo_obj = Sexo.objects.filter(pk=_entero(sexo)).first() if _entero(sexo) else None
    return {
        "id_persona_sge": id_persona,
        "apellidos": _texto(apellido).strip(),
        "nombres": _texto(nombre).strip(),
        "tipo_doc": _texto(tipo_obj),
        "tipo_doc_id": tipo_bnh or "",
        "nro_doc": _texto(nro_doc).strip(),
        "cuil": _solo_digitos(cuil),
        "fecha_nac": fecha,
        "sexo": _texto(sexo_obj),
        "sexo_id": _entero(sexo) or "",
        "lugar_nac": _texto(lugar).strip(),
    }


def _persona_sge_row(persona):
    return persona


def _resolver_persona_sge(*, tipo_doc, nro_doc="", cuil=""):
    filas = _buscar_personas_sge(tipo_doc=tipo_doc, nro_doc=nro_doc, cuil=cuil)
    personas = {fila[0]: fila for fila in filas}
    if len(personas) > 1:
        raise ValidationError(
            "Los identificadores ingresados coinciden con más de una persona en SGE. Revise CUIL y documento antes de continuar."
        )
    if not personas:
        return None
    return _persona_sge_payload(next(iter(personas.values())))


def _resolver_alumno_o_sge(*, tipo_doc, nro_doc="", cuil=""):
    tipo_doc, nro_doc, cuil = _normalizar_identidad(
        tipo_doc=tipo_doc,
        nro_doc=nro_doc,
        cuil=cuil,
    )
    candidatos = _alumnos_por_identidad(
        tipo_doc=tipo_doc,
        nro_doc=nro_doc,
        cuil=cuil,
    )
    if len(candidatos) > 1:
        raise ValidationError(
            "Los identificadores ingresados coinciden con más de un alumno. No se seleccionó ninguno automáticamente."
        )
    if candidatos:
        return candidatos[0], None
    return None, _resolver_persona_sge(
        tipo_doc=tipo_doc,
        nro_doc=nro_doc,
        cuil=cuil,
    )


def _url_carga_alumno(
    next_url,
    return_label="Volver",
    *,
    alumno=None,
    tipo_doc="",
    nro_doc="",
    cuil="",
    apellidos="",
    nombres="",
    fecha_nacimiento="",
    sexo="",
):
    try:
        base = reverse("bnhalumnos:carga_alumno")
    except NoReverseMatch:
        return ""
    params = {}
    if alumno is not None and getattr(alumno, "pk", None):
        params["alumno_id"] = alumno.pk
    for key, value in (
        ("tipo_doc", getattr(tipo_doc, "pk", tipo_doc)),
        ("nro_doc", nro_doc),
        ("cuil", cuil),
        ("apellidos", apellidos),
        ("nombres", nombres),
        ("fecha_nacimiento", fecha_nacimiento),
        ("sexo", getattr(sexo, "pk", sexo)),
    ):
        if value not in (None, ""):
            params[key] = value.isoformat() if hasattr(value, "isoformat") else value
    if next_url:
        params["next"] = next_url
    if return_label:
        params["return_label"] = return_label
    return f"{base}?{urlencode(params)}" if params else base
