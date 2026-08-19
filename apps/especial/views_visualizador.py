# -*- coding: utf-8 -*-
"""Visualizador global de personas y establecimientos para administradores."""

import re
import logging
from types import SimpleNamespace
from urllib.parse import urlencode

from django.apps import apps
from django.core.paginator import Paginator
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import connections
from django.db.models import CharField, F, Func, Prefetch, Q, Subquery, Value
from django.db.utils import OperationalError, ProgrammingError
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse

from apps.bnhpersonas.models import Personas, validar_cuil

from .models import (
    AlumnoSeccion,
    CatalogoTipoEstructuraEspecial,
    DocenteSeccion,
    EspecialAlumnoBanco,
    EspecialCiclo,
    EspecialDocenteBanco,
    EspecialDocenteBnh,
    EspecialPadronOferta,
    ModalidadDictadoTipo,
    PADRON_DB_ALIAS,
    SeccionEspecial,
    TurnoTipo,
)
from .permisos import especial_required, get_permisos_especial_request
from .views_contexto import contexto_base


logger = logging.getLogger(__name__)

VISUALIZADOR_ALUMNOS_PAGE_SIZE = 25
VISUALIZADOR_PRUEBA_LIMITE = 10
FILTROS_ALUMNOS_QUERYSTRING = {
    "modo",
    "cuil",
    "filtro_cueanexo",
    "establecimiento",
    "localidad",
    "estado",
    "departamento",
    "filtro_ciclo",
    "modalidad",
    "nivel",
    "seccion",
    "turno",
}

FILTROS_DOCENTES_QUERYSTRING = {
    "cuil",
    "filtro_cueanexo",
    "establecimiento",
    "localidad",
    "estado",
    "departamento",
    "filtro_ciclo",
    "modalidad",
    "nivel",
    "seccion",
    "turno",
    "rol",
}


TIPOS_BUSQUEDA = {"alumno", "docente", "director"}


def _solo_digitos(valor):
    return re.sub(r"\D", "", str(valor or ""))


def _alumno_model():
    return apps.get_model("bnhalumnos", "Alumno")


def _es_administrador(request):
    return bool(get_permisos_especial_request(request).get("es_admin"))


def _exigir_administrador(request):
    if not _es_administrador(request):
        raise PermissionDenied("El Visualizador Global es exclusivo para administradores.")


def _texto(valor):
    return "" if valor is None else str(valor)


def _es_modo_prueba(request):
    return (
        (request.GET.get("modo") or "").strip().lower() == "prueba"
        or (request.GET.get("prueba") or "").strip().lower()
        in {"1", "si", "sí", "true"}
    )


def _solicita_alumnos_prueba(request):
    return (request.GET.get("agregar_prueba") or "").strip() == "1"


def _relacion_texto(objeto, *atributos):
    if not objeto:
        return ""
    for atributo in atributos:
        valor = getattr(objeto, atributo, None)
        if valor not in (None, ""):
            return _texto(valor)
    return _texto(objeto)


def _personas_bnh_queryset():
    """Consulta bnh.personas mediante el modelo compartido de BNH."""
    return (
        Personas.objects.using(PADRON_DB_ALIAS)
        .select_related("sexo", "localidad", "codigo_area")
    )


def _filtros_alumnos(request):
    """Normaliza únicamente los filtros operativos permitidos."""
    filtros = {
        "cuil": _solo_digitos(request.GET.get("cuil")),
        "cueanexo": _solo_digitos(request.GET.get("filtro_cueanexo")),
        "establecimiento": (request.GET.get("establecimiento") or "").strip(),
        "localidad": (request.GET.get("localidad") or "").strip(),
        "departamento": (request.GET.get("departamento") or "").strip(),
        "ciclo": (request.GET.get("filtro_ciclo") or "").strip(),
        "modalidad": (request.GET.get("modalidad") or "").strip(),
        "nivel": (request.GET.get("nivel") or "").strip(),
        "seccion": (request.GET.get("seccion") or "").strip(),
        "turno": (request.GET.get("turno") or "").strip(),
        "estado": (request.GET.get("estado") or "todos").strip().lower(),
    }
    errores = {}

    if request.GET.get("cuil") and len(filtros["cuil"]) != 11:
        errores["cuil"] = "El CUIL debe contener exactamente 11 dígitos."
    elif filtros["cuil"]:
        try:
            validar_cuil(filtros["cuil"])
        except ValidationError:
            errores["cuil"] = "El CUIL no tiene un dígito verificador válido."
    if request.GET.get("cueanexo") and len(filtros["cueanexo"]) != 9:
        errores["cueanexo"] = "El CUE-Anexo debe contener exactamente 9 dígitos."

    estados_validos = {
        estado
        for estado, _ in EspecialAlumnoBanco.Estado.choices
    } | {"todos"}
    if filtros["estado"] not in estados_validos:
        filtros["estado"] = "todos"

    for key in ("ciclo", "modalidad", "nivel", "seccion", "turno"):
        if filtros[key] and not filtros[key].isdigit():
            errores[key] = "Seleccioná una opción válida."

    return filtros, errores


def _padron_especial_queryset():
    """Filas de Padrón vinculadas a establecimientos de Educación Especial."""
    return (
        EspecialPadronOferta.objects.using(PADRON_DB_ALIAS)
        .filter(acronimo__iexact="EEE")
    )


def _padron_cues_para_filtros(filtros):
    """Obtiene CUE-Anexos de Especial para filtros de establecimiento/localidad."""
    if not any(
        filtros[key] for key in ("establecimiento", "localidad", "departamento")
    ):
        return None

    queryset = _padron_especial_queryset()
    if filtros["establecimiento"]:
        queryset = queryset.filter(nom_est__icontains=filtros["establecimiento"])
    if filtros["localidad"]:
        queryset = queryset.filter(localidad__icontains=filtros["localidad"])
    if filtros["departamento"]:
        queryset = queryset.filter(departamento__icontains=filtros["departamento"])
    return queryset.values("cueanexo").distinct()


def _section_filter_kwargs(
    filtros,
    padron_cues=None,
    *,
    include_cue=True,
    include_ciclo=True,
):
    """Filtros sobre SeccionEspecial, sin resolver relaciones en Python."""
    kwargs = {}
    if include_cue and filtros["cueanexo"]:
        kwargs["cueanexo"] = filtros["cueanexo"]
    if padron_cues is not None:
        kwargs["cueanexo__in"] = padron_cues
    if include_ciclo and filtros["ciclo"]:
        kwargs["ciclo_id"] = filtros["ciclo"]
    if filtros["modalidad"]:
        kwargs["modalidad_id"] = filtros["modalidad"]
    if filtros["nivel"]:
        kwargs["tipo_estructura_especial_id"] = filtros["nivel"]
    if filtros["seccion"]:
        kwargs["id"] = filtros["seccion"]
    if filtros["turno"]:
        kwargs["turno_id"] = filtros["turno"]
    return kwargs


def _section_scope_requested(filtros, padron_cues):
    return bool(
        padron_cues is not None
        or any(
            filtros[key]
            for key in ("modalidad", "nivel", "seccion", "turno")
        )
    )


def _bancos_alumnos_visualizador(filtros):
    """Query base del visualizador: siempre nace en especial.alumno_banco."""
    queryset = EspecialAlumnoBanco.objects.all()

    if filtros["estado"] == "activo":
        queryset = queryset.filter(estado=EspecialAlumnoBanco.Estado.ACTIVO)
    elif filtros["estado"] != "todos":
        queryset = queryset.filter(estado=filtros["estado"])

    if filtros["cuil"]:
        queryset = queryset.filter(
            Q(alumno__cuil=filtros["cuil"])
            | Q(alumno_cuil_snapshot=filtros["cuil"])
        )
    if filtros["cueanexo"]:
        queryset = queryset.filter(cueanexo=filtros["cueanexo"])
    if filtros["ciclo"]:
        queryset = queryset.filter(ciclo_id=filtros["ciclo"])

    padron_cues = _padron_cues_para_filtros(filtros)
    if _section_scope_requested(filtros, padron_cues):
        section_kwargs = _section_filter_kwargs(
            filtros,
            padron_cues,
            include_cue=False,
            include_ciclo=False,
        )
        section_filters = {
            f"alumno__secciones_especial__seccion__{key}": value
            for key, value in section_kwargs.items()
        }
        if filtros["estado"] == EspecialAlumnoBanco.Estado.ACTIVO:
            section_filters["alumno__secciones_especial__estado"] = (
                AlumnoSeccion.Estado.ACTIVO
            )
        elif filtros["estado"] == EspecialAlumnoBanco.Estado.BAJA:
            section_filters["alumno__secciones_especial__estado"] = (
                AlumnoSeccion.Estado.BAJA
            )
        queryset = queryset.filter(**section_filters)

    return queryset.distinct(), padron_cues


def _alumnos_prueba_queryset(filtros):
    """Primeros 10 alumnos reales, sin escribir ni limitar la vista operativa."""
    alumno_model = _alumno_model()
    primeros_diez = (
        alumno_model.objects.order_by("id")
        .values("pk")[:VISUALIZADOR_PRUEBA_LIMITE]
    )
    queryset = alumno_model.objects.filter(pk__in=Subquery(primeros_diez))
    if filtros["cuil"]:
        queryset = queryset.filter(
            Q(cuil=filtros["cuil"])
            | Q(bancos_especial__alumno_cuil_snapshot=filtros["cuil"])
        )

    padron_cues = _padron_cues_para_filtros(filtros)
    if filtros["cueanexo"]:
        queryset = queryset.filter(bancos_especial__cueanexo=filtros["cueanexo"])
    if filtros["ciclo"]:
        queryset = queryset.filter(bancos_especial__ciclo_id=filtros["ciclo"])
    if padron_cues is not None:
        queryset = queryset.filter(bancos_especial__cueanexo__in=padron_cues)
    section_kwargs = _section_filter_kwargs(
        filtros,
        padron_cues,
        include_cue=True,
        include_ciclo=True,
    )
    if section_kwargs:
        queryset = queryset.filter(
            **{
                f"secciones_especial__seccion__{key}": value
                for key, value in section_kwargs.items()
            }
        )
        queryset = queryset.filter(
            secciones_especial__estado=AlumnoSeccion.Estado.ACTIVO
        )
    if filtros["estado"] != "todos":
        queryset = queryset.filter(
            Q(bancos_especial__estado=filtros["estado"])
            | Q(bancos_especial__pk__isnull=True)
        )
    return queryset.distinct().order_by("id")


def _datos_persona_alumno(alumno, persona, *, preferir_alumno=False):
    """Arma datos de BNH y conserva la fuente real de cada campo."""
    localidad_persona = getattr(persona, "localidad", None) if persona else None
    localidad_alumno = getattr(alumno, "loc_residencia", None)
    localidad_persona_txt = (
        getattr(localidad_persona, "descrip_localidad", "")
    )
    localidad_alumno_txt = getattr(localidad_alumno, "descrip_localidad", "")
    departamento_persona = (
        getattr(localidad_persona, "descrip_departamento", "")
    )
    departamento_alumno = getattr(localidad_alumno, "descrip_departamento", "")

    apellido = _texto(getattr(alumno, "apellidos", ""))
    nombre = _texto(getattr(alumno, "nombres", ""))
    cuil = _texto(getattr(alumno, "cuil", ""))
    dni = _texto(getattr(alumno, "nro_doc", ""))
    fecha_nacimiento = getattr(alumno, "fecha_nacimiento", None)
    sexo = _relacion_texto(getattr(alumno, "sexo", None), "descrip_sexo")
    telefono = _texto(getattr(alumno, "telefono", ""))
    localidad = localidad_alumno_txt
    departamento = departamento_alumno
    estado_persona = "No consultado"

    if persona and not preferir_alumno:
        try:
            telefono_persona = persona.telefono_display()
        except AttributeError:
            telefono_persona = _texto(getattr(persona, "telefono", ""))
        telefono = telefono_persona or telefono
        apellido = _texto(persona.apellido)
        nombre = _texto(persona.nombre)
        cuil = _texto(persona.cuil)
        dni = _texto(persona.dni)
        fecha_nacimiento = persona.f_nacimiento
        sexo = _texto(getattr(persona, "sexo", "")) or sexo
        localidad = localidad_persona_txt or localidad
        departamento = departamento_persona or departamento
        estado_persona = _texto(persona.get_estado_display())
    elif persona:
        estado_persona = _texto(persona.get_estado_display())
    else:
        estado_persona = "No disponible en bnh.personas"

    tipo_documento = _relacion_texto(
        getattr(alumno, "tipo_doc", None),
        "descrip_doc",
    ) or ("DNI" if dni else "")
    localidad_nacimiento = _relacion_texto(
        getattr(alumno, "loc_nacimiento", None),
        "descrip_localidad",
    )
    provincia_nacimiento = _relacion_texto(
        getattr(alumno, "prov_nacimiento", None),
        "descrip_provincia",
    )
    pais_nacimiento = _relacion_texto(
        getattr(alumno, "pais_nacimiento", None),
        "descrip_pais",
    )
    localidad_residencia = _relacion_texto(
        getattr(alumno, "loc_residencia", None),
        "descrip_localidad",
    )
    provincia_residencia = _relacion_texto(
        getattr(alumno, "prov_residencia", None),
        "descrip_provincia",
    )
    pais_residencia = _relacion_texto(
        getattr(alumno, "pais_residencia", None),
        "descrip_pais",
    )
    return {
        "id": alumno.pk,
        "apellido": apellido,
        "nombre": nombre,
        "nombre_completo": ", ".join(filter(None, (apellido, nombre))),
        "cuil": cuil or _texto(getattr(alumno, "cuil", "")),
        "tipo_documento": tipo_documento,
        "nro_documento": dni or _texto(getattr(alumno, "nro_doc", "")),
        "localidad": localidad,
        "departamento": departamento,
        "localidad_residencia": localidad_residencia,
        "provincia_residencia": provincia_residencia,
        "pais_residencia": pais_residencia,
        "localidad_nacimiento": localidad_nacimiento,
        "provincia_nacimiento": provincia_nacimiento,
        "pais_nacimiento": pais_nacimiento,
        "lugar_nacimiento": _texto(getattr(alumno, "lugar_nacimiento", "")),
        "est_civil": _relacion_texto(
            getattr(alumno, "est_civil", None),
            "descrip_estado_civil",
        ),
        "email": _texto(getattr(alumno, "email", "")),
        "telefono": telefono,
        "telefono_normalizado": _texto(
            getattr(alumno, "telefono_normalizado", "")
        ),
        "es_celular": bool(getattr(alumno, "es_celular", False)),
        "whatsapp": bool(getattr(alumno, "whatsapp", False)),
        "fecha_nacimiento": fecha_nacimiento,
        "fecha_registro": getattr(alumno, "fecha_registro", None),
        "observaciones": _texto(getattr(alumno, "observaciones", "")),
        "sexo": sexo,
        "estado": estado_persona,
        "en_bnh_personas": bool(persona),
    }


def _personas_por_cuil(alumnos):
    cuiles = {
        _solo_digitos(getattr(alumno, "cuil", ""))
        for alumno in alumnos
        if len(_solo_digitos(getattr(alumno, "cuil", ""))) == 11
    }
    if not cuiles:
        return {}
    return {
        _solo_digitos(persona.cuil): persona
        for persona in _personas_bnh_queryset().filter(cuil__in=cuiles)
    }


def _padron_por_cueanexo(cueanexos, *, solo_especial=True):
    if not cueanexos:
        return {}
    cueanexos = {
        _solo_digitos(cueanexo)
        for cueanexo in cueanexos
        if _solo_digitos(cueanexo)
    }
    padron_queryset = (
        _padron_especial_queryset()
        if solo_especial
        else EspecialPadronOferta.objects.using(PADRON_DB_ALIAS)
    )
    filas = (
        padron_queryset
        .filter(Q(cueanexo__in=cueanexos) | Q(padron_cueanexo__in=cueanexos))
        .order_by("cueanexo", "padron_cueanexo", "nom_est", "localidad", "departamento")
        .values(
            "cueanexo",
            "padron_cueanexo",
            "nom_est",
            "localidad",
            "departamento",
        )
    )
    por_cueanexo = {}
    for fila in filas:
        claves = {
            _solo_digitos(fila.get("cueanexo")),
            _solo_digitos(fila.get("padron_cueanexo")),
        }
        claves.discard("")
        for clave in claves:
            existente = por_cueanexo.get(clave)
            if not existente or (
                not existente.get("nom_est") and fila.get("nom_est")
            ):
                por_cueanexo[clave] = fila
    return por_cueanexo


def _enriquecer_bancos(bancos):
    """Agrega datos de padrón y valida matrícula contra bancos activos."""
    bancos_validos, cues_asociados = _matriculas_compartidas_validas(bancos)
    cueanexos = {
        cue
        for banco in bancos
        for cue in (
            banco.cueanexo,
            cues_asociados.get(banco.pk),
        )
        if cue
    }
    padron_por_cue = _padron_por_cueanexo(cueanexos)
    padron_por_cue_asociado = _padron_por_cueanexo(
        cueanexos,
        solo_especial=False,
    )
    for banco in bancos:
        banco.visualizador_padron = padron_por_cue.get(banco.cueanexo, {})
        banco.visualizador_matricula_compartida = banco.pk in bancos_validos
        banco.visualizador_cue_asociado = cues_asociados.get(banco.pk, "")
        banco.visualizador_padron_asociado = (
            padron_por_cue_asociado.get(banco.visualizador_cue_asociado, {})
            if banco.visualizador_cue_asociado
            else {}
        )

    bancos_por_alumno = {}
    for banco in bancos:
        bancos_por_alumno.setdefault(banco.alumno_id, []).append(banco)

    for bancos_alumno in bancos_por_alumno.values():
        bancos_activos = [
            banco
            for banco in bancos_alumno
            if banco.estado == EspecialAlumnoBanco.Estado.ACTIVO
            and _solo_digitos(banco.cueanexo)
        ]
        bancos_con_relacion_directa = [
            banco
            for banco in bancos_activos
            if banco.visualizador_matricula_compartida
            and banco.visualizador_cue_asociado
            and _solo_digitos(banco.matricula_compartida)
            == _solo_digitos(banco.visualizador_cue_asociado)
        ]
        banco_original = (
            (bancos_con_relacion_directa or bancos_activos or bancos_alumno)
            or [None]
        )[0]

        for banco in bancos_alumno:
            banco.visualizador_es_cue_original = banco is banco_original
            banco.visualizador_cue_matricula = ""
            banco.visualizador_padron_matricula = {}

        if banco_original and banco_original.visualizador_matricula_compartida:
            banco_original.visualizador_cue_matricula = (
                banco_original.visualizador_cue_asociado
            )
            banco_original.visualizador_padron_matricula = (
                banco_original.visualizador_padron_asociado
            )


def _resumen_cues_alumno(bancos):
    """Devuelve el CUE original y el CUE separado de matrícula compartida."""
    banco_original = next(
        (
            banco
            for banco in bancos
            if getattr(banco, "visualizador_es_cue_original", False)
        ),
        None,
    )
    if not banco_original:
        return {
            "cue_original": "",
            "matricula_compartida": False,
            "cue_matricula": "",
            "padron_matricula": {},
        }
    return {
        "cue_original": banco_original.cueanexo or "",
        "matricula_compartida": bool(
            banco_original.visualizador_matricula_compartida
        ),
        "cue_matricula": (
            banco_original.visualizador_cue_matricula
            if banco_original.visualizador_matricula_compartida
            else ""
        ),
        "padron_matricula": (
            banco_original.visualizador_padron_matricula
            if banco_original.visualizador_matricula_compartida
            else {}
        ),
    }


def _matriculas_compartidas_validas(bancos):
    """Valida CUE-Anexos compartidos activos sin modificar datos persistidos."""
    grupos = {}
    for banco in bancos:
        if banco.estado != EspecialAlumnoBanco.Estado.ACTIVO:
            continue
        grupos.setdefault(banco.alumno_id, []).append(banco)

    bancos_validos = set()
    cues_asociados = {}
    for alumno_id, bancos_activos in grupos.items():
        cues_activos = {
            _solo_digitos(banco.cueanexo)
            for banco in bancos_activos
            if len(_solo_digitos(banco.cueanexo)) == 9
        }
        hay_multiples_cues = len(cues_activos) > 1
        for banco in bancos_activos:
            valor = banco.matricula_compartida
            cue_actual = _solo_digitos(banco.cueanexo)
            cue_asociado = _solo_digitos(valor)
            motivo_invalidez = ""

            if not valor and not hay_multiples_cues:
                continue
            if valor and len(cue_asociado) != 9:
                motivo_invalidez = "el CUE asociado no tiene 9 dígitos"
            elif len(cues_activos) <= 1 and valor:
                motivo_invalidez = "solo existe un CUE-Anexo activo"
            elif valor and cue_asociado == cue_actual:
                motivo_invalidez = "el CUE asociado coincide con el CUE actual"
            elif valor and cue_asociado not in cues_activos:
                motivo_invalidez = "el CUE asociado no pertenece a otro banco activo"

            if motivo_invalidez:
                logger.warning(
                    "Matrícula compartida inconsistente: alumno_id=%s ciclo_id=%s "
                    "cueanexo=%s matricula_compartida=%s (%s). No se modifica la base.",
                    alumno_id,
                    banco.ciclo_id,
                    banco.cueanexo,
                    valor,
                    motivo_invalidez,
                )
                # Un valor persistido inválido no habilita la matrícula cuando
                # el alumno solo tiene un CUE. Si hay dos CUE activos, la
                # relación operativa se puede inferir del segundo CUE vigente.
                if not hay_multiples_cues:
                    continue

            if not hay_multiples_cues:
                continue

            bancos_validos.add(banco.pk)
            if cue_asociado in cues_activos and cue_asociado != cue_actual:
                cues_asociados[banco.pk] = cue_asociado
                continue

            alternativas = sorted(cue for cue in cues_activos if cue != cue_actual)
            if alternativas:
                cues_asociados[banco.pk] = alternativas[0]

    return bancos_validos, cues_asociados


def _inscripciones_visualizador(alumno_ids, filtros=None, *, detalle=False):
    queryset = (
        AlumnoSeccion.objects.filter(alumno_id__in=alumno_ids)
        .select_related(
            "seccion",
            "seccion__ciclo",
            "seccion__cd_tipo_seccion",
            "seccion__tipo_estructura_especial",
            "seccion__rango_etario",
            "seccion__modalidad",
            "seccion__turno",
        )
        .order_by(
            "alumno_id",
            "seccion__ciclo__anio",
            "seccion__cueanexo",
            "seccion__nombre_seccion",
            "-fecha_inscripcion",
        )
    )
    if detalle:
        docentes_queryset = DocenteSeccion.objects.order_by(
            "rol", "docente_nombre_snapshot", "docente_cuil"
        )
        queryset = queryset.prefetch_related(
            Prefetch(
                "seccion__docentes",
                queryset=docentes_queryset,
                to_attr="visualizador_docentes",
            )
        )
    elif filtros is not None:
        padron_cues = _padron_cues_para_filtros(filtros)
        section_kwargs = _section_filter_kwargs(
            filtros,
            padron_cues,
            include_cue=True,
            include_ciclo=True,
        )
        if section_kwargs:
            queryset = queryset.filter(
                **{
                    f"seccion__{key}": value
                    for key, value in section_kwargs.items()
                }
            )
        if filtros["estado"] == EspecialAlumnoBanco.Estado.ACTIVO:
            queryset = queryset.filter(estado=AlumnoSeccion.Estado.ACTIVO)
        elif filtros["estado"] == EspecialAlumnoBanco.Estado.BAJA:
            queryset = queryset.filter(estado=AlumnoSeccion.Estado.BAJA)
    return queryset


def _enriquecer_inscripciones(inscripciones, *, incluir_docentes=False):
    cueanexos = {item.seccion.cueanexo for item in inscripciones}
    padron_por_cue = _padron_por_cueanexo(cueanexos)
    personas_docentes = {}
    if incluir_docentes:
        cuiles = {
            _solo_digitos(asignacion.docente_cuil)
            for item in inscripciones
            for asignacion in getattr(item.seccion, "visualizador_docentes", [])
            if _solo_digitos(asignacion.docente_cuil)
        }
        if cuiles:
            personas_docentes = {
                _solo_digitos(persona.cuil): persona
                for persona in _personas_bnh_queryset().filter(cuil__in=cuiles)
            }

    for item in inscripciones:
        item.visualizador_padron = padron_por_cue.get(item.seccion.cueanexo, {})
        if incluir_docentes:
            for asignacion in getattr(item.seccion, "visualizador_docentes", []):
                persona = personas_docentes.get(_solo_digitos(asignacion.docente_cuil))
                if persona:
                    asignacion.visualizador_docente_nombre = (
                        f"{persona.apellido}, {persona.nombre}"
                    ).strip(", ")
                    asignacion.visualizador_docente_dni = persona.dni or ""
                else:
                    asignacion.visualizador_docente_nombre = (
                        asignacion.docente_nombre_snapshot
                        or asignacion.docente_cuil
                    )
                    asignacion.visualizador_docente_dni = (
                        asignacion.docente_dni_snapshot or ""
                    )


def _filtros_querystring(request):
    parametros = []
    for key in request.GET:
        if key == "page" or key not in FILTROS_ALUMNOS_QUERYSTRING:
            continue
        for value in request.GET.getlist(key):
            parametros.append((key, value))
    return urlencode(parametros)


def _error_busqueda(mensaje):
    return JsonResponse({"ok": False, "mensaje": mensaje, "resultados": []}, status=400)


def _buscar_personas(request, tipo):
    valor = (request.GET.get("q") or request.GET.get("cuil") or request.GET.get("dni") or "").strip()
    documento = _solo_digitos(valor)
    if len(documento) < 7:
        return _error_busqueda("Ingresá un CUIL o DNI válido para buscar.")

    if tipo == "alumno":
        bancos = EspecialAlumnoBanco.objects.filter(
            estado=EspecialAlumnoBanco.Estado.ACTIVO,
        )
        if len(documento) == 11:
            bancos = bancos.filter(
                Q(alumno__cuil=documento) | Q(alumno_cuil_snapshot=documento)
            )
        else:
            bancos = bancos.filter(
                Q(alumno__nro_doc=documento)
                | Q(alumno_documento_snapshot=documento)
            )
        alumnos_ids = bancos.values("alumno_id").distinct()[:20]
        alumnos = _alumno_model().objects.filter(
            pk__in=Subquery(alumnos_ids)
        ).select_related("tipo_doc", "sexo")
        personas = _personas_por_cuil(alumnos)
        resultados = [
            {
                "nombre": _datos_persona_alumno(
                    alumno,
                    personas.get(_solo_digitos(alumno.cuil)),
                )["nombre_completo"],
                "dni": alumno.nro_doc or "",
                "cuil": alumno.cuil or "",
                "detalle_url": (
                    f"{reverse('especial:visualizador_detalle_alumno')}?alumno_id={alumno.pk}"
                ),
            }
            for alumno in alumnos
        ]
    elif tipo == "docente":
        docentes = EspecialDocenteBnh.objects.using(PADRON_DB_ALIAS).filter(
            Q(cuil=documento) | Q(dni=documento)
        ).order_by("apellido", "nombre")[:20]
        resultados = [
            {
                "nombre": docente.nombre_completo,
                "dni": docente.dni or "",
                "cuil": docente.cuil or "",
                "detalle_url": f"{reverse('especial:visualizador_detalle_docente')}?cuil={docente.cuil}",
            }
            for docente in docentes
        ]
    else:
        resultados = _buscar_directores(documento)

    return JsonResponse({"ok": True, "resultados": resultados})


def _buscar_directores(cuil):
    sql = """
        SELECT cueanexo, nom_est, oferta, localidad, departamento,
               estado_est, apellido_resp, nombre_resp, resploc_cuitcuil,
               resploc_email, resploc_telefono
          FROM v_capa_unica_ofertas_ant
         WHERE regexp_replace(COALESCE(resploc_cuitcuil, ''), '\\D', '', 'g') = %s
         ORDER BY cueanexo, nom_est, oferta
         LIMIT 50
    """
    try:
        with connections[PADRON_DB_ALIAS].cursor() as cursor:
            cursor.execute(sql, [cuil])
            columnas = [columna[0] for columna in cursor.description]
            filas = [dict(zip(columnas, fila)) for fila in cursor.fetchall()]
    except (OperationalError, ProgrammingError):
        return []

    return [
        {
            "nombre": " ".join(filter(None, [fila.get("apellido_resp"), fila.get("nombre_resp")])),
            "dni": "",
            "cuil": fila.get("resploc_cuitcuil") or cuil,
            "establecimiento": fila.get("nom_est") or "",
            "cueanexo": fila.get("cueanexo") or "",
            "detalle_url": f"{reverse('especial:visualizador_detalle_director')}?cuil={cuil}",
        }
        for fila in filas
    ]


def _datos_director(cuil):
    sql = """
        SELECT cueanexo, nom_est, oferta, localidad, departamento,
               estado_est, apellido_resp, nombre_resp, resploc_cuitcuil,
               resploc_email, resploc_telefono
          FROM v_capa_unica_ofertas_ant
         WHERE regexp_replace(COALESCE(resploc_cuitcuil, ''), '\\D', '', 'g') = %s
         ORDER BY cueanexo, nom_est, oferta
    """
    with connections[PADRON_DB_ALIAS].cursor() as cursor:
        cursor.execute(sql, [cuil])
        columnas = [columna[0] for columna in cursor.description]
        return [dict(zip(columnas, fila)) for fila in cursor.fetchall()]


def _persona_context(request, titulo, subtitulo="Consulta global exclusiva para administradores."):
    context = contexto_base(request, "visualizador", titulo, subtitulo)
    context["visualizador_es_admin"] = True
    return context


@especial_required
def visualizador_inicio(request):
    _exigir_administrador(request)
    tipo = (request.GET.get("tipo") or "").lower()
    if request.headers.get("x-requested-with") == "XMLHttpRequest" and tipo in TIPOS_BUSQUEDA:
        try:
            return _buscar_personas(request, tipo)
        except (OperationalError, ProgrammingError):
            return JsonResponse({"ok": False, "mensaje": "No se pudo consultar la fuente de datos.", "resultados": []}, status=503)

    context = _persona_context(
        request,
        "Visualizador",
        "Consultá globalmente alumnos, docentes y directores del módulo Especial.",
    )
    context["opciones_visualizador"] = (
        ("alumno", "Buscar alumno", "fa-user-graduate"),
        ("docente", "Buscar docente", "fa-chalkboard-user"),
        ("director", "Buscar director", "fa-user-tie"),
    )
    return render(request, "especial/visualizador_inicio.html", context)


def _catalogos_filtros_alumnos():
    padron = _padron_especial_queryset()
    secciones = (
        SeccionEspecial.objects.filter(
            alumnos__estado=AlumnoSeccion.Estado.ACTIVO,
            alumnos__alumno__bancos_especial__estado=(
                EspecialAlumnoBanco.Estado.ACTIVO
            ),
        )
        .select_related("ciclo")
        .distinct()
        .order_by("cueanexo", "ciclo__anio", "nombre_seccion")
    )
    return {
        "cueanexos_filtro": (
            EspecialAlumnoBanco.objects.values_list("cueanexo", flat=True)
            .distinct()
            .order_by("cueanexo")
        ),
        "establecimientos_filtro": (
            padron.exclude(nom_est__isnull=True)
            .exclude(nom_est="")
            .values("nom_est")
            .distinct()
            .order_by("nom_est")
        ),
        "localidades_filtro": (
            padron.exclude(localidad__isnull=True)
            .exclude(localidad="")
            .values_list("localidad", flat=True)
            .distinct()
            .order_by("localidad")
        ),
        "departamentos_filtro": (
            padron.exclude(departamento__isnull=True)
            .exclude(departamento="")
            .values_list("departamento", flat=True)
            .distinct()
            .order_by("departamento")
        ),
        "estados_filtro": EspecialAlumnoBanco.Estado.choices,
        "ciclos_filtro": EspecialCiclo.objects.order_by("-anio"),
        "modalidades_filtro": ModalidadDictadoTipo.objects.order_by("descripcion"),
        "niveles_filtro": CatalogoTipoEstructuraEspecial.objects.order_by("descripcion"),
        "secciones_filtro": secciones,
        "turnos_filtro": TurnoTipo.objects.order_by("descripcion"),
    }


def _filtros_docentes(request):
    """Normaliza los filtros de consulta del visualizador de docentes."""
    filtros = {
        "cuil": _solo_digitos(request.GET.get("cuil")),
        "cueanexo": _solo_digitos(request.GET.get("filtro_cueanexo")),
        "establecimiento": (request.GET.get("establecimiento") or "").strip(),
        "localidad": (request.GET.get("localidad") or "").strip(),
        "departamento": (request.GET.get("departamento") or "").strip(),
        "ciclo": (request.GET.get("filtro_ciclo") or "").strip(),
        "modalidad": (request.GET.get("modalidad") or "").strip(),
        "nivel": (request.GET.get("nivel") or "").strip(),
        "seccion": (request.GET.get("seccion") or "").strip(),
        "turno": (request.GET.get("turno") or "").strip(),
        "rol": (request.GET.get("rol") or "").strip().lower(),
        "estado": (request.GET.get("estado") or "todos").strip().lower(),
    }
    errores = {}

    if request.GET.get("cuil") and len(filtros["cuil"]) != 11:
        errores["cuil"] = "El CUIL debe contener exactamente 11 dígitos."
    elif filtros["cuil"]:
        try:
            validar_cuil(filtros["cuil"])
        except ValidationError:
            errores["cuil"] = "El CUIL no tiene un dígito verificador válido."
    if request.GET.get("filtro_cueanexo") and len(filtros["cueanexo"]) != 9:
        errores["cueanexo"] = "El CUE-Anexo debe contener exactamente 9 dígitos."

    estados_validos = {
        estado
        for estado, _ in EspecialDocenteBanco.Estado.choices
    } | {"todos"}
    if filtros["estado"] not in estados_validos:
        filtros["estado"] = "todos"

    roles_validos = {rol for rol, _ in DocenteSeccion.Rol.choices} | {""}
    if filtros["rol"] not in roles_validos:
        errores["rol"] = "Seleccioná un rol válido."

    for key in ("ciclo", "modalidad", "nivel", "seccion", "turno"):
        if filtros[key] and not filtros[key].isdigit():
            errores[key] = "Seleccioná una opción válida."

    return filtros, errores


def _filtros_directores(request):
    filtros = {
        "cuil": _solo_digitos(request.GET.get("cuil")),
        "cueanexo": _solo_digitos(request.GET.get("filtro_cueanexo")),
        "establecimiento": (request.GET.get("establecimiento") or "").strip(),
        "localidad": (request.GET.get("localidad") or "").strip(),
        "departamento": (request.GET.get("departamento") or "").strip(),
    }
    errores = {}
    if request.GET.get("cuil") and len(filtros["cuil"]) != 11:
        errores["cuil"] = "El CUIL debe contener exactamente 11 dígitos."
    elif filtros["cuil"]:
        try:
            validar_cuil(filtros["cuil"])
        except ValidationError:
            errores["cuil"] = "El CUIL no tiene un dígito verificador válido."
    if request.GET.get("filtro_cueanexo") and len(filtros["cueanexo"]) != 9:
        errores["cueanexo"] = "El CUE-Anexo debe contener exactamente 9 dígitos."
    return filtros, errores


def _directores_queryset(filtros):
    queryset = (
        _padron_especial_queryset()
        .annotate(
            cuil_limpio=Func(
                F("resploc_cuitcuil"),
                Value(r"\D"),
                Value(""),
                Value("g"),
                function="REGEXP_REPLACE",
                output_field=CharField(),
            )
        )
        .exclude(cuil_limpio="")
    )
    if filtros["cuil"]:
        queryset = queryset.filter(cuil_limpio=filtros["cuil"])
    if filtros["cueanexo"]:
        queryset = queryset.filter(cueanexo=filtros["cueanexo"])
    if filtros["establecimiento"]:
        queryset = queryset.filter(nom_est__icontains=filtros["establecimiento"])
    if filtros["localidad"]:
        queryset = queryset.filter(localidad__icontains=filtros["localidad"])
    if filtros["departamento"]:
        queryset = queryset.filter(departamento__icontains=filtros["departamento"])
    return queryset.order_by(
        "cuil_limpio",
        "cueanexo",
        "nom_est",
        "oferta",
    )


def _filtros_directores_querystring(request):
    parametros = []
    for key in request.GET:
        if key == "page" or key not in {
            "cuil",
            "filtro_cueanexo",
            "establecimiento",
            "localidad",
            "departamento",
        }:
            continue
        for value in request.GET.getlist(key):
            parametros.append((key, value))
    return urlencode(parametros)


def _catalogos_filtros_directores():
    padron = _padron_especial_queryset()
    return {
        "cueanexos_directores_filtro": (
            padron.exclude(cueanexo__isnull=True)
            .values_list("cueanexo", flat=True)
            .distinct()
            .order_by("cueanexo")
        ),
        "establecimientos_directores_filtro": (
            padron.exclude(nom_est__isnull=True)
            .exclude(nom_est="")
            .values("nom_est")
            .distinct()
            .order_by("nom_est")
        ),
        "localidades_directores_filtro": (
            padron.exclude(localidad__isnull=True)
            .exclude(localidad="")
            .values_list("localidad", flat=True)
            .distinct()
            .order_by("localidad")
        ),
        "departamentos_directores_filtro": (
            padron.exclude(departamento__isnull=True)
            .exclude(departamento="")
            .values_list("departamento", flat=True)
            .distinct()
            .order_by("departamento")
        ),
    }


def _agrupar_directores(filas):
    agrupados = {}
    for fila in filas:
        cuil = fila.cuil_limpio
        if cuil not in agrupados:
            agrupados[cuil] = {
                "cuil": cuil,
                "nombre": " ".join(
                    parte
                    for parte in (
                        _texto(fila.apellido_resp),
                        _texto(fila.nombre_resp),
                    )
                    if parte
                ),
                "vinculos": [],
                "detalle_url": (
                    f"{reverse('especial:visualizador_detalle_director')}?cuil={cuil}"
                ),
            }
        cueanexo = fila.cueanexo or fila.padron_cueanexo or ""
        vinculo = {
            "cueanexo": cueanexo,
            "oferta": fila.oferta or "",
            "establecimiento": fila.nom_est or "",
            "localidad": fila.localidad or "",
            "departamento": fila.departamento or "",
            "estado": fila.estado_est or "",
        }
        clave_vinculo = tuple(vinculo.values())
        if not any(
            tuple(existente.values()) == clave_vinculo
            for existente in agrupados[cuil]["vinculos"]
        ):
            agrupados[cuil]["vinculos"].append(vinculo)

    directores = list(agrupados.values())
    for director in directores:
        director["vinculos"].sort(
            key=lambda vinculo: (
                vinculo["cueanexo"],
                vinculo["oferta"],
                vinculo["establecimiento"],
            )
        )
    return directores


def _asignaciones_docentes_scope(filtros, *, incluir_estado=False):
    """Construye el alcance real de DocenteSeccion para filtrar CUILes."""
    padron_cues = _padron_cues_para_filtros(filtros)
    section_kwargs = _section_filter_kwargs(
        filtros,
        padron_cues,
        include_cue=True,
        include_ciclo=True,
    )
    queryset = DocenteSeccion.objects.all()
    if section_kwargs:
        queryset = queryset.filter(
            **{
                f"seccion__{key}": value
                for key, value in section_kwargs.items()
            }
        )
    if filtros["rol"]:
        queryset = queryset.filter(rol=filtros["rol"])
    if incluir_estado and filtros["estado"] != "todos":
        queryset = queryset.filter(estado=filtros["estado"])
    return queryset, padron_cues


def _bancos_docentes_visualizador(filtros):
    """Obtiene bancos de docentes sin duplicar por sus asignaciones."""
    queryset = EspecialDocenteBanco.objects.all()
    filtros_sobre_asignacion = bool(
        filtros["establecimiento"]
        or filtros["localidad"]
        or filtros["departamento"]
        or filtros["modalidad"]
        or filtros["nivel"]
        or filtros["seccion"]
        or filtros["turno"]
        or filtros["rol"]
    )

    if filtros["cuil"]:
        queryset = queryset.filter(docente_cuil=filtros["cuil"])

    if filtros_sobre_asignacion:
        asignaciones, _ = _asignaciones_docentes_scope(
            filtros,
            incluir_estado=filtros["estado"] != "todos",
        )
        queryset = queryset.filter(
            docente_cuil__in=asignaciones.values("docente_cuil")
        )
        if filtros["cueanexo"]:
            queryset = queryset.filter(cueanexo=filtros["cueanexo"])
        if filtros["ciclo"]:
            queryset = queryset.filter(ciclo_id=filtros["ciclo"])
    else:
        if filtros["estado"] != "todos":
            queryset = queryset.filter(estado=filtros["estado"])
        if filtros["cueanexo"]:
            queryset = queryset.filter(cueanexo=filtros["cueanexo"])
        if filtros["ciclo"]:
            queryset = queryset.filter(ciclo_id=filtros["ciclo"])

    return queryset.distinct()


def _catalogos_filtros_docentes():
    padron = _padron_especial_queryset()
    secciones = (
        SeccionEspecial.objects.filter(docentes__isnull=False)
        .select_related("ciclo")
        .distinct()
        .order_by("cueanexo", "ciclo__anio", "nombre_seccion")
    )
    return {
        "cueanexos_docentes_filtro": (
            EspecialDocenteBanco.objects.values_list("cueanexo", flat=True)
            .distinct()
            .order_by("cueanexo")
        ),
        "establecimientos_docentes_filtro": (
            padron.exclude(nom_est__isnull=True)
            .exclude(nom_est="")
            .values("nom_est")
            .distinct()
            .order_by("nom_est")
        ),
        "localidades_docentes_filtro": (
            padron.exclude(localidad__isnull=True)
            .exclude(localidad="")
            .values_list("localidad", flat=True)
            .distinct()
            .order_by("localidad")
        ),
        "departamentos_docentes_filtro": (
            padron.exclude(departamento__isnull=True)
            .exclude(departamento="")
            .values_list("departamento", flat=True)
            .distinct()
            .order_by("departamento")
        ),
        "estados_docentes_filtro": EspecialDocenteBanco.Estado.choices,
        "ciclos_docentes_filtro": EspecialCiclo.objects.order_by("-anio"),
        "modalidades_docentes_filtro": ModalidadDictadoTipo.objects.order_by(
            "descripcion"
        ),
        "niveles_docentes_filtro": CatalogoTipoEstructuraEspecial.objects.order_by(
            "descripcion"
        ),
        "secciones_docentes_filtro": secciones,
        "turnos_docentes_filtro": TurnoTipo.objects.order_by("descripcion"),
        "roles_docentes_filtro": DocenteSeccion.Rol.choices,
    }


def _filtros_docentes_querystring(request):
    parametros = []
    for key in request.GET:
        if key == "page" or key not in FILTROS_DOCENTES_QUERYSTRING:
            continue
        for value in request.GET.getlist(key):
            parametros.append((key, value))
    return urlencode(parametros)


def _datos_persona_docente(persona, bancos):
    """Arma los datos personales usando la fuente BNH y snapshots como respaldo."""
    banco = bancos[0] if bancos else None
    snapshot = _texto(getattr(banco, "docente_nombre_snapshot", ""))
    apellido = ""
    nombre = ""
    if "," in snapshot:
        apellido, nombre = [parte.strip() for parte in snapshot.split(",", 1)]
    elif snapshot:
        apellido = snapshot

    if persona:
        try:
            telefono = persona.telefono_display()
        except AttributeError:
            telefono = _texto(getattr(persona, "telefono", ""))
        telefono = telefono or _texto(
            getattr(persona, "telefono_normalizado", "")
            or getattr(persona, "telefono", "")
        )
        localidad = _relacion_texto(
            getattr(persona, "localidad", None),
            "descrip_localidad",
        )
        provincia = _relacion_texto(
            getattr(persona, "provincia", None),
            "descrip_provincia",
        )
        return {
            "apellido": _texto(persona.apellido),
            "nombre": _texto(persona.nombre),
            "cuil": _solo_digitos(persona.cuil),
            "dni": _texto(persona.dni),
            "fecha_nacimiento": persona.f_nacimiento,
            "sexo": _relacion_texto(getattr(persona, "sexo", None), "descrip_sexo"),
            "domicilio": _texto(getattr(persona, "domicilio", "")),
            "localidad": localidad,
            "provincia": provincia,
            "telefono": telefono,
            "email": _texto(getattr(persona, "email", "")),
            "estado_bnh": _texto(persona.get_estado_display()),
        }

    return {
        "apellido": apellido,
        "nombre": nombre,
        "cuil": _solo_digitos(getattr(banco, "docente_cuil", "")),
        "dni": _texto(getattr(banco, "docente_dni_snapshot", "")),
        "fecha_nacimiento": None,
        "sexo": "",
        "domicilio": "",
        "localidad": "",
        "provincia": "",
        "telefono": "",
        "email": "",
        "estado_bnh": _texto(getattr(banco, "docente_estado_bnh_snapshot", ""))
        or "No disponible",
    }


def _enriquecer_docentes_visualizador(docentes, bancos, asignaciones, personas):
    bancos_por_cuil = {}
    for banco in bancos:
        bancos_por_cuil.setdefault(_solo_digitos(banco.docente_cuil), []).append(banco)

    asignaciones_por_cuil = {}
    cueanexos = set()
    for asignacion in asignaciones:
        cuil = _solo_digitos(asignacion.docente_cuil)
        asignaciones_por_cuil.setdefault(cuil, []).append(asignacion)
        cueanexos.add(asignacion.seccion.cueanexo)
    for banco in bancos:
        cueanexos.add(banco.cueanexo)

    padron_por_cue = _padron_por_cueanexo(cueanexos)
    padron_por_cue_todas_ofertas = _padron_por_cueanexo(
        cueanexos,
        solo_especial=False,
    )
    for asignacion in asignaciones:
        asignacion.visualizador_padron = padron_por_cue.get(
            asignacion.seccion.cueanexo,
            padron_por_cue_todas_ofertas.get(asignacion.seccion.cueanexo, {}),
        )

    for docente in docentes:
        cuil = _solo_digitos(getattr(docente, "docente_cuil", docente))
        bancos_docente = bancos_por_cuil.get(cuil, [])
        asignaciones_docente = asignaciones_por_cuil.get(cuil, [])
        persona = personas.get(cuil)
        docente.visualizador_persona = _datos_persona_docente(
            persona,
            bancos_docente,
        )
        docente.visualizador_bancos = bancos_docente
        docente.visualizador_asignaciones = asignaciones_docente
        cues = {
            banco.cueanexo
            for banco in bancos_docente
            if banco.cueanexo
        } | {
            asignacion.seccion.cueanexo
            for asignacion in asignaciones_docente
            if asignacion.seccion.cueanexo
        }
        docente.visualizador_cueanexos = sorted(cues)
        establecimientos = {
            padron_por_cue[cue].get("nom_est")
            for cue in cues
            if padron_por_cue.get(cue, {}).get("nom_est")
        }
        docente.visualizador_establecimientos = sorted(establecimientos)
        docente.visualizador_secciones = len(
            {asignacion.seccion_id for asignacion in asignaciones_docente}
        )
        estados = []
        for registro in bancos_docente + asignaciones_docente:
            etiqueta = registro.get_estado_display()
            if etiqueta not in estados:
                estados.append(etiqueta)
        docente.visualizador_estados = estados or ["Sin registros"]


@especial_required
def visualizador_docentes(request):
    """Listado global de docentes de Especial, sólo de consulta."""
    _exigir_administrador(request)
    permisos = get_permisos_especial_request(request)
    logger.info(
        "Visualizador docentes: url=%s metodo=%s usuario_id=%s usuario=%s "
        "rol=%s permiso_puede_ver=%s permiso_es_admin=%s filtros=%s",
        request.get_full_path(),
        request.method,
        getattr(request.user, "pk", ""),
        getattr(request.user, "username", ""),
        permisos.get("rol", ""),
        permisos.get("puede_ver", False),
        permisos.get("es_admin", False),
        request.GET.urlencode(),
    )
    filtros, errores = _filtros_docentes(request)
    context = _persona_context(
        request,
        "Visualizador de docentes",
        "Consulta de docentes, asignaciones y secciones de Educación Especial.",
    )
    context.update(_catalogos_filtros_docentes())
    context.update(
        {
            "filtros_docentes": filtros,
            "filtros_docentes_errores": errores,
            "filtros_docentes_querystring": _filtros_docentes_querystring(request),
            "docentes_visualizador": [],
            "page_obj": Paginator([], VISUALIZADOR_ALUMNOS_PAGE_SIZE).get_page(1),
            "consulta_error": "",
            "filtros_panel_abierto": bool(errores or request.GET),
        }
    )

    if errores:
        return render(request, "especial/visualizador_docentes.html", context)

    try:
        bancos_queryset = _bancos_docentes_visualizador(filtros)
        cuiles_queryset = (
            bancos_queryset.values_list("docente_cuil", flat=True)
            .distinct()
            .order_by("docente_cuil")
        )
        paginator = Paginator(cuiles_queryset, VISUALIZADOR_ALUMNOS_PAGE_SIZE)
        page_obj = paginator.get_page(request.GET.get("page") or 1)
        cuiles = list(page_obj.object_list)

        bancos = list(
            EspecialDocenteBanco.objects.filter(docente_cuil__in=cuiles)
            .select_related("ciclo")
            .order_by("docente_cuil", "-ciclo__anio", "-pk")
        )
        asignaciones = list(
            DocenteSeccion.objects.filter(docente_cuil__in=cuiles)
            .select_related(
                "seccion",
                "seccion__ciclo",
                "seccion__cd_tipo_seccion",
                "seccion__tipo_estructura_especial",
                "seccion__modalidad",
                "seccion__turno",
            )
            .order_by(
                "docente_cuil",
                "seccion__ciclo__anio",
                "seccion__cueanexo",
                "seccion__nombre_seccion",
                "rol",
            )
        )
        personas = {
            _solo_digitos(persona.cuil): persona
            for persona in _personas_bnh_queryset().filter(cuil__in=cuiles)
        }
        docentes = [SimpleNamespace(docente_cuil=cuil) for cuil in cuiles]
        _enriquecer_docentes_visualizador(
            docentes,
            bancos,
            asignaciones,
            personas,
        )
        page_obj.object_list = docentes
        context.update(
            {
                "docentes_visualizador": docentes,
                "page_obj": page_obj,
                "total_docentes": paginator.count,
            }
        )
    except (OperationalError, ProgrammingError):
        logger.exception("No se pudo consultar el Visualizador de docentes Especial.")
        context["consulta_error"] = (
            "No se pudo consultar la fuente de datos seleccionada."
        )

    return render(request, "especial/visualizador_docentes.html", context)


@especial_required
def visualizador_directores(request):
    """Listado global de directores/responsables de establecimientos Especial."""
    _exigir_administrador(request)
    filtros, errores = _filtros_directores(request)
    context = _persona_context(
        request,
        "Visualizador de directores",
        "Consulta global de directores, establecimientos y CUE-Anexos de Educación Especial.",
    )
    context.update(_catalogos_filtros_directores())
    context.update(
        {
            "filtros_directores": filtros,
            "filtros_directores_errores": errores,
            "filtros_directores_querystring": _filtros_directores_querystring(request),
            "directores_visualizador": [],
            "page_obj": Paginator([], VISUALIZADOR_ALUMNOS_PAGE_SIZE).get_page(1),
            "consulta_error": "",
            "filtros_panel_abierto": bool(errores or request.GET),
        }
    )
    if errores:
        return render(request, "especial/visualizador_directores.html", context)

    try:
        filas = list(_directores_queryset(filtros))
        directores_agrupados = _agrupar_directores(filas)
        paginator = Paginator(directores_agrupados, VISUALIZADOR_ALUMNOS_PAGE_SIZE)
        page_obj = paginator.get_page(request.GET.get("page") or 1)
        directores = list(page_obj.object_list)
        context.update(
            {
                "directores_visualizador": directores,
                "page_obj": page_obj,
                "total_directores": paginator.count,
            }
        )
    except (OperationalError, ProgrammingError):
        logger.exception("No se pudo consultar el Visualizador de directores Especial.")
        context["consulta_error"] = "No se pudo consultar la fuente de datos seleccionada."

    return render(request, "especial/visualizador_directores.html", context)


@especial_required
def visualizador_alumnos(request):
    """Lista operativa del banco Especial o vista explícita de prueba BNH."""
    _exigir_administrador(request)
    permisos = get_permisos_especial_request(request)
    logger.info(
        "Visualizador alumnos: url=%s metodo=%s usuario_id=%s usuario=%s "
        "rol=%s permiso_puede_ver=%s permiso_es_admin=%s filtros=%s",
        request.get_full_path(),
        request.method,
        getattr(request.user, "pk", ""),
        getattr(request.user, "username", ""),
        permisos.get("rol", ""),
        permisos.get("puede_ver", False),
        permisos.get("es_admin", False),
        request.GET.urlencode(),
    )
    cargar_alumnos_prueba = _solicita_alumnos_prueba(request)
    modo_prueba = _es_modo_prueba(request) or cargar_alumnos_prueba
    filtros, errores = _filtros_alumnos(request)
    context = _persona_context(
        request,
        "Visualizador de alumnos",
        (
            "Registros de prueba para validar el listado y los filtros."
            if modo_prueba
            else "Alumnos pertenecientes al banco de Educación Especial y sus inscripciones."
        ),
    )
    context.update(_catalogos_filtros_alumnos())
    context.update(
        {
            "filtros": filtros,
            "filtros_errores": errores,
            "filtros_querystring": _filtros_querystring(request),
            "alumnos": [],
            "page_obj": Paginator([], VISUALIZADOR_ALUMNOS_PAGE_SIZE).get_page(1),
            "consulta_error": "",
            "modo_prueba": modo_prueba,
            "cargar_alumnos_prueba": cargar_alumnos_prueba,
            "filtros_panel_abierto": cargar_alumnos_prueba,
        }
    )

    if errores:
        return render(request, "especial/visualizador_alumnos.html", context)

    try:
        if modo_prueba:
            alumnos_queryset = _alumnos_prueba_queryset(filtros)
        else:
            bancos_queryset, _ = _bancos_alumnos_visualizador(filtros)
            alumnos_queryset = (
                _alumno_model()
                .objects.filter(
                    pk__in=Subquery(
                        bancos_queryset.values("alumno_id").distinct()
                    )
                )
                .order_by("apellidos", "nombres", "pk")
            )
        alumnos_queryset = alumnos_queryset.select_related(
            "tipo_doc",
            "sexo",
            "est_civil",
            "pais_nacimiento",
            "prov_nacimiento",
            "loc_nacimiento",
            "pais_residencia",
            "prov_residencia",
            "loc_residencia",
            "codigo_area",
        )
        paginator = Paginator(
            alumnos_queryset,
            VISUALIZADOR_ALUMNOS_PAGE_SIZE,
        )
        page_obj = paginator.get_page(request.GET.get("page") or 1)
        alumnos = list(page_obj.object_list)
        alumno_ids = [alumno.pk for alumno in alumnos]

        inscripciones = list(
            _inscripciones_visualizador(
                alumno_ids,
                detalle=True,
            )
        )
        _enriquecer_inscripciones(inscripciones, incluir_docentes=True)
        inscripciones_por_alumno = {}
        for inscripcion in inscripciones:
            inscripciones_por_alumno.setdefault(
                inscripcion.alumno_id,
                [],
            ).append(inscripcion)

        bancos = list(
            EspecialAlumnoBanco.objects.filter(
                alumno_id__in=alumno_ids,
            )
            .select_related("ciclo")
            .order_by("alumno_id", "-ciclo__anio", "-pk")
        )
        _enriquecer_bancos(bancos)
        bancos_por_alumno = {}
        for banco in bancos:
            bancos_por_alumno.setdefault(banco.alumno_id, []).append(banco)

        alumnos_con_seccion_activa = set(
            AlumnoSeccion.objects.filter(
                alumno_id__in=alumno_ids,
                estado=AlumnoSeccion.Estado.ACTIVO,
            ).values_list("alumno_id", flat=True)
        )

        personas = {} if modo_prueba else _personas_por_cuil(alumnos)
        for alumno in alumnos:
            persona = personas.get(_solo_digitos(getattr(alumno, "cuil", "")))
            alumno.visualizador_persona = _datos_persona_alumno(
                alumno,
                persona,
                preferir_alumno=modo_prueba,
            )
            alumno.visualizador_detalle_inscripciones = inscripciones_por_alumno.get(
                alumno.pk,
                [],
            )
            alumno.visualizador_bancos = bancos_por_alumno.get(alumno.pk, [])
            resumen_cues = _resumen_cues_alumno(alumno.visualizador_bancos)
            alumno.visualizador_cue_original = resumen_cues["cue_original"]
            alumno.visualizador_en_seccion = alumno.pk in alumnos_con_seccion_activa
            alumno.visualizador_matricula_compartida = resumen_cues[
                "matricula_compartida"
            ]
            alumno.visualizador_cue_matricula = resumen_cues["cue_matricula"]
            alumno.visualizador_padron_matricula = resumen_cues["padron_matricula"]
            alumno.visualizador_cue_asociados = [
                banco
                for banco in alumno.visualizador_bancos
                if banco.visualizador_es_cue_original
                and banco.visualizador_matricula_compartida
            ]

        page_obj.object_list = alumnos
        context.update(
            {
                "alumnos": alumnos,
                "page_obj": page_obj,
                "total_alumnos": paginator.count,
            }
        )
    except (OperationalError, ProgrammingError):
        logger.exception("No se pudo consultar el visualizador de alumnos Especial.")
        context["consulta_error"] = (
            "No se pudo consultar la fuente de datos seleccionada."
        )

    return render(request, "especial/visualizador_alumnos.html", context)


@especial_required
def visualizador_detalle_alumno(request):
    _exigir_administrador(request)
    modo_prueba = _es_modo_prueba(request)
    cuil = _solo_digitos(request.GET.get("cuil"))
    alumno_id_param = (request.GET.get("alumno_id") or "").strip()
    alumno = None
    consulta_error = ""
    alumno_id = None

    if alumno_id_param:
        if not alumno_id_param.isdigit():
            consulta_error = "El alumno seleccionado no es válido."
        else:
            alumno_id = int(alumno_id_param)
            if modo_prueba:
                primeros_diez = (
                    _alumno_model().objects.order_by("id").values("pk")[:VISUALIZADOR_PRUEBA_LIMITE]
                )
                alumno_en_prueba = _alumno_model().objects.filter(
                    pk=alumno_id,
                    pk__in=Subquery(primeros_diez),
                ).exists()
            else:
                alumno_en_prueba = EspecialAlumnoBanco.objects.filter(
                    alumno_id=alumno_id
                ).exists()
            if not alumno_en_prueba:
                consulta_error = (
                    "No se encontró el alumno en la fuente seleccionada."
                )
    elif cuil:
        if len(cuil) != 11:
            consulta_error = "El CUIL debe contener exactamente 11 dígitos."
        else:
            try:
                validar_cuil(cuil)
            except ValidationError:
                consulta_error = "El CUIL no tiene un dígito verificador válido."
            else:
                if modo_prueba:
                    primeros_diez = (
                        _alumno_model().objects.order_by("id").values("pk")[:VISUALIZADOR_PRUEBA_LIMITE]
                    )
                    alumno_ids = list(
                        _alumno_model()
                        .objects.filter(pk__in=Subquery(primeros_diez), cuil=cuil)
                        .values_list("pk", flat=True)
                        .distinct()
                    )
                else:
                    alumno_ids = list(
                        EspecialAlumnoBanco.objects.filter(
                            Q(alumno__cuil=cuil) | Q(alumno_cuil_snapshot=cuil)
                        )
                        .values_list("alumno_id", flat=True)
                        .distinct()
                    )
                if len(alumno_ids) == 1:
                    alumno_id = next(iter(alumno_ids))
                elif not alumno_ids:
                    consulta_error = (
                        "No se encontró un alumno con ese CUIL dentro del banco de Educación Especial."
                    )
                else:
                    consulta_error = (
                        "El CUIL está asociado a más de un registro de alumno Especial."
                    )

    if alumno_id and not consulta_error:
        try:
            alumno = (
                _alumno_model()
                .objects.select_related(
                    "tipo_doc",
                    "sexo",
                    "est_civil",
                    "pais_nacimiento",
                    "prov_nacimiento",
                    "loc_nacimiento",
                    "pais_residencia",
                    "prov_residencia",
                    "loc_residencia",
                    "codigo_area",
                )
                .get(pk=alumno_id)
            )
        except _alumno_model().DoesNotExist:
            consulta_error = "No se encontró el alumno relacionado con el banco Especial."

    context = _persona_context(
        request,
        "Detalle de alumno",
        "Información personal e historial completo de Educación Especial.",
    )
    context.update(
        {
            "alumno": alumno,
            "persona_datos": None,
            "cuil_buscado": cuil,
            "inscripciones": [],
            "bancos": [],
            "consulta_error": consulta_error,
            "identificador_buscado": bool(alumno_id_param or cuil),
            "modo_prueba": modo_prueba,
        }
    )
    if alumno:
        personas = {} if modo_prueba else _personas_por_cuil([alumno])
        persona = personas.get(_solo_digitos(getattr(alumno, "cuil", "")))
        context["persona_datos"] = _datos_persona_alumno(
            alumno,
            persona,
            preferir_alumno=modo_prueba,
        )
        if not context["cuil_buscado"]:
            context["cuil_buscado"] = context["persona_datos"]["cuil"]
        context["bancos"] = list(
            EspecialAlumnoBanco.objects.filter(alumno_id=alumno.pk)
            .select_related("ciclo")
            .order_by("-ciclo__anio", "-pk")
        )
        _enriquecer_bancos(context["bancos"])
        resumen_cues = _resumen_cues_alumno(context["bancos"])
        context.update(
            {
                "visualizador_cue_original": resumen_cues["cue_original"],
                "visualizador_matricula_compartida": resumen_cues[
                    "matricula_compartida"
                ],
                "visualizador_cue_matricula": resumen_cues["cue_matricula"],
                "visualizador_padron_matricula": resumen_cues[
                    "padron_matricula"
                ],
            }
        )
        context["inscripciones"] = list(
            _inscripciones_visualizador([alumno.pk], detalle=True)
        )
        _enriquecer_inscripciones(
            context["inscripciones"],
            incluir_docentes=True,
        )
    return render(request, "especial/visualizador_detalle_alumno.html", context)


@especial_required
def visualizador_detalle_docente(request):
    _exigir_administrador(request)
    cuil = _solo_digitos(request.GET.get("cuil"))
    docente = EspecialDocenteBnh.objects.using(PADRON_DB_ALIAS).filter(cuil=cuil).first() if len(cuil) == 11 else None
    context = _persona_context(request, "Detalle de docente")
    context.update({
        "persona": docente,
        "cuil_buscado": cuil,
        "asignaciones": [],
        "secciones_filtro": [],
        "cueanexos_filtro": [],
        "roles_filtro": DocenteSeccion.Rol.choices,
        "estados_filtro": DocenteSeccion.Estado.choices,
        "estados_seleccionados": set(
            request.GET.getlist("estado")
            if request.GET.get("estado_aplicado")
            else [estado for estado, _ in DocenteSeccion.Estado.choices]
        ),
        "filtro_seccion": request.GET.get("seccion", ""),
        "filtro_cueanexo": request.GET.get("cueanexo", ""),
        "filtro_rol": request.GET.get("rol", ""),
    })
    if docente:
        asignaciones_base = DocenteSeccion.objects.filter(docente_cuil=cuil).select_related(
            "seccion", "seccion__ciclo"
        )
        context["secciones_filtro"] = [
            {"id": seccion_id, "nombre": nombre, "cueanexo": cueanexo}
            for seccion_id, nombre, cueanexo in asignaciones_base.values_list(
                "seccion_id", "seccion__nombre_seccion", "seccion__cueanexo"
            ).distinct().order_by("seccion__cueanexo", "seccion__nombre_seccion")
        ]
        context["cueanexos_filtro"] = sorted(
            {cueanexo for _, _, cueanexo in context["secciones_filtro"]}
        )

        asignaciones = asignaciones_base
        seccion_id = request.GET.get("seccion")
        if seccion_id and seccion_id.isdigit():
            asignaciones = asignaciones.filter(seccion_id=int(seccion_id))
        cueanexo = _solo_digitos(request.GET.get("cueanexo"))
        if cueanexo:
            asignaciones = asignaciones.filter(seccion__cueanexo=cueanexo)
        rol = request.GET.get("rol")
        if rol in dict(DocenteSeccion.Rol.choices):
            asignaciones = asignaciones.filter(rol=rol)
        estados = set(request.GET.getlist("estado"))
        estados_validos = {estado for estado, _ in DocenteSeccion.Estado.choices}
        if request.GET.get("estado_aplicado"):
            asignaciones = asignaciones.filter(estado__in=estados & estados_validos)
        else:
            asignaciones = asignaciones.filter(estado__in=estados_validos)

        asignaciones = list(
            asignaciones.order_by(
                "seccion__cueanexo", "seccion__nombre_seccion", "-fecha_desde"
            )
        )
        padron_por_cue = _padron_por_cueanexo(
            {asignacion.seccion.cueanexo for asignacion in asignaciones}
        )
        padron_por_cue_todas_ofertas = _padron_por_cueanexo(
            {asignacion.seccion.cueanexo for asignacion in asignaciones},
            solo_especial=False,
        )
        for asignacion in asignaciones:
            asignacion.visualizador_padron = padron_por_cue.get(
                asignacion.seccion.cueanexo,
                padron_por_cue_todas_ofertas.get(
                    asignacion.seccion.cueanexo,
                    {},
                ),
            )
        context["asignaciones"] = asignaciones
    return render(request, "especial/visualizador_detalle_docente.html", context)


@especial_required
def visualizador_detalle_director(request):
    _exigir_administrador(request)
    cuil = _solo_digitos(request.GET.get("cuil"))
    context = _persona_context(request, "Detalle de director")
    filas = []
    error = ""
    if len(cuil) == 11:
        try:
            filas = _datos_director(cuil)
        except (OperationalError, ProgrammingError):
            error = "No se pudo consultar la información del Padrón."
    context.update({"director": filas[0] if filas else None, "escuelas": filas, "cuil_buscado": cuil, "consulta_error": error})
    return render(request, "especial/visualizador_detalle_director.html", context)
