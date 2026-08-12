# -*- coding: utf-8 -*-
"""Motor declarativo y de solo lectura para el explorador global de Métricas.

La interfaz pública de este módulo está deliberadamente reducida a
``construir_configuracion_metricas`` y ``ejecutar_consulta_metricas``.  Las
rutas ORM que aparecen más abajo son internas y forman la lista blanca: ningún
nombre de campo recibido desde el navegador se convierte en un ``filter``.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.db.models import (
    Case,
    CharField,
    Count,
    DurationField,
    Exists,
    F,
    FloatField,
    Func,
    IntegerField,
    OuterRef,
    Q,
    Subquery,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Cast, Coalesce, Concat, ExtractMonth, NullIf

from .models import (
    CefActividad,
    CefAlumnoCef,
    CefAsistencia,
    CefBeneficioSinoTipo,
    CefCiclo,
    CefCodigoRa,
    CefDatosRelevamiento,
    CefDiaSemana,
    CefDocenteCef,
    CefDocenteGrupo,
    CefEje,
    CefEspacioComedorTipo,
    CefEstadoMaterialTipo,
    CefFuenteFinanciamientoTipo,
    CefGrupo,
    CefGrupoDiaFuncionamiento,
    CefInscripcion,
    CefInventarioMaterialEstado,
    CefMaterial,
    CefNivelActividad,
    CefOrientacionTipo,
    CefPrestacionTipo,
    CefRangoEtario,
    CefTurno,
    get_todos_los_cef,
    normalizar_cueanexo,
)


SIN_INFORMACION = "Sin información"
TODOS_LOS_CEF = "Todos los CEF"
CLAVES_TERRITORIO = ("region", "departamento", "localidad")

MESES = {
    1: "Enero",
    2: "Febrero",
    3: "Marzo",
    4: "Abril",
    5: "Mayo",
    6: "Junio",
    7: "Julio",
    8: "Agosto",
    9: "Septiembre",
    10: "Octubre",
    11: "Noviembre",
    12: "Diciembre",
}

TIPOS_GRAFICO = {
    "auto": "Automático",
    "kpi": "Indicador",
    "bar": "Barras",
    "grouped_bar": "Barras agrupadas",
    "stacked_bar": "Barras apiladas",
    "line": "Línea",
    "doughnut": "Dona",
}


class MetricasValidationError(ValueError):
    """Error de parámetros públicos del explorador de métricas."""


@dataclass(frozen=True)
class ConsultaResuelta:
    area: str
    indicador: str
    ciclos: tuple
    cefs: tuple
    todos_cef: bool
    agrupar: str
    comparar: str
    grafico: str
    filtros: dict


def _texto_limpio(valor):
    return " ".join(str(valor or "").split())


def _valor_json(valor):
    if valor is None:
        return None
    if isinstance(valor, Decimal):
        return float(valor)
    if isinstance(valor, (date,)):
        return valor.isoformat()
    return valor


def _snapshot(snapshot, fallback):
    return Coalesce(
        NullIf(F(snapshot), Value("")),
        F(fallback),
        Value(SIN_INFORMACION),
        output_field=CharField(),
    )


def _texto_campo(campo):
    return Coalesce(
        NullIf(F(campo), Value("")),
        Value(SIN_INFORMACION),
        output_field=CharField(),
    )


def _dimension_campo(campo, etiqueta=None, orden="texto"):
    etiqueta = etiqueta or campo
    return {
        "key": lambda campo=campo: F(campo),
        "label": lambda etiqueta=etiqueta: F(etiqueta),
        "sort": orden,
    }


def _dimension_snapshot(snapshot, fallback, orden="texto"):
    return {
        "key": lambda snapshot=snapshot, fallback=fallback: _snapshot(snapshot, fallback),
        "label": lambda snapshot=snapshot, fallback=fallback: _snapshot(snapshot, fallback),
        "sort": orden,
    }


def _dimension_texto(campo, orden="texto"):
    return {
        "key": lambda campo=campo: _texto_campo(campo),
        "label": lambda campo=campo: _texto_campo(campo),
        "sort": orden,
    }


def _edad_historica_expresion(fecha_referencia, fecha_nacimiento):
    """Años completos a la fecha histórica, calculados por PostgreSQL AGE."""

    intervalo = Func(
        F(fecha_referencia),
        F(fecha_nacimiento),
        function="AGE",
        output_field=DurationField(),
    )
    anios = Func(
        intervalo,
        function="DATE_PART",
        template="DATE_PART('year', %(expressions)s)",
        output_field=FloatField(),
    )
    return Cast(anios, IntegerField())


def _dimension_edad():
    clave = Coalesce(
        Cast(F("_metrica_edad"), CharField()),
        Value("__sin_informacion__"),
        output_field=CharField(),
    )
    return {
        "key": lambda clave=clave: clave.copy(),
        "label": lambda clave=clave: clave.copy(),
        "sort": "edad",
    }


def _dimension_ciclo(campo):
    return {
        "key": lambda campo=campo: F(campo),
        "label": lambda campo=campo: Cast(F(campo), CharField()),
        "sort": "numero",
    }


def _dimension_grupo(prefijo):
    nombre = f"{prefijo}nombre"
    numero = f"{prefijo}numero"
    actividad_snapshot = f"{prefijo}actividad_nombre_snapshot"
    actividad_fallback = f"{prefijo}actividad__nombre"
    cueanexo = f"{prefijo}cueanexo"
    ciclo = f"{prefijo}ciclo__anio"

    def etiqueta():
        nombre_grupo = Coalesce(
            NullIf(F(nombre), Value("")),
            Concat(Value("Grupo "), Cast(F(numero), CharField())),
            output_field=CharField(),
        )
        return Concat(
            _snapshot(actividad_snapshot, actividad_fallback),
            Value(" · "),
            nombre_grupo,
            Value(" · CEF "),
            F(cueanexo),
            Value(" · "),
            Cast(F(ciclo), CharField()),
            output_field=CharField(),
        )

    return {
        "key": lambda prefijo=prefijo: F(f"{prefijo}pk"),
        "label": etiqueta,
        "sort": "texto",
    }


def _dimension_codigo_ra(prefijo):
    def valor():
        return Coalesce(
            NullIf(F(f"{prefijo}codigo_ra_snapshot"), Value("")),
            F(f"{prefijo}codigo_ra_override__codigo"),
            F(f"{prefijo}actividad__codigo_ra__codigo"),
            Value(SIN_INFORMACION),
            output_field=CharField(),
        )

    return {
        "key": valor,
        "label": valor,
        "sort": "texto",
    }


def _dimension_dia(prefijo):
    return {
        "key": lambda prefijo=prefijo: F(
            f"{prefijo}dias_funcionamiento__dia_semana_id"
        ),
        "label": lambda prefijo=prefijo: F(
            f"{prefijo}dias_funcionamiento__dia_semana__nombre"
        ),
        "sort": "texto",
    }


def _dimensiones_grupo(prefijo):
    return {
        "ciclo": _dimension_ciclo(f"{prefijo}ciclo__anio"),
        "cef": _dimension_campo(f"{prefijo}cueanexo"),
        "actividad": _dimension_snapshot(
            f"{prefijo}actividad_nombre_snapshot",
            f"{prefijo}actividad__nombre",
        ),
        "eje": _dimension_snapshot(
            f"{prefijo}eje_nombre_snapshot",
            f"{prefijo}actividad__eje__nombre",
        ),
        "codigo_ra": _dimension_codigo_ra(prefijo),
        "nivel": _dimension_snapshot(
            f"{prefijo}nivel_nombre_snapshot",
            f"{prefijo}nivel__nombre",
        ),
        "rango_etario": _dimension_snapshot(
            f"{prefijo}rango_etario_nombre_snapshot",
            f"{prefijo}rango_etario__nombre",
        ),
        "turno": _dimension_snapshot(
            f"{prefijo}turno_nombre_snapshot",
            f"{prefijo}turno__nombre",
        ),
        "grupo": _dimension_grupo(prefijo),
        "estado": _dimension_campo(f"{prefijo}estado"),
        "dia": _dimension_dia(prefijo),
    }


def _filtros_grupo(prefijo):
    return {
        "actividad": f"{prefijo}actividad_id",
        "eje": f"{prefijo}actividad__eje_id",
        "codigo_ra": ("codigo_ra_efectivo", prefijo),
        "nivel": f"{prefijo}nivel_id",
        "rango_etario": f"{prefijo}rango_etario_id",
        "turno": f"{prefijo}turno_id",
        "grupo": f"{prefijo}pk",
        "estado": f"{prefijo}estado",
        "dia": ("dia_grupo", prefijo),
    }


_DIMENSIONES_ALUMNOS_BANCO = {
    "ciclo": _dimension_ciclo("ciclo__anio"),
    "cef": _dimension_campo("cueanexo"),
    "estado": _dimension_campo("estado"),
    "edad": _dimension_edad(),
    "sexo": _dimension_campo("alumno__sexo_id"),
}

_DIMENSIONES_INSCRIPCIONES = _dimensiones_grupo("grupo__")
_DIMENSIONES_INSCRIPCIONES.update(
    {
        "estado": _dimension_campo("estado"),
        "edad": _dimension_edad(),
        "sexo": _dimension_campo("alumno__sexo_id"),
    }
)

_DIMENSIONES_DOCENTES_BANCO = {
    "ciclo": _dimension_ciclo("ciclo__anio"),
    "cef": _dimension_campo("cueanexo"),
    "estado": _dimension_campo("estado"),
}

_DIMENSIONES_ASIGNACIONES = _dimensiones_grupo("grupo__")
_DIMENSIONES_ASIGNACIONES.update(
    {
        "estado": _dimension_campo("estado"),
        "rol": _dimension_campo("rol"),
    }
)

_DIMENSIONES_GRUPOS = _dimensiones_grupo("")

_DIMENSIONES_INVENTARIO = {
    "ciclo": _dimension_ciclo("inventario_material__ciclo__anio"),
    "cef": _dimension_campo("inventario_material__cueanexo"),
    "material": _dimension_snapshot(
        "inventario_material__material_nombre_snapshot",
        "inventario_material__material__nombre",
    ),
    "estado": _dimension_campo("estado__nombre"),
}

_DIMENSIONES_ASISTENCIA = _dimensiones_grupo("jornada__grupo__")
_DIMENSIONES_ASISTENCIA.update(
    {
        "estado": _dimension_campo("estado"),
        "fecha": _dimension_campo("jornada__fecha", orden="fecha"),
        "mes": {
            "key": lambda: ExtractMonth("jornada__fecha"),
            "label": lambda: ExtractMonth("jornada__fecha"),
            "sort": "numero",
        },
    }
)

_DIMENSIONES_RELEVAMIENTO = {
    "ciclo": _dimension_ciclo("ciclo__anio"),
    "cef": _dimension_campo("cueanexo"),
    "beneficio": _dimension_snapshot(
        "beneficio_nombre_snapshot",
        "beneficio_alimentario_gratuito__nombre",
    ),
    "financiamiento": _dimension_snapshot(
        "fuente_nombre_snapshot",
        "fuente_financiamiento__nombre",
    ),
    "prestacion": _dimension_snapshot(
        "prestacion_nombre_snapshot",
        "prestacion_tipo__nombre",
    ),
    "espacio_comedor": _dimension_snapshot(
        "espacio_comedor_nombre_snapshot",
        "espacio_comedor__nombre",
    ),
    "orientacion": _dimension_snapshot(
        "orientacion_nombre_snapshot",
        "c_orientacion__nombre",
    ),
}


FUENTES = {
    "alumnos_banco": {
        "model": CefAlumnoCef,
        "ciclo": "ciclo_id",
        "cef": "cueanexo",
        "dimensiones": _DIMENSIONES_ALUMNOS_BANCO,
        "filtros": {
            "estado": "estado",
            "sexo": "alumno__sexo_id",
            "edad": ("edad", "fecha_alta", "alumno__fecha_nacimiento"),
            "fecha": ("fecha", "fecha_alta"),
        },
        "filter_labels": {"fecha": "Fecha de alta"},
    },
    "inscripciones": {
        "model": CefInscripcion,
        "ciclo": "grupo__ciclo_id",
        "cef": "grupo__cueanexo",
        "dimensiones": _DIMENSIONES_INSCRIPCIONES,
        "filtros": {
            **_filtros_grupo("grupo__"),
            "estado": "estado",
            "sexo": "alumno__sexo_id",
            "edad": ("edad", "fecha_inscripcion", "alumno__fecha_nacimiento"),
            "fecha": ("fecha", "fecha_inscripcion"),
        },
        "filter_labels": {"fecha": "Fecha de inscripción"},
    },
    "docentes_banco": {
        "model": CefDocenteCef,
        "ciclo": "ciclo_id",
        "cef": "cueanexo",
        "dimensiones": _DIMENSIONES_DOCENTES_BANCO,
        "filtros": {
            "estado": "estado",
            "fecha": ("fecha", "fecha_alta"),
        },
        "filter_labels": {"fecha": "Fecha de alta"},
    },
    "asignaciones": {
        "model": CefDocenteGrupo,
        "ciclo": "grupo__ciclo_id",
        "cef": "grupo__cueanexo",
        "dimensiones": _DIMENSIONES_ASIGNACIONES,
        "filtros": {
            **_filtros_grupo("grupo__"),
            "estado": "estado",
            "rol": "rol",
            "fecha": ("fecha", "fecha_desde"),
        },
        "filter_labels": {"fecha": "Fecha de asignación (desde)"},
    },
    "grupos": {
        "model": CefGrupo,
        "ciclo": "ciclo_id",
        "cef": "cueanexo",
        "dimensiones": _DIMENSIONES_GRUPOS,
        "filtros": {
            **_filtros_grupo(""),
            "estado": "estado",
            "cupo": ("numero", "cupo_maximo"),
        },
    },
    "inventario": {
        "model": CefInventarioMaterialEstado,
        "ciclo": "inventario_material__ciclo_id",
        "cef": "inventario_material__cueanexo",
        "dimensiones": _DIMENSIONES_INVENTARIO,
        "filtros": {
            "material": "inventario_material__material_id",
            "estado": "estado_id",
        },
        "base_q": Q(estado__isnull=False),
    },
    "asistencia": {
        "model": CefAsistencia,
        "ciclo": "jornada__grupo__ciclo_id",
        "cef": "jornada__grupo__cueanexo",
        "dimensiones": _DIMENSIONES_ASISTENCIA,
        "filtros": {
            **_filtros_grupo("jornada__grupo__"),
            "estado": "estado",
            "fecha": ("fecha", "jornada__fecha"),
            "mes": ("mes", "jornada__fecha"),
        },
        "filter_labels": {"fecha": "Fecha de jornada"},
    },
    "relevamiento": {
        "model": CefDatosRelevamiento,
        "ciclo": "ciclo_id",
        "cef": "cueanexo",
        "dimensiones": _DIMENSIONES_RELEVAMIENTO,
        "filtros": {
            "beneficio": "beneficio_alimentario_gratuito_id",
            "financiamiento": "fuente_financiamiento_id",
            "prestacion": "prestacion_tipo_id",
            "espacio_comedor": "espacio_comedor_id",
            "orientacion": "c_orientacion_id",
        },
    },
}


DIMENSIONES_TERRITORIO = {
    "region": {"key": "region", "label": "Región"},
    "departamento": {"key": "departamento", "label": "Departamento"},
    "localidad": {"key": "localidad", "label": "Localidad"},
}

DIMENSIONES_META = {
    "ciclo": "Ciclo",
    "cef": "CEF",
    "actividad": "Actividad",
    "eje": "Eje",
    "codigo_ra": "Código RA",
    "nivel": "Nivel",
    "rango_etario": "Rango etario del grupo",
    "turno": "Turno",
    "grupo": "Grupo",
    "estado": "Estado",
    "edad": "Edad",
    "sexo": "Sexo",
    "rol": "Rol",
    "dia": "Día de funcionamiento",
    "material": "Material",
    "fecha": "Fecha",
    "mes": "Mes",
    "beneficio": "Beneficio alimentario",
    "financiamiento": "Fuente de financiamiento",
    "prestacion": "Tipo de prestación",
    "espacio_comedor": "Espacio comedor",
    "orientacion": "Orientación",
    **{clave: datos["label"] for clave, datos in DIMENSIONES_TERRITORIO.items()},
}


FILTROS_META = {
    "actividad": {"label": "Actividad", "type": "multi", "choices": "actividad"},
    "eje": {"label": "Eje", "type": "multi", "choices": "eje"},
    "codigo_ra": {"label": "Código RA", "type": "multi", "choices": "codigo_ra"},
    "nivel": {"label": "Nivel", "type": "multi", "choices": "nivel"},
    "rango_etario": {"label": "Rango etario", "type": "multi", "choices": "rango_etario"},
    "turno": {"label": "Turno", "type": "multi", "choices": "turno"},
    "grupo": {"label": "Grupo", "type": "multi", "choices": "grupo"},
    "estado": {"label": "Estado", "type": "multi", "choices": "estado"},
    "sexo": {"label": "Sexo", "type": "multi", "choices": "sexo"},
    "edad": {"label": "Edad", "type": "number_range", "min": 0, "max": 150},
    "fecha": {"label": "Fecha", "type": "date_range"},
    "mes": {"label": "Mes", "type": "multi", "choices": "mes"},
    "rol": {"label": "Rol", "type": "multi", "choices": "rol"},
    "dia": {"label": "Día de funcionamiento", "type": "multi", "choices": "dia"},
    "cupo": {"label": "Cupo máximo", "type": "number_range", "min": 1, "max": 100000},
    "material": {"label": "Material", "type": "multi", "choices": "material"},
    "beneficio": {"label": "Beneficio alimentario", "type": "multi", "choices": "beneficio"},
    "financiamiento": {"label": "Fuente de financiamiento", "type": "multi", "choices": "financiamiento"},
    "prestacion": {"label": "Tipo de prestación", "type": "multi", "choices": "prestacion"},
    "espacio_comedor": {"label": "Espacio comedor", "type": "multi", "choices": "espacio_comedor"},
    "orientacion": {"label": "Orientación", "type": "multi", "choices": "orientacion"},
    "region": {"label": "Región", "type": "multi", "choices": "region"},
    "departamento": {"label": "Departamento", "type": "multi", "choices": "departamento"},
    "localidad": {"label": "Localidad", "type": "multi", "choices": "localidad"},
}


def _indicador(
    label,
    source,
    metric,
    definition,
    filters,
    groupings,
    comparisons=None,
    unit="registros",
    notes=(),
    fixed_q=None,
    filter_overrides=None,
    filter_labels=None,
):
    return {
        "label": label,
        "source": source,
        "metric": metric,
        "definition": definition,
        "filters": tuple(filters),
        "groupings": tuple(groupings),
        "comparisons": tuple(
            dimension
            for dimension in (groupings if comparisons is None else comparisons)
            if dimension != "grupo"
        ),
        "unit": unit,
        "notes": tuple(notes),
        "fixed_q": fixed_q,
        "filter_overrides": dict(filter_overrides or {}),
        "filter_labels": dict(filter_labels or {}),
    }


def _etiquetas_filtros_indicador(indicador):
    etiquetas = dict(FUENTES[indicador["source"]].get("filter_labels", {}))
    etiquetas.update(indicador["filter_labels"])
    return etiquetas


FILTROS_TERRITORIO = ("region", "departamento", "localidad")
# Las dimensiones territoriales se expresan como CASE dentro de la consulta
# agregada. Así, también las medidas de personas únicas pueden deduplicar una
# misma persona presente en varios CEF del mismo territorio.
DIMENSIONES_GRUPO = (
    "ciclo",
    "cef",
    "actividad",
    "eje",
    "codigo_ra",
    "nivel",
    "rango_etario",
    "turno",
    "grupo",
    "estado",
)
DIMENSIONES_GRUPO_TERRITORIO = DIMENSIONES_GRUPO + FILTROS_TERRITORIO
FILTROS_GRUPO = (
    "actividad",
    "eje",
    "codigo_ra",
    "nivel",
    "rango_etario",
    "turno",
    "grupo",
    "estado",
    "dia",
) + FILTROS_TERRITORIO


AREAS = {
    "alumnos": {
        "label": "Alumnos",
        "filter_order": (
            "actividad",
            "eje",
            "codigo_ra",
            "nivel",
            "rango_etario",
            "turno",
            "grupo",
            "dia",
            "estado",
            "sexo",
            "edad",
            "fecha",
            *FILTROS_TERRITORIO,
        ),
        "indicators": {
            "alumnos_inscriptos_activos": _indicador(
                "Alumnos inscriptos actualmente",
                "inscripciones",
                {"kind": "distinct", "field": "alumno_id"},
                (
                    "Cantidad de alumnos con al menos una inscripción activa en el "
                    "alcance seleccionado. Cada persona cuenta una sola vez, aunque "
                    "tenga más de una inscripción."
                ),
                (
                    "actividad", "eje", "codigo_ra", "nivel", "rango_etario",
                    "turno", "grupo", "dia", "sexo", "edad", "fecha",
                    *FILTROS_TERRITORIO,
                ),
                (
                    "ciclo", "cef", "actividad", "eje", "codigo_ra", "nivel",
                    "rango_etario", "turno", "grupo", "edad", "sexo",
                    *FILTROS_TERRITORIO,
                ),
                unit="alumnos",
                notes=(
                    "La edad se calcula en años completos a la fecha de inscripción; "
                    "si falta la fecha de nacimiento se informa por separado.",
                ),
                fixed_q=Q(estado=CefInscripcion.Estado.ACTIVO),
            ),
            "alumnos_banco_unicos": _indicador(
                "Alumnos registrados en el banco CEF",
                "alumnos_banco",
                {"kind": "distinct", "field": "alumno_id"},
                (
                    "Cantidad de alumnos incorporados al banco CEF. Cada persona cuenta "
                    "una sola vez; no se mezclan estas incorporaciones con inscripciones "
                    "a grupos."
                ),
                ("estado", "sexo", "edad", "fecha", *FILTROS_TERRITORIO),
                ("ciclo", "cef", "estado", "edad", "sexo", *FILTROS_TERRITORIO),
                unit="alumnos",
                notes=(
                    "La edad se calcula en años completos a la fecha de alta en el banco CEF.",
                ),
            ),
            "alumnos_banco_activos": _indicador(
                "Alumnos activos en el banco CEF",
                "alumnos_banco",
                {"kind": "distinct", "field": "alumno_id"},
                "Cantidad de alumnos cuyo registro en el banco CEF está activo. Cada "
                "persona cuenta una sola vez.",
                ("sexo", "edad", "fecha", *FILTROS_TERRITORIO),
                ("ciclo", "cef", "edad", "sexo", *FILTROS_TERRITORIO),
                unit="alumnos",
                notes=(
                    "La edad se calcula en años completos a la fecha de alta en el banco CEF.",
                ),
                fixed_q=Q(estado=CefAlumnoCef.Estado.ACTIVO),
            ),
            "alumnos_banco_baja": _indicador(
                "Alumnos dados de baja del banco CEF",
                "alumnos_banco",
                {"kind": "distinct", "field": "alumno_id"},
                "Cantidad de alumnos con registro dado de baja en el banco CEF. Cada "
                "persona cuenta una sola vez.",
                ("sexo", "edad", "fecha", *FILTROS_TERRITORIO),
                ("ciclo", "cef", "edad", "sexo", *FILTROS_TERRITORIO),
                unit="alumnos",
                notes=(
                    "La edad se calcula en años completos a la fecha de alta en el banco CEF.",
                ),
                fixed_q=Q(estado=CefAlumnoCef.Estado.BAJA),
                filter_overrides={"fecha": ("fecha", "fecha_baja")},
                filter_labels={"fecha": "Fecha de baja"},
            ),
            "inscripciones_total": _indicador(
                "Total de inscripciones",
                "inscripciones",
                {"kind": "count", "field": "pk"},
                (
                    "Cantidad de registros de inscripción a grupos. Un alumno con más "
                    "de una inscripción aporta un registro por cada inscripción."
                ),
                (*FILTROS_GRUPO, "sexo", "edad", "fecha"),
                (*DIMENSIONES_GRUPO_TERRITORIO, "edad", "sexo"),
                unit="inscripciones",
                notes=(
                    "La edad se calcula en años completos a la fecha de inscripción.",
                ),
            ),
            "inscripciones_activas": _indicador(
                "Inscripciones activas",
                "inscripciones",
                {"kind": "count", "field": "pk"},
                "Cantidad de registros de inscripción cuyo estado actual es activo.",
                (
                    "actividad", "eje", "codigo_ra", "nivel", "rango_etario",
                    "turno", "grupo", "dia", "sexo", "edad", "fecha",
                    *FILTROS_TERRITORIO,
                ),
                tuple(d for d in DIMENSIONES_GRUPO_TERRITORIO if d != "estado")
                + ("edad", "sexo"),
                unit="inscripciones",
                notes=(
                    "La edad se calcula en años completos a la fecha de inscripción.",
                ),
                fixed_q=Q(estado=CefInscripcion.Estado.ACTIVO),
            ),
            "inscripciones_baja": _indicador(
                "Inscripciones dadas de baja",
                "inscripciones",
                {"kind": "count", "field": "pk"},
                "Cantidad de registros de inscripción cuyo estado actual es baja.",
                (
                    "actividad", "eje", "codigo_ra", "nivel", "rango_etario",
                    "turno", "grupo", "dia", "sexo", "edad", "fecha",
                    *FILTROS_TERRITORIO,
                ),
                tuple(d for d in DIMENSIONES_GRUPO_TERRITORIO if d != "estado")
                + ("edad", "sexo"),
                unit="inscripciones",
                notes=(
                    "La edad se calcula en años completos a la fecha de inscripción.",
                ),
                fixed_q=Q(estado=CefInscripcion.Estado.BAJA),
                filter_overrides={"fecha": ("fecha", "fecha_baja")},
                filter_labels={"fecha": "Fecha de baja"},
            ),
        },
    },
    "profesores": {
        "label": "Profesores",
        "filter_order": (
            "actividad", "eje", "codigo_ra", "nivel", "rango_etario",
            "turno", "grupo", "estado", "rol", "dia", "fecha",
            *FILTROS_TERRITORIO,
        ),
        "indicators": {
            "profesores_banco_unicos": _indicador(
                "Profesores registrados en el banco CEF",
                "docentes_banco",
                {"kind": "distinct", "field": "docente_cuil"},
                "Cantidad de profesores incorporados al banco CEF. Cada profesor cuenta "
                "una sola vez.",
                ("estado", "fecha", *FILTROS_TERRITORIO),
                ("ciclo", "cef", "estado", *FILTROS_TERRITORIO),
                unit="profesores",
            ),
            "profesores_banco_activos": _indicador(
                "Profesores activos en el banco CEF",
                "docentes_banco",
                {"kind": "distinct", "field": "docente_cuil"},
                "Cantidad de profesores cuyo registro en el banco CEF está activo. Cada "
                "profesor cuenta una sola vez.",
                ("fecha", *FILTROS_TERRITORIO),
                ("ciclo", "cef", *FILTROS_TERRITORIO),
                unit="profesores",
                fixed_q=Q(estado=CefDocenteCef.Estado.ACTIVO),
            ),
            "profesores_banco_baja": _indicador(
                "Profesores dados de baja del banco CEF",
                "docentes_banco",
                {"kind": "distinct", "field": "docente_cuil"},
                "Cantidad de profesores con registro dado de baja en el banco CEF. Cada "
                "profesor cuenta una sola vez.",
                ("fecha", *FILTROS_TERRITORIO),
                ("ciclo", "cef", *FILTROS_TERRITORIO),
                unit="profesores",
                fixed_q=Q(estado=CefDocenteCef.Estado.BAJA),
                filter_overrides={"fecha": ("fecha", "fecha_baja")},
                filter_labels={"fecha": "Fecha de baja"},
            ),
            "profesores_asignados_activos": _indicador(
                "Profesores con asignación activa",
                "asignaciones",
                {"kind": "distinct", "field": "docente_cuil"},
                (
                    "Cantidad de profesores con al menos una asignación activa a un grupo. "
                    "Cada profesor cuenta una sola vez en el total."
                ),
                (
                    "actividad", "eje", "codigo_ra", "nivel", "rango_etario",
                    "turno", "grupo", "rol", "dia", "fecha", *FILTROS_TERRITORIO,
                ),
                (
                    "ciclo", "cef", "actividad", "eje", "codigo_ra", "nivel",
                    "rango_etario", "turno", "grupo", "rol",
                    *FILTROS_TERRITORIO,
                ),
                unit="profesores",
                fixed_q=Q(estado=CefDocenteGrupo.Estado.ACTIVO),
            ),
            "asignaciones_total": _indicador(
                "Asignaciones de profesores registradas",
                "asignaciones",
                {"kind": "count", "field": "pk"},
                "Cantidad de registros de asignación de profesores a grupos.",
                (*FILTROS_GRUPO, "rol", "fecha"),
                (*DIMENSIONES_GRUPO_TERRITORIO, "rol"),
                unit="asignaciones",
            ),
            "asignaciones_activas": _indicador(
                "Asignaciones de profesores activas",
                "asignaciones",
                {"kind": "count", "field": "pk"},
                "Cantidad de asignaciones a grupos cuyo estado actual es activo.",
                (
                    "actividad", "eje", "codigo_ra", "nivel", "rango_etario",
                    "turno", "grupo", "rol", "dia", "fecha", *FILTROS_TERRITORIO,
                ),
                tuple(d for d in DIMENSIONES_GRUPO_TERRITORIO if d != "estado")
                + ("rol",),
                unit="asignaciones",
                fixed_q=Q(estado=CefDocenteGrupo.Estado.ACTIVO),
            ),
            "asignaciones_baja": _indicador(
                "Asignaciones de profesores dadas de baja",
                "asignaciones",
                {"kind": "count", "field": "pk"},
                "Cantidad de asignaciones a grupos cuyo estado actual es baja.",
                (
                    "actividad", "eje", "codigo_ra", "nivel", "rango_etario",
                    "turno", "grupo", "rol", "dia", "fecha", *FILTROS_TERRITORIO,
                ),
                tuple(d for d in DIMENSIONES_GRUPO_TERRITORIO if d != "estado")
                + ("rol",),
                unit="asignaciones",
                fixed_q=Q(estado=CefDocenteGrupo.Estado.BAJA),
                filter_overrides={"fecha": ("fecha", "fecha_hasta")},
                filter_labels={"fecha": "Fecha de baja (hasta)"},
            ),
            "asignaciones_titulares": _indicador(
                "Asignaciones titulares de profesores",
                "asignaciones",
                {"kind": "count", "field": "pk"},
                "Cantidad de asignaciones registradas con rol titular.",
                FILTROS_GRUPO + ("fecha",),
                tuple(d for d in DIMENSIONES_GRUPO_TERRITORIO if d != "rol"),
                unit="asignaciones",
                fixed_q=Q(rol=CefDocenteGrupo.Rol.TITULAR),
            ),
            "asignaciones_suplentes": _indicador(
                "Asignaciones suplentes de profesores",
                "asignaciones",
                {"kind": "count", "field": "pk"},
                "Cantidad de asignaciones registradas con rol suplente.",
                FILTROS_GRUPO + ("fecha",),
                tuple(d for d in DIMENSIONES_GRUPO_TERRITORIO if d != "rol"),
                unit="asignaciones",
                fixed_q=Q(rol=CefDocenteGrupo.Rol.SUPLENTE),
            ),
        },
    },
    "grupos": {
        "label": "Grupos",
        "filter_order": (*FILTROS_GRUPO, "cupo"),
        "indicators": {
            "grupos_total": _indicador(
                "Grupos",
                "grupos",
                {"kind": "count", "field": "pk", "distinct": True},
                "Cantidad de grupos del alcance, contados sin unir inscripciones, docentes ni días.",
                (*FILTROS_GRUPO, "cupo"),
                (*DIMENSIONES_GRUPO_TERRITORIO, "dia"),
                unit="grupos",
            ),
            "grupos_activos": _indicador(
                "Grupos activos",
                "grupos",
                {"kind": "count", "field": "pk", "distinct": True},
                "Cantidad de grupos cuyo estado actual es activo.",
                tuple(f for f in FILTROS_GRUPO if f != "estado") + ("cupo",),
                tuple(d for d in DIMENSIONES_GRUPO_TERRITORIO if d != "estado")
                + ("dia",),
                unit="grupos",
                fixed_q=Q(estado=CefGrupo.Estado.ACTIVO),
            ),
            "grupos_baja": _indicador(
                "Grupos dados de baja",
                "grupos",
                {"kind": "count", "field": "pk", "distinct": True},
                "Cantidad de grupos cuyo estado actual es baja.",
                tuple(f for f in FILTROS_GRUPO if f != "estado") + ("cupo",),
                tuple(d for d in DIMENSIONES_GRUPO_TERRITORIO if d != "estado")
                + ("dia",),
                unit="grupos",
                fixed_q=Q(estado=CefGrupo.Estado.BAJA),
            ),
            "alumnos_activos_grupos": _indicador(
                "Alumnos inscriptos en grupos activos",
                "grupos",
                {"kind": "active_students"},
                (
                    "Suma de inscripciones activas por grupo. El conteo de cada grupo "
                    "se calcula en una subconsulta independiente para evitar productos "
                    "con docentes o días."
                ),
                (*FILTROS_GRUPO, "cupo"),
                (*DIMENSIONES_GRUPO_TERRITORIO, "dia"),
                unit="alumnos",
            ),
            "promedio_alumnos_grupo": _indicador(
                "Promedio de alumnos por grupo activo",
                "grupos",
                {"kind": "average_active_students"},
                (
                    "Promedio de inscripciones activas por grupo incluido. Cada grupo "
                    "pesa una vez y su cantidad se obtiene mediante una subconsulta."
                ),
                (*FILTROS_GRUPO, "cupo"),
                (*DIMENSIONES_GRUPO_TERRITORIO, "dia"),
                comparisons=("ciclo", "cef", "actividad", "turno", "estado"),
                unit="alumnos por grupo",
            ),
            "cupo_total": _indicador(
                "Cupo total informado",
                "grupos",
                {"kind": "sum", "field": "cupo_maximo"},
                "Suma de los cupos máximos informados; los grupos sin cupo no agregan unidades.",
                (*FILTROS_GRUPO, "cupo"),
                (*DIMENSIONES_GRUPO_TERRITORIO, "dia"),
                unit="vacantes",
            ),
            "ocupacion": _indicador(
                "Porcentaje de ocupación de grupos",
                "grupos",
                {"kind": "occupancy"},
                (
                    "Inscripciones activas de los grupos con cupo válido, divididas por "
                    "la suma de esos cupos. Es una ocupación ponderada, no un promedio "
                    "simple de porcentajes."
                ),
                tuple(f for f in FILTROS_GRUPO if f != "estado") + ("cupo",),
                tuple(d for d in DIMENSIONES_GRUPO_TERRITORIO if d != "estado")
                + ("dia",),
                comparisons=("ciclo", "cef", "actividad", "turno"),
                unit="%",
                notes=("Los grupos sin cupo máximo informado quedan fuera del denominador.",),
                fixed_q=Q(
                    estado=CefGrupo.Estado.ACTIVO,
                    cupo_maximo__gt=0,
                ),
            ),
        },
    },
    "inventario": {
        "label": "Inventario",
        "filter_order": ("material", "estado", *FILTROS_TERRITORIO),
        "indicators": {
            "unidades": _indicador(
                "Unidades de material",
                "inventario",
                {"kind": "sum", "field": "cantidad"},
                (
                    "Suma de cantidades de la distribución vigente por estado de material, "
                    "considerando solamente filas asociadas al catálogo de estados."
                ),
                ("material", "estado", *FILTROS_TERRITORIO),
                ("ciclo", "cef", "material", "estado", *FILTROS_TERRITORIO),
                unit="unidades",
                notes=(
                    "No se utiliza el campo de cantidad heredado de la cabecera de inventario.",
                ),
            ),
        },
    },
    "asistencia": {
        "label": "Asistencia",
        "filter_order": (
            "actividad", "eje", "codigo_ra", "nivel", "rango_etario",
            "turno", "grupo", "estado", "dia", "fecha", "mes",
            *FILTROS_TERRITORIO,
        ),
        "indicators": {},
    },
    "relevamiento": {
        "label": "Relevamiento de CEF",
        "filter_order": (
            "beneficio", "financiamiento", "prestacion", "espacio_comedor",
            "orientacion", *FILTROS_TERRITORIO,
        ),
        "indicators": {},
    },
}


_FILTROS_ASISTENCIA = (
    "actividad", "eje", "codigo_ra", "nivel", "rango_etario", "turno",
    "grupo", "estado", "dia", "fecha", "mes", *FILTROS_TERRITORIO,
)
_DIMENSIONES_ASISTENCIA_PUBLICAS = (
    "ciclo", "cef", "actividad", "eje", "codigo_ra", "nivel",
    "rango_etario", "turno", "grupo", "estado", "fecha", "mes",
    *FILTROS_TERRITORIO,
)


AREAS["asistencia"]["indicators"].update(
    {
        "jornadas": _indicador(
            "Jornadas con asistencia",
            "asistencia",
            {"kind": "distinct", "field": "jornada_id"},
            (
                "Cantidad de jornadas con al menos un registro de asistencia dentro de "
                "los filtros. Cada jornada cuenta una sola vez."
            ),
            _FILTROS_ASISTENCIA,
            _DIMENSIONES_ASISTENCIA_PUBLICAS,
            unit="jornadas",
        ),
        "registros": _indicador(
            "Registros de asistencia",
            "asistencia",
            {"kind": "count", "field": "pk"},
            "Cantidad de filas de asistencia efectivamente registradas.",
            _FILTROS_ASISTENCIA,
            _DIMENSIONES_ASISTENCIA_PUBLICAS,
            unit="registros",
        ),
        "presentes": _indicador(
            "Registros presentes",
            "asistencia",
            {"kind": "count", "field": "pk"},
            "Cantidad de registros de asistencia cuyo estado es presente.",
            tuple(f for f in _FILTROS_ASISTENCIA if f != "estado"),
            tuple(d for d in _DIMENSIONES_ASISTENCIA_PUBLICAS if d != "estado"),
            unit="registros",
            fixed_q=Q(estado=CefAsistencia.Estado.PRESENTE),
        ),
        "ausentes": _indicador(
            "Registros ausentes",
            "asistencia",
            {"kind": "count", "field": "pk"},
            (
                "Cantidad de registros marcados explícitamente como ausente; la falta "
                "de un registro nunca se interpreta como ausencia."
            ),
            tuple(f for f in _FILTROS_ASISTENCIA if f != "estado"),
            tuple(d for d in _DIMENSIONES_ASISTENCIA_PUBLICAS if d != "estado"),
            unit="registros",
            fixed_q=Q(estado=CefAsistencia.Estado.AUSENTE),
        ),
        "justificadas": _indicador(
            "Ausencias justificadas",
            "asistencia",
            {"kind": "count", "field": "pk"},
            "Cantidad de registros marcados explícitamente como ausencia justificada.",
            tuple(f for f in _FILTROS_ASISTENCIA if f != "estado"),
            tuple(d for d in _DIMENSIONES_ASISTENCIA_PUBLICAS if d != "estado"),
            unit="registros",
            fixed_q=Q(estado=CefAsistencia.Estado.JUSTIFICADA),
        ),
    }
)

for _clave, _label, _estado in (
    ("porcentaje_presentes", "Porcentaje de registros presentes", CefAsistencia.Estado.PRESENTE),
    ("porcentaje_ausentes", "Porcentaje de registros ausentes", CefAsistencia.Estado.AUSENTE),
    (
        "porcentaje_justificadas",
        "Porcentaje de ausencias justificadas",
        CefAsistencia.Estado.JUSTIFICADA,
    ),
):
    AREAS["asistencia"]["indicators"][_clave] = _indicador(
        _label,
        "asistencia",
        {"kind": "state_ratio", "state": _estado},
        (
            f"{_label} sobre el total de registros de asistencia incluidos en la consulta. "
            "La ausencia de una fila no integra el denominador."
        ),
        tuple(f for f in _FILTROS_ASISTENCIA if f != "estado"),
        tuple(d for d in _DIMENSIONES_ASISTENCIA_PUBLICAS if d != "estado"),
        unit="%",
    )


_FILTROS_RELEVAMIENTO = (
    "beneficio", "financiamiento", "prestacion", "espacio_comedor",
    "orientacion", *FILTROS_TERRITORIO,
)
_DIMENSIONES_RELEVAMIENTO_PUBLICAS = (
    "ciclo", "cef", "beneficio", "financiamiento", "prestacion",
    "espacio_comedor", "orientacion", *FILTROS_TERRITORIO,
)
AREAS["relevamiento"]["indicators"].update(
    {
        "cef_relevados": _indicador(
            "CEF con relevamiento",
            "relevamiento",
            {"kind": "distinct", "field": "cueanexo"},
            "Cantidad de CEF con al menos un relevamiento en el alcance. Cada CEF cuenta "
            "una sola vez.",
            _FILTROS_RELEVAMIENTO,
            _DIMENSIONES_RELEVAMIENTO_PUBLICAS,
            unit="CEF",
        ),
        "relevamientos": _indicador(
            "Relevamientos registrados",
            "relevamiento",
            {"kind": "count", "field": "pk"},
            "Cantidad de snapshots de relevamiento por CEF y ciclo.",
            _FILTROS_RELEVAMIENTO,
            _DIMENSIONES_RELEVAMIENTO_PUBLICAS,
            unit="relevamientos",
        ),
        "porcentaje_distribucion": _indicador(
            "Distribución de relevamientos (%)",
            "relevamiento",
            {"kind": "distribution_ratio"},
            (
                "Porcentaje de relevamientos de cada categoría sobre el total filtrado. "
                "Con una comparación, cada celda conserva el mismo denominador global."
            ),
            _FILTROS_RELEVAMIENTO,
            _DIMENSIONES_RELEVAMIENTO_PUBLICAS,
            unit="%",
            notes=(
                "Sin desglose, el resultado es 100 % cuando existen relevamientos; "
                "sin denominador se informa como no calculable.",
            ),
        ),
    }
)


MODELOS_CATALOGO = {
    "actividad": CefActividad,
    "eje": CefEje,
    "codigo_ra": CefCodigoRa,
    "nivel": CefNivelActividad,
    "rango_etario": CefRangoEtario,
    "turno": CefTurno,
    "dia": CefDiaSemana,
    "material": CefMaterial,
    "estado_material": CefEstadoMaterialTipo,
    "beneficio": CefBeneficioSinoTipo,
    "financiamiento": CefFuenteFinanciamientoTipo,
    "prestacion": CefPrestacionTipo,
    "espacio_comedor": CefEspacioComedorTipo,
    "orientacion": CefOrientacionTipo,
}


def _cargar_ciclos():
    return list(
        CefCiclo.objects.order_by("anio", "pk").values(
            "pk", "anio", "descripcion", "activo", "actual", "cerrado"
        )
    )


def _cargar_cefs():
    """Construye en una sola consulta un Padrón deduplicado por CUE-Anexo."""

    campos = (
        "cueanexo",
        "nom_est",
        "region_loc",
        "departamento",
        "localidad",
    )
    filas = get_todos_los_cef().order_by("cueanexo", "nom_est", "pk").values(*campos)
    resultado = {}
    for fila in filas:
        cueanexo = normalizar_cueanexo(fila.get("cueanexo"))
        if not cueanexo:
            continue

        nombre = _texto_limpio(fila.get("nom_est"))
        actual = resultado.setdefault(
            cueanexo,
            {
                "value": cueanexo,
                "label": f"{cueanexo} - {nombre}" if nombre else cueanexo,
                "nombre": nombre,
                "region": _texto_limpio(fila.get("region_loc")) or SIN_INFORMACION,
                "departamento": _texto_limpio(fila.get("departamento")) or SIN_INFORMACION,
                "localidad": _texto_limpio(fila.get("localidad")) or SIN_INFORMACION,
            },
        )

        # La vista puede repetir una oferta. Se conserva la primera etiqueta estable,
        # pero se completan datos territoriales que estuvieran vacíos en esa fila.
        if not actual["nombre"] and nombre:
            actual["nombre"] = nombre
            actual["label"] = f"{cueanexo} - {nombre}"
        for clave, campo in (
            ("region", "region_loc"),
            ("departamento", "departamento"),
            ("localidad", "localidad"),
        ):
            nuevo = _texto_limpio(fila.get(campo))
            if actual[clave] == SIN_INFORMACION and nuevo:
                actual[clave] = nuevo

    return dict(sorted(resultado.items(), key=lambda item: item[0]))


def _opciones_modelo(modelo, etiqueta="nombre"):
    filas = modelo.objects.order_by("pk").values("pk", etiqueta)
    opciones = []
    for fila in filas:
        label = _texto_limpio(fila.get(etiqueta)) or str(fila["pk"])
        opciones.append({"value": str(fila["pk"]), "label": label})
    return opciones


def _opciones_grupos():
    filas = CefGrupo.objects.order_by(
        "ciclo__anio", "cueanexo", "actividad__nombre", "numero", "pk"
    ).values(
        "pk",
        "cueanexo",
        "ciclo__anio",
        "nombre",
        "numero",
        "actividad_nombre_snapshot",
        "actividad__nombre",
    )
    opciones = []
    for fila in filas:
        actividad = (
            _texto_limpio(fila.get("actividad_nombre_snapshot"))
            or _texto_limpio(fila.get("actividad__nombre"))
            or SIN_INFORMACION
        )
        nombre = _texto_limpio(fila.get("nombre")) or f"Grupo {fila['numero']}"
        label = (
            f"{actividad} · {nombre} · CEF {fila['cueanexo']} · "
            f"{fila['ciclo__anio']}"
        )
        opciones.append({"value": str(fila["pk"]), "label": label})
    return opciones


def _modelo_sexo():
    alumno_model = CefInscripcion._meta.get_field("alumno").remote_field.model
    return alumno_model._meta.get_field("sexo").remote_field.model


def _opciones_sexo():
    modelo = _modelo_sexo()
    return [
        {"value": str(obj.pk), "label": _texto_limpio(str(obj)) or str(obj.pk)}
        for obj in modelo._default_manager.order_by("pk")
    ]


def _opciones_choices(choices):
    return [{"value": str(valor), "label": str(label)} for valor, label in choices]


def _opciones_territorio(cef_map, clave):
    valores = sorted(
        {datos.get(clave) or SIN_INFORMACION for datos in cef_map.values()},
        key=lambda valor: (valor == SIN_INFORMACION, valor.casefold()),
    )
    return [{"value": valor, "label": valor} for valor in valores]


def _opciones_filtro(area, clave, cef_map, cache):
    cache_key = (area if clave == "estado" else "global", clave)
    if cache_key in cache:
        return cache[cache_key]

    if clave in CLAVES_TERRITORIO:
        opciones = _opciones_territorio(cef_map, clave)
    elif clave == "grupo":
        opciones = _opciones_grupos()
    elif clave == "sexo":
        opciones = _opciones_sexo()
    elif clave == "mes":
        opciones = [
            {"value": str(numero), "label": nombre}
            for numero, nombre in MESES.items()
        ]
    elif clave == "estado":
        if area == "inventario":
            opciones = _opciones_modelo(CefEstadoMaterialTipo)
        elif area == "asistencia":
            opciones = _opciones_choices(CefAsistencia.Estado.choices)
        elif area == "grupos":
            opciones = _opciones_choices(CefGrupo.Estado.choices)
        elif area == "profesores":
            opciones = _opciones_choices(CefDocenteGrupo.Estado.choices)
        else:
            opciones = _opciones_choices(CefInscripcion.Estado.choices)
    elif clave == "rol":
        opciones = _opciones_choices(CefDocenteGrupo.Rol.choices)
    elif clave == "turno":
        opciones = _opciones_modelo(CefTurno)
    elif clave == "codigo_ra":
        filas = CefCodigoRa.objects.order_by("orden", "codigo", "pk").values(
            "pk", "codigo", "descripcion"
        )
        opciones = [
            {
                "value": str(fila["pk"]),
                "label": f"{fila['codigo']} - {_texto_limpio(fila['descripcion'])}".strip(" -"),
            }
            for fila in filas
        ]
    else:
        modelo = MODELOS_CATALOGO.get(clave)
        opciones = _opciones_modelo(modelo) if modelo else []

    cache[cache_key] = opciones
    return opciones


def _definicion_filtro(area, clave, cef_map, cache):
    meta = FILTROS_META[clave]
    definicion = {
        "key": clave,
        "label": meta["label"],
        "type": meta["type"],
    }
    if meta["type"] == "multi":
        definicion["choices"] = _opciones_filtro(area, clave, cef_map, cache)
    else:
        definicion["from_param"] = f"f_{clave}_desde"
        definicion["to_param"] = f"f_{clave}_hasta"
        if "min" in meta:
            definicion["min"] = meta["min"]
        if "max" in meta:
            definicion["max"] = meta["max"]
    return definicion


def construir_configuracion_metricas():
    """Devuelve toda la lista blanca serializable que consume la interfaz."""

    ciclos_db = _cargar_ciclos()
    cef_map = _cargar_cefs()
    opciones_cache = {}
    ciclos = [
        {
            "value": str(fila["pk"]),
            "label": str(fila["anio"]),
            "anio": fila["anio"],
            "descripcion": fila["descripcion"] or "",
            "activo": bool(fila["activo"]),
            "actual": bool(fila["actual"]),
            "cerrado": bool(fila["cerrado"]),
        }
        for fila in ciclos_db
    ]
    ciclo_actual = next((c for c in ciclos if c["actual"]), None)
    if ciclo_actual is None and ciclos:
        ciclo_actual = max(ciclos, key=lambda item: (item["anio"], int(item["value"])))

    areas = []
    for area_key, area in AREAS.items():
        filtros_usados = {
            clave
            for indicador in area["indicators"].values()
            for clave in indicador["filters"]
        }
        filtros = [
            _definicion_filtro(area_key, clave, cef_map, opciones_cache)
            for clave in area["filter_order"]
            if clave in filtros_usados
        ]

        dimensiones_usadas = {
            clave
            for indicador in area["indicators"].values()
            for clave in indicador["groupings"] + indicador["comparisons"]
        }
        dimensiones = [
            {"key": clave, "label": DIMENSIONES_META[clave]}
            for clave in DIMENSIONES_META
            if clave in dimensiones_usadas
        ]
        indicadores = []
        for key, indicador in area["indicators"].items():
            etiquetas_filtro = _etiquetas_filtros_indicador(indicador)
            indicadores.append(
                {
                    "key": key,
                    "label": indicador["label"],
                    "definition": indicador["definition"],
                    "notes": list(indicador["notes"]),
                    "unit": indicador["unit"],
                    "filters": list(dict.fromkeys(indicador["filters"])),
                    "filter_labels": etiquetas_filtro,
                    "groupings": list(dict.fromkeys(indicador["groupings"])),
                    "comparisons": list(dict.fromkeys(indicador["comparisons"])),
                }
            )

        areas.append(
            {
                "key": area_key,
                "label": area["label"],
                "filters": filtros,
                "dimensions": dimensiones,
                "indicators": indicadores,
            }
        )

    return {
        "areas": areas,
        "ciclos": ciclos,
        "cefs": list(cef_map.values()),
        "defaults": {
            "ciclos": [ciclo_actual["value"]] if ciclo_actual else [],
            "cefs": [],
            "area": "alumnos",
            "indicador": "alumnos_inscriptos_activos",
            "agrupar": "cef",
            "comparar": "",
            "grafico": "auto",
        },
        "opciones": {
            "cef_vacio_significa_todos": True,
            "sin_informacion": SIN_INFORMACION,
            "graficos": [
                {"value": clave, "label": label}
                for clave, label in TIPOS_GRAFICO.items()
            ],
        },
    }


PARAMETROS_BASE = {
    "ciclos",
    "cefs",
    "area",
    "indicador",
    "agrupar",
    "comparar",
    "grafico",
}


def _parametros_claves(params):
    return set(params.keys()) if hasattr(params, "keys") else set(params)


def _parametro_presente(params, clave):
    try:
        return clave in params
    except TypeError:
        return False


def _parametro(params, clave, default=""):
    valor = params.get(clave, default)
    if isinstance(valor, (list, tuple)):
        return valor[-1] if valor else default
    return valor


def _parametro_lista(params, clave):
    if hasattr(params, "getlist"):
        valores = params.getlist(clave)
    else:
        valor = params.get(clave, [])
        valores = valor if isinstance(valor, (list, tuple)) else [valor]
    resultado = []
    for valor in valores:
        limpio = str(valor or "").strip()
        if limpio and limpio not in resultado:
            resultado.append(limpio)
    return resultado


def _valor_fecha(valor, etiqueta):
    try:
        return date.fromisoformat(valor)
    except (TypeError, ValueError):
        raise MetricasValidationError(
            f"{etiqueta} debe tener formato AAAA-MM-DD."
        ) from None


def _valor_entero(valor, etiqueta, minimo=None, maximo=None):
    try:
        numero = int(valor)
    except (TypeError, ValueError):
        raise MetricasValidationError(f"{etiqueta} debe ser un número entero.") from None
    if minimo is not None and numero < minimo:
        raise MetricasValidationError(f"{etiqueta} no puede ser menor que {minimo}.")
    if maximo is not None and numero > maximo:
        raise MetricasValidationError(f"{etiqueta} no puede ser mayor que {maximo}.")
    return numero


def _tipos_grafico_compatibles(agrupar, comparar, indicador=None):
    if not agrupar:
        return ("kpi",)
    temporal = agrupar in {"ciclo", "fecha", "mes"}
    kind = (indicador or {}).get("metric", {}).get("kind")
    if comparar:
        tipos = ["grouped_bar"]
        if kind in {"count", "sum", "active_students"} and comparar != "dia":
            tipos.append("stacked_bar")
        if temporal:
            tipos.append("line")
        return tuple(tipos)
    tipos = ["bar"]
    if kind in {"count", "sum", "distribution_ratio"} and agrupar != "dia":
        tipos.append("doughnut")
    if temporal:
        tipos.append("line")
    return tuple(tipos)


def _resolver_consulta(params, ciclos_db, cef_map):
    area_key = str(_parametro(params, "area", "alumnos") or "alumnos").strip()
    area = AREAS.get(area_key)
    if area is None:
        raise MetricasValidationError("El área solicitada no está permitida.")

    primer_indicador = next(iter(area["indicators"]))
    indicador_default = (
        "alumnos_inscriptos_activos" if area_key == "alumnos" else primer_indicador
    )
    indicador_key = str(
        _parametro(params, "indicador", indicador_default) or indicador_default
    ).strip()
    indicador = area["indicators"].get(indicador_key)
    if indicador is None:
        raise MetricasValidationError("El indicador solicitado no está permitido para el área.")

    filtros_permitidos = set(indicador["filters"])
    for clave_parametro in _parametros_claves(params) - PARAMETROS_BASE:
        if not clave_parametro.startswith("f_"):
            raise MetricasValidationError(
                f"El parámetro '{clave_parametro}' no está permitido."
            )
        resto = clave_parametro[2:]
        sufijo = ""
        for candidato in ("_desde", "_hasta"):
            if resto.endswith(candidato):
                resto = resto[: -len(candidato)]
                sufijo = candidato
                break
        if resto not in filtros_permitidos:
            raise MetricasValidationError(
                f"El filtro '{resto}' no está permitido para el indicador."
            )
        tipo = FILTROS_META[resto]["type"]
        if tipo == "multi" and sufijo:
            raise MetricasValidationError(f"El filtro '{resto}' no admite rangos.")
        if tipo != "multi" and not sufijo:
            raise MetricasValidationError(
                f"El filtro '{resto}' requiere límites desde/hasta."
            )

    ciclos_por_valor = {str(fila["pk"]): fila for fila in ciclos_db}
    ciclos_solicitados = _parametro_lista(params, "ciclos")
    if not ciclos_solicitados:
        actual = next((fila for fila in ciclos_db if fila["actual"]), None)
        if actual is None and ciclos_db:
            actual = max(ciclos_db, key=lambda fila: (fila["anio"], fila["pk"]))
        ciclos_solicitados = [str(actual["pk"])] if actual else []
    invalidos = [valor for valor in ciclos_solicitados if valor not in ciclos_por_valor]
    if invalidos:
        raise MetricasValidationError("Uno o más ciclos seleccionados no existen.")
    ciclos_ordenados = tuple(
        int(valor)
        for valor in sorted(
            ciclos_solicitados,
            key=lambda valor: (
                ciclos_por_valor[valor]["anio"],
                ciclos_por_valor[valor]["pk"],
            ),
        )
    )

    cefs_solicitados = _parametro_lista(params, "cefs")
    todos_cef = not cefs_solicitados
    if any(valor not in cef_map for valor in cefs_solicitados):
        raise MetricasValidationError("Uno o más CEF seleccionados no existen en Padrón.")
    cefs = tuple(cefs_solicitados or cef_map.keys())

    if _parametro_presente(params, "agrupar"):
        agrupar = str(_parametro(params, "agrupar", "") or "").strip()
    else:
        agrupar = "cef" if "cef" in indicador["groupings"] else ""
    if agrupar and agrupar not in indicador["groupings"]:
        raise MetricasValidationError(
            "La agrupación solicitada no es compatible con el indicador."
        )

    comparar = str(_parametro(params, "comparar", "") or "").strip()
    if comparar and comparar not in indicador["comparisons"]:
        raise MetricasValidationError(
            "La comparación solicitada no es compatible con el indicador."
        )
    if comparar and not agrupar:
        raise MetricasValidationError("Para comparar primero debe seleccionar una agrupación.")
    if comparar and comparar == agrupar:
        raise MetricasValidationError("La agrupación y la comparación deben ser diferentes.")
    if comparar and agrupar == "grupo":
        raise MetricasValidationError(
            "La dimensión Grupo ya identifica el CEF, el ciclo y la actividad; "
            "no admite una comparación adicional."
        )

    grafico = str(_parametro(params, "grafico", "auto") or "auto").strip()
    if grafico not in TIPOS_GRAFICO:
        raise MetricasValidationError("El tipo de gráfico solicitado no está permitido.")
    compatibles = _tipos_grafico_compatibles(agrupar, comparar, indicador)
    if grafico != "auto" and grafico not in compatibles:
        raise MetricasValidationError(
            "El tipo de gráfico no es compatible con la consulta solicitada."
        )

    filtros = {}
    cache_opciones = {}
    for clave in indicador["filters"]:
        meta = FILTROS_META[clave]
        if meta["type"] == "multi":
            valores = _parametro_lista(params, f"f_{clave}")
            if not valores:
                continue
            opciones = _opciones_filtro(area_key, clave, cef_map, cache_opciones)
            etiquetas = {opcion["value"]: opcion["label"] for opcion in opciones}
            if any(valor not in etiquetas for valor in valores):
                raise MetricasValidationError(
                    f"Uno o más valores del filtro '{meta['label']}' no están permitidos."
                )
            filtros[clave] = {
                "type": "multi",
                "values": tuple(valores),
                "labels": tuple(etiquetas[valor] for valor in valores),
            }
            continue

        desde_txt = str(_parametro(params, f"f_{clave}_desde", "") or "").strip()
        hasta_txt = str(_parametro(params, f"f_{clave}_hasta", "") or "").strip()
        if not desde_txt and not hasta_txt:
            continue
        if meta["type"] == "date_range":
            desde = _valor_fecha(desde_txt, f"{meta['label']} desde") if desde_txt else None
            hasta = _valor_fecha(hasta_txt, f"{meta['label']} hasta") if hasta_txt else None
        else:
            desde = (
                _valor_entero(
                    desde_txt,
                    f"{meta['label']} desde",
                    meta.get("min"),
                    meta.get("max"),
                )
                if desde_txt
                else None
            )
            hasta = (
                _valor_entero(
                    hasta_txt,
                    f"{meta['label']} hasta",
                    meta.get("min"),
                    meta.get("max"),
                )
                if hasta_txt
                else None
            )
        if desde is not None and hasta is not None and desde > hasta:
            raise MetricasValidationError(
                f"En '{meta['label']}', el valor desde no puede superar al valor hasta."
            )
        filtros[clave] = {"type": meta["type"], "desde": desde, "hasta": hasta}

    return ConsultaResuelta(
        area=area_key,
        indicador=indicador_key,
        ciclos=ciclos_ordenados,
        cefs=cefs,
        todos_cef=todos_cef,
        agrupar=agrupar,
        comparar=comparar,
        grafico=grafico,
        filtros=filtros,
    )


def _cefs_filtrados_por_territorio(consulta, cef_map):
    cefs = set(consulta.cefs)
    for clave in CLAVES_TERRITORIO:
        filtro = consulta.filtros.get(clave)
        if not filtro:
            continue
        permitidos = set(filtro["values"])
        cefs &= {
            cueanexo
            for cueanexo, datos in cef_map.items()
            if datos.get(clave, SIN_INFORMACION) in permitidos
        }
    return tuple(cueanexo for cueanexo in consulta.cefs if cueanexo in cefs)


def _aplicar_filtros(qs, consulta, fuente):
    indicador = AREAS[consulta.area]["indicators"][consulta.indicador]
    for clave, filtro in consulta.filtros.items():
        if clave in CLAVES_TERRITORIO:
            continue
        descriptor = indicador["filter_overrides"].get(
            clave,
            fuente["filtros"].get(clave),
        )
        if descriptor is None:
            raise MetricasValidationError(
                f"El filtro '{clave}' no está disponible en la fuente del indicador."
            )

        if filtro["type"] == "multi":
            valores = filtro["values"]
            if isinstance(descriptor, str):
                qs = qs.filter(**{f"{descriptor}__in": valores})
                continue

            tipo = descriptor[0]
            if tipo == "codigo_ra_efectivo":
                prefijo = descriptor[1]
                override = f"{prefijo}codigo_ra_override_id"
                normal = f"{prefijo}actividad__codigo_ra_id"
                qs = qs.filter(
                    Q(**{f"{override}__in": valores})
                    | Q(**{f"{override}__isnull": True, f"{normal}__in": valores})
                )
            elif tipo == "dia_grupo":
                prefijo = descriptor[1]
                grupo_pk = f"{prefijo}pk"
                dias = CefGrupoDiaFuncionamiento.objects.filter(
                    grupo_id=OuterRef(grupo_pk),
                    dia_semana_id__in=valores,
                )
                qs = qs.annotate(_metrica_coincide_dia=Exists(dias)).filter(
                    _metrica_coincide_dia=True
                )
            elif tipo == "mes":
                qs = qs.filter(
                    **{f"{descriptor[1]}__month__in": valores}
                )
            else:
                raise MetricasValidationError(f"El filtro '{clave}' no es aplicable.")
            continue

        tipo = descriptor[0]
        if tipo == "edad":
            campo = "_metrica_edad"
        elif tipo in {"fecha", "numero"}:
            campo = descriptor[1]
        else:
            raise MetricasValidationError(f"El filtro '{clave}' no es aplicable.")
        if filtro.get("desde") is not None:
            qs = qs.filter(**{f"{campo}__gte": filtro["desde"]})
        if filtro.get("hasta") is not None:
            qs = qs.filter(**{f"{campo}__lte": filtro["hasta"]})
    return qs


def _anotar_alumnos_activos(qs):
    por_grupo = (
        CefInscripcion.objects.filter(
            grupo_id=OuterRef("pk"),
            estado=CefInscripcion.Estado.ACTIVO,
        )
        .order_by()
        .values("grupo_id")
        .annotate(total=Count("alumno_id", distinct=True))
        .values("total")[:1]
    )
    return qs.annotate(
        _metrica_alumnos_activos=Coalesce(
            Subquery(por_grupo, output_field=IntegerField()),
            Value(0),
            output_field=IntegerField(),
        )
    )


def _preparar_queryset(consulta, indicador, cef_map):
    fuente = FUENTES[indicador["source"]]
    cefs_efectivos = _cefs_filtrados_por_territorio(consulta, cef_map)
    qs = fuente["model"].objects.all().filter(
        **{
            f"{fuente['ciclo']}__in": consulta.ciclos,
            f"{fuente['cef']}__in": cefs_efectivos,
        }
    )
    if fuente.get("base_q") is not None:
        qs = qs.filter(fuente["base_q"])
    if indicador.get("fixed_q") is not None:
        qs = qs.filter(indicador["fixed_q"])

    usa_edad = "edad" in consulta.filtros or consulta.agrupar == "edad" or consulta.comparar == "edad"
    if usa_edad:
        descriptor_edad = fuente["filtros"].get("edad")
        if not descriptor_edad:
            raise MetricasValidationError("La edad no está disponible para este indicador.")
        qs = qs.annotate(
            _metrica_edad=_edad_historica_expresion(
                descriptor_edad[1], descriptor_edad[2]
            )
        )

    if indicador["metric"]["kind"] in {
        "active_students",
        "average_active_students",
        "occupancy",
    }:
        qs = _anotar_alumnos_activos(qs)

    return _aplicar_filtros(qs, consulta, fuente), fuente


def _division_segura(numerador, denominador):
    numerador = float(numerador or 0)
    denominador = float(denominador or 0)
    if denominador <= 0:
        return None
    return numerador / denominador


def _calcular_total(qs, indicador):
    metrica = indicador["metric"]
    kind = metrica["kind"]
    if kind in {"count", "distinct"}:
        distinct = kind == "distinct" or bool(metrica.get("distinct"))
        value = qs.aggregate(
            value=Count(metrica.get("field", "pk"), distinct=distinct)
        )["value"]
        return {
            "value": int(value or 0),
            "numerator": None,
            "denominator": None,
            "empty": not value,
        }
    if kind == "sum":
        datos = qs.aggregate(
            value=Sum(metrica["field"]),
            rows=Count(metrica["field"]),
        )
        value = datos["value"] or 0
        return {
            "value": _valor_json(value),
            "numerator": None,
            "denominator": None,
            "empty": not datos["rows"],
        }
    if kind == "active_students":
        datos = qs.aggregate(
            value=Sum("_metrica_alumnos_activos"),
            rows=Count("pk"),
        )
        value = datos["value"] or 0
        return {
            "value": int(value),
            "numerator": None,
            "denominator": None,
            "empty": not datos["rows"],
        }
    if kind == "average_active_students":
        datos = qs.aggregate(
            numerator=Sum("_metrica_alumnos_activos"),
            denominator=Count("pk"),
        )
        numerator = int(datos["numerator"] or 0)
        denominator = int(datos["denominator"] or 0)
        return {
            "value": _division_segura(numerator, denominator),
            "numerator": numerator,
            "denominator": denominator,
            "empty": denominator == 0,
        }
    if kind == "occupancy":
        datos = qs.aggregate(
            numerator=Sum("_metrica_alumnos_activos"),
            denominator=Sum("cupo_maximo"),
        )
        numerator = int(datos["numerator"] or 0)
        denominator = int(datos["denominator"] or 0)
        return {
            "value": _division_segura(numerator * 100, denominator),
            "numerator": numerator,
            "denominator": denominator,
            "empty": denominator == 0,
        }
    if kind == "state_ratio":
        datos = qs.aggregate(
            numerator=Count("pk", filter=Q(estado=metrica["state"])),
            denominator=Count("pk"),
        )
        numerator = int(datos["numerator"] or 0)
        denominator = int(datos["denominator"] or 0)
        return {
            "value": _division_segura(numerator * 100, denominator),
            "numerator": numerator,
            "denominator": denominator,
            "empty": denominator == 0,
        }
    if kind == "distribution_ratio":
        denominator = int(qs.aggregate(total=Count("pk"))["total"] or 0)
        return {
            "value": 100.0 if denominator else None,
            "numerator": denominator,
            "denominator": denominator,
            "empty": denominator == 0,
        }
    raise MetricasValidationError("El cálculo configurado para el indicador no existe.")


def _anotaciones_metrica(indicador):
    metrica = indicador["metric"]
    kind = metrica["kind"]
    if kind in {"count", "distinct"}:
        distinct = kind == "distinct" or bool(metrica.get("distinct"))
        return {"_metrica_valor": Count(metrica.get("field", "pk"), distinct=distinct)}
    if kind == "sum":
        return {"_metrica_valor": Sum(metrica["field"])}
    if kind == "active_students":
        return {"_metrica_valor": Sum("_metrica_alumnos_activos")}
    if kind == "average_active_students":
        return {
            "_metrica_numerador": Sum("_metrica_alumnos_activos"),
            "_metrica_denominador": Count("pk"),
        }
    if kind == "occupancy":
        return {
            "_metrica_numerador": Sum("_metrica_alumnos_activos"),
            "_metrica_denominador": Sum("cupo_maximo"),
        }
    if kind == "state_ratio":
        return {
            "_metrica_numerador": Count(
                "pk", filter=Q(estado=metrica["state"])
            ),
            "_metrica_denominador": Count("pk"),
        }
    if kind == "distribution_ratio":
        return {"_metrica_numerador": Count("pk")}
    raise MetricasValidationError("El cálculo configurado para el indicador no existe.")


def _opciones_sexo_mapa(cache):
    if "sexo" not in cache:
        cache["sexo"] = {
            opcion["value"]: opcion["label"] for opcion in _opciones_sexo()
        }
    return cache["sexo"]


def _etiqueta_dimension(clave, valor, etiqueta, fuente_key, cef_map, cache):
    if clave in CLAVES_TERRITORIO:
        return _texto_limpio(valor) or SIN_INFORMACION
    if clave == "cef":
        return cef_map.get(str(valor), {}).get("label", str(valor or SIN_INFORMACION))
    if clave == "mes":
        try:
            return MESES.get(int(valor), SIN_INFORMACION)
        except (TypeError, ValueError):
            return SIN_INFORMACION
    if clave == "edad":
        if valor in (None, "", "__sin_informacion__"):
            return SIN_INFORMACION
        return str(valor)
    if clave == "sexo":
        return _opciones_sexo_mapa(cache).get(str(valor), SIN_INFORMACION)
    if clave == "rol":
        return dict(CefDocenteGrupo.Rol.choices).get(valor, SIN_INFORMACION)
    if clave == "estado":
        if fuente_key == "asistencia":
            choices = dict(CefAsistencia.Estado.choices)
        elif fuente_key == "grupos":
            choices = dict(CefGrupo.Estado.choices)
        elif fuente_key in {"docentes_banco", "asignaciones"}:
            choices = dict(CefDocenteGrupo.Estado.choices)
        else:
            choices = dict(CefInscripcion.Estado.choices)
        return choices.get(valor, _texto_limpio(etiqueta) or _texto_limpio(valor) or SIN_INFORMACION)
    return _texto_limpio(_valor_json(etiqueta)) or _texto_limpio(_valor_json(valor)) or SIN_INFORMACION


def _expresion_dimension_territorial(clave, campo_cef, cueanexos, cef_map):
    """Traduce el mapa Padrón a un CASE SQL para agregar exactamente en base.

    La carga del Padrón sigue siendo una sola consulta. Expresar el mapa como CASE
    evita reagrupar sumas por CEF en Python, algo que duplicaría personas distintas
    cuando una misma persona participa en dos CEF del mismo territorio.
    """

    casos = [
        When(
            **{
                campo_cef: cueanexo,
                "then": Value(
                    cef_map.get(cueanexo, {}).get(clave, SIN_INFORMACION)
                    or SIN_INFORMACION
                ),
            }
        )
        for cueanexo in cueanexos
        if cueanexo in cef_map
    ]
    if not casos:
        return Value(SIN_INFORMACION, output_field=CharField())
    return Case(
        *casos,
        default=Value(SIN_INFORMACION),
        output_field=CharField(),
    )


def _orden_dimension(clave, key, label, fuente):
    if label == SIN_INFORMACION:
        return (1, 0, "")
    spec = fuente["dimensiones"].get(clave, {})
    tipo = spec.get("sort", "texto")
    if clave in {"ciclo", "mes"} or tipo == "numero":
        try:
            return (0, float(key), "")
        except (TypeError, ValueError):
            return (1, 0, str(label).casefold())
    if clave == "edad" or tipo == "edad":
        try:
            return (0, int(key), "")
        except (TypeError, ValueError):
            return (1, 0, str(label).casefold())
    return (0, 0, str(label).casefold())


def _filtrar_dimension_dia(qs, consulta, fuente):
    filtro = consulta.filtros.get("dia")
    if not filtro or "dia" not in {consulta.agrupar, consulta.comparar}:
        return qs
    descriptor = fuente["filtros"].get("dia")
    if not descriptor or descriptor[0] != "dia_grupo":
        return qs
    prefijo = descriptor[1]
    return qs.filter(
        **{
            f"{prefijo}dias_funcionamiento__dia_semana_id__in": filtro["values"]
        }
    )


def _filas_agrupadas(qs, consulta, indicador, fuente, cef_map, total):
    if not consulta.agrupar:
        return [
            {
                "group_key": "total",
                "group_label": "Total",
                "comparison_key": None,
                "comparison_label": None,
                "value": total["value"],
                "numerator": total["numerator"],
                "denominator": total["denominator"],
            }
        ]

    anotaciones_dimension = {}
    for prefijo, clave in (
        ("_metrica_grupo", consulta.agrupar),
        ("_metrica_comparacion", consulta.comparar),
    ):
        if not clave:
            continue
        if clave in CLAVES_TERRITORIO:
            expresion = _expresion_dimension_territorial(
                clave,
                fuente["cef"],
                consulta.cefs,
                cef_map,
            )
            anotaciones_dimension[f"{prefijo}_key"] = expresion
            anotaciones_dimension[f"{prefijo}_label"] = expresion.copy()
            continue
        spec = fuente["dimensiones"].get(clave)
        if spec is None:
            raise MetricasValidationError(
                f"La dimensión '{clave}' no está disponible en la fuente del indicador."
            )
        anotaciones_dimension[f"{prefijo}_key"] = spec["key"]()
        anotaciones_dimension[f"{prefijo}_label"] = spec["label"]()

    qs_grupos = _filtrar_dimension_dia(qs, consulta, fuente)
    consulta_orm = (
        qs_grupos.annotate(**anotaciones_dimension)
        .values(*anotaciones_dimension.keys())
        .annotate(**_anotaciones_metrica(indicador))
        .order_by()
    )

    metrica = indicador["metric"]
    kind = metrica["kind"]
    cache_etiquetas = {}
    acumulados = {}
    for fila in consulta_orm:
        group_key = _valor_json(fila.get("_metrica_grupo_key"))
        group_label = _etiqueta_dimension(
            consulta.agrupar,
            group_key,
            fila.get("_metrica_grupo_label"),
            indicador["source"],
            cef_map,
            cache_etiquetas,
        )

        if consulta.comparar:
            comparison_key = _valor_json(fila.get("_metrica_comparacion_key"))
            comparison_label = _etiqueta_dimension(
                consulta.comparar,
                comparison_key,
                fila.get("_metrica_comparacion_label"),
                indicador["source"],
                cef_map,
                cache_etiquetas,
            )
        else:
            comparison_key = None
            comparison_label = None

        identidad = (
            str(group_key),
            group_label,
            str(comparison_key) if comparison_key is not None else None,
            comparison_label,
        )
        acumulado = acumulados.setdefault(
            identidad,
            {
                "group_key": group_key,
                "group_label": group_label,
                "comparison_key": comparison_key,
                "comparison_label": comparison_label,
                "value": 0,
                "numerator": 0,
                "denominator": 0,
            },
        )
        if kind in {
            "average_active_students",
            "occupancy",
            "state_ratio",
            "distribution_ratio",
        }:
            acumulado["numerator"] += int(fila.get("_metrica_numerador") or 0)
            if kind != "distribution_ratio":
                acumulado["denominator"] += int(fila.get("_metrica_denominador") or 0)
        else:
            acumulado["value"] += _valor_json(fila.get("_metrica_valor") or 0)

    filas = []
    for acumulado in acumulados.values():
        if kind == "occupancy":
            acumulado["value"] = _division_segura(
                acumulado["numerator"] * 100, acumulado["denominator"]
            )
        elif kind in {"average_active_students", "state_ratio"}:
            factor = 100 if kind == "state_ratio" else 1
            acumulado["value"] = _division_segura(
                acumulado["numerator"] * factor, acumulado["denominator"]
            )
        elif kind == "distribution_ratio":
            acumulado["denominator"] = int(total["denominator"] or 0)
            acumulado["value"] = _division_segura(
                acumulado["numerator"] * 100, acumulado["denominator"]
            )
        else:
            acumulado["numerator"] = None
            acumulado["denominator"] = None
        filas.append(acumulado)

    filas.sort(
        key=lambda fila: (
            _orden_dimension(
                consulta.agrupar,
                fila["group_key"],
                fila["group_label"],
                fuente,
            ),
            _orden_dimension(
                consulta.comparar,
                fila["comparison_key"],
                fila["comparison_label"] or "",
                fuente,
            )
            if consulta.comparar
            else (0, 0, ""),
        )
    )
    return filas


def _formatear_numero(valor, unidad):
    if valor is None:
        return "No calculable"
    valor = float(valor or 0)
    if unidad == "%" or "por grupo" in unidad:
        texto = f"{valor:.1f}"
        entero, decimal = texto.split(".")
        entero = f"{int(entero):,}".replace(",", ".")
        return f"{entero},{decimal}"
    if valor.is_integer():
        return f"{int(valor):,}".replace(",", ".")
    texto = f"{valor:.2f}".rstrip("0").rstrip(".")
    entero, _, decimal = texto.partition(".")
    entero = f"{int(entero):,}".replace(",", ".")
    return f"{entero},{decimal}" if decimal else entero


def _tabla_resultado(filas, consulta, indicador):
    columnas = []
    if consulta.agrupar:
        columnas.append(
            {"key": "grupo", "label": DIMENSIONES_META[consulta.agrupar]}
        )
    if consulta.comparar:
        columnas.append(
            {"key": "comparacion", "label": DIMENSIONES_META[consulta.comparar]}
        )
    columnas.append({"key": "valor", "label": indicador["label"]})
    if indicador["metric"]["kind"] in {
        "average_active_students",
        "occupancy",
        "state_ratio",
        "distribution_ratio",
    }:
        columnas.extend(
            (
                {"key": "numerador", "label": "Numerador"},
                {"key": "denominador", "label": "Denominador"},
            )
        )

    rows = []
    for fila in filas:
        valor_json = _valor_json(fila["value"])
        valor_formateado = _formatear_numero(fila["value"], indicador["unit"])
        if indicador["unit"] == "%" and fila["value"] is not None:
            valor_formateado = f"{valor_formateado} %"
        row = {
            "valor": {
                "value": valor_json,
                "formatted": valor_formateado,
            },
            "valor_formateado": valor_formateado,
        }
        if consulta.agrupar:
            row["grupo_key"] = _valor_json(fila["group_key"])
            row["grupo"] = fila["group_label"]
        if consulta.comparar:
            row["comparacion_key"] = _valor_json(fila["comparison_key"])
            row["comparacion"] = fila["comparison_label"]
        if fila["numerator"] is not None:
            row["numerador"] = _valor_json(fila["numerator"])
            row["denominador"] = _valor_json(fila["denominator"])
        rows.append(row)
    return {"columns": columnas, "rows": rows}


def _grafico_resultado(filas, consulta, indicador):
    max_categorias = 160
    max_series = 8
    max_puntos = 1600
    disponibles = list(
        _tipos_grafico_compatibles(
            consulta.agrupar,
            consulta.comparar,
            indicador,
        )
    )
    if not consulta.agrupar:
        return {
            "type": "kpi",
            "available_types": disponibles,
            "labels": [],
            "series": [],
        }

    labels = []
    claves_grupo = []
    claves_grupo_vistas = set()
    for fila in filas:
        identidad = (str(fila["group_key"]), fila["group_label"])
        if identidad in claves_grupo_vistas:
            continue
        claves_grupo_vistas.add(identidad)
        claves_grupo.append(identidad)
        labels.append(fila["group_label"])

    grafico_solicitado = consulta.grafico
    if len(labels) > 8 and "doughnut" in disponibles:
        disponibles.remove("doughnut")
    if grafico_solicitado == "doughnut" and "doughnut" not in disponibles:
        grafico_solicitado = "auto"

    if consulta.comparar:
        comparaciones = []
        comparaciones_vistas = set()
        for fila in filas:
            identidad = (str(fila["comparison_key"]), fila["comparison_label"])
            if identidad in comparaciones_vistas:
                continue
            comparaciones_vistas.add(identidad)
            comparaciones.append(identidad)
        cantidad_puntos = len(claves_grupo) * len(comparaciones)
        if (
            len(claves_grupo) > max_categorias
            or len(comparaciones) > max_series
            or cantidad_puntos > max_puntos
        ):
            return {
                "type": "grouped_bar",
                "available_types": [],
                "labels": [],
                "series": [],
                "omitted": True,
                "message": (
                    "El gráfico se omite porque la combinación genera demasiadas "
                    "categorías o series. Refiná los filtros; la tabla y el Excel "
                    "conservan el resultado completo."
                ),
            }
        mapa = {
            (
                str(fila["group_key"]),
                fila["group_label"],
                str(fila["comparison_key"]),
                fila["comparison_label"],
            ): _valor_json(fila["value"])
            for fila in filas
        }
        series = [
            {
                "name": comparacion_label,
                "key": comparacion_key,
                "data": [
                    mapa.get(
                        (
                            grupo_key,
                            grupo_label,
                            comparacion_key,
                            comparacion_label,
                        ),
                        (
                            None
                            if indicador["metric"]["kind"] in {
                                "average_active_students",
                                "occupancy",
                                "state_ratio",
                            }
                            else 0
                        ),
                    )
                    for grupo_key, grupo_label in claves_grupo
                ],
            }
            for comparacion_key, comparacion_label in comparaciones
        ]
    else:
        if len(claves_grupo) > max_categorias:
            return {
                "type": "bar",
                "available_types": [],
                "labels": [],
                "series": [],
                "omitted": True,
                "message": (
                    "El gráfico se omite porque el resultado contiene demasiadas "
                    "categorías. Refiná los filtros; la tabla y el Excel conservan "
                    "el resultado completo."
                ),
            }
        mapa = {
            (str(fila["group_key"]), fila["group_label"]): _valor_json(fila["value"])
            for fila in filas
        }
        series = [
            {
                "name": indicador["label"],
                "key": consulta.indicador,
                "data": [mapa.get(clave, 0) for clave in claves_grupo],
            }
        ]

    if grafico_solicitado != "auto":
        tipo = grafico_solicitado
    elif consulta.agrupar in {"ciclo", "fecha", "mes"} and "line" in disponibles:
        tipo = "line"
    elif consulta.comparar:
        tipo = "grouped_bar"
    elif indicador["metric"]["kind"] == "distribution_ratio" and len(labels) <= 6:
        tipo = "doughnut"
    else:
        tipo = "bar"
    return {
        "type": tipo,
        "available_types": disponibles,
        "labels": labels,
        "series": series,
    }


def _filtros_publicos(consulta):
    indicador = AREAS[consulta.area]["indicators"][consulta.indicador]
    etiquetas = _etiquetas_filtros_indicador(indicador)
    resultado = []
    for clave, filtro in consulta.filtros.items():
        item = {
            "key": clave,
            "label": etiquetas.get(clave, FILTROS_META[clave]["label"]),
            "type": filtro["type"],
        }
        if filtro["type"] == "multi":
            item["values"] = list(filtro["values"])
            item["labels"] = list(filtro["labels"])
            item["summary"] = ", ".join(filtro["labels"])
        else:
            desde = _valor_json(filtro.get("desde"))
            hasta = _valor_json(filtro.get("hasta"))
            item["desde"] = desde
            item["hasta"] = hasta
            if desde is not None and hasta is not None:
                item["summary"] = f"{desde} a {hasta}"
            elif desde is not None:
                item["summary"] = f"Desde {desde}"
            else:
                item["summary"] = f"Hasta {hasta}"
        resultado.append(item)
    return resultado


def _consulta_publica(consulta, ciclos_db, cef_map, indicador):
    ciclos_por_id = {fila["pk"]: fila for fila in ciclos_db}
    ciclos = [
        {
            "value": str(ciclo_id),
            "label": str(ciclos_por_id[ciclo_id]["anio"]),
            "anio": ciclos_por_id[ciclo_id]["anio"],
            "activo": bool(ciclos_por_id[ciclo_id]["activo"]),
            "actual": bool(ciclos_por_id[ciclo_id]["actual"]),
            "cerrado": bool(ciclos_por_id[ciclo_id]["cerrado"]),
        }
        for ciclo_id in consulta.ciclos
    ]
    cefs = [cef_map[cueanexo] for cueanexo in consulta.cefs if cueanexo in cef_map]
    filtros = _filtros_publicos(consulta)
    resumen = [
        f"Ciclos: {', '.join(ciclo['label'] for ciclo in ciclos) or SIN_INFORMACION}",
        f"CEF: {TODOS_LOS_CEF if consulta.todos_cef else ', '.join(cef['label'] for cef in cefs)}",
    ]
    resumen.extend(
        f"Limitado por {filtro['label']}: {filtro['summary']}" for filtro in filtros
    )
    return {
        "area": consulta.area,
        "area_label": AREAS[consulta.area]["label"],
        "indicador": consulta.indicador,
        "indicador_label": indicador["label"],
        "ciclos": ciclos,
        "cefs": cefs,
        "todos_cef": consulta.todos_cef,
        "cef_scope_label": TODOS_LOS_CEF if consulta.todos_cef else ", ".join(
            cef["label"] for cef in cefs
        ),
        "filters": filtros,
        "filter_summary": resumen,
        "agrupar": consulta.agrupar,
        "agrupar_label": DIMENSIONES_META.get(consulta.agrupar, "Sólo total general"),
        "comparar": consulta.comparar,
        "comparar_label": DIMENSIONES_META.get(consulta.comparar, "No comparar"),
        "grafico": consulta.grafico,
    }


def _notas_resultado(consulta, indicador, total):
    notas = list(indicador["notes"])
    metrica = indicador["metric"]
    if metrica["kind"] == "distinct" and consulta.agrupar:
        notas.append(
            "El total se calcula con un COUNT DISTINCT independiente sobre todo el alcance; "
            "las categorías pueden no ser mutuamente excluyentes y su suma puede superar el total."
        )
    if len(consulta.ciclos) > 1 and metrica["kind"] == "distinct":
        notas.append(
            "En el total multi-ciclo, una misma entidad se deduplica entre los ciclos seleccionados."
        )
    if total["empty"] and metrica["kind"] in {
        "occupancy",
        "average_active_students",
        "state_ratio",
        "distribution_ratio",
    }:
        notas.append("No hay un denominador válido para calcular el indicador con estos filtros.")
    if consulta.agrupar in CLAVES_TERRITORIO or consulta.comparar in CLAVES_TERRITORIO:
        notas.append(
            "El territorio se obtuvo en bloque desde el Padrón actual y se aplicó por "
            "CUE-Anexo, sin consultas por fila. Un cambio posterior en Padrón también "
            "reclasifica los ciclos históricos."
        )
    dimensiones_usadas = {consulta.agrupar, consulta.comparar, *consulta.filtros}
    if consulta.area == "alumnos" and dimensiones_usadas & {"edad", "sexo"}:
        notas.append(
            "Fecha de nacimiento y sexo provienen del registro actual del alumno y no "
            "de un snapshot histórico; una corrección posterior puede cambiar el resultado."
        )
    if "dia" in {consulta.agrupar, consulta.comparar}:
        notas.append(
            "Un grupo puede funcionar varios días; las categorías por día no son "
            "mutuamente excluyentes y su suma puede superar el total general."
        )
    return list(dict.fromkeys(notas))


def ejecutar_consulta_metricas(params):
    """Valida un QueryDict GET y devuelve el único resultado canónico de la consulta.

    El diccionario resultante es serializable y alimenta el total, el gráfico, la tabla y la
    exportación. Este servicio no usa sesión ni ejecuta escrituras.
    """

    ciclos_db = _cargar_ciclos()
    cef_map = _cargar_cefs()
    consulta = _resolver_consulta(params, ciclos_db, cef_map)
    indicador = AREAS[consulta.area]["indicators"][consulta.indicador]
    qs, fuente = _preparar_queryset(consulta, indicador, cef_map)
    total = _calcular_total(qs, indicador)
    filas = _filas_agrupadas(qs, consulta, indicador, fuente, cef_map, total)
    tabla = _tabla_resultado(filas, consulta, indicador)
    grafico = _grafico_resultado(filas, consulta, indicador)
    total_formateado = _formatear_numero(total["value"], indicador["unit"])
    if indicador["unit"] == "%" and total["value"] is not None:
        total_formateado = f"{total_formateado} %"
    total_publico = {
        "value": _valor_json(total["value"]),
        "formatted": total_formateado,
        "label": indicador["label"],
        "unit": indicador["unit"],
    }
    if total["numerator"] is not None:
        total_publico["numerator"] = _valor_json(total["numerator"])
        total_publico["denominator"] = _valor_json(total["denominator"])
        kind = indicador["metric"]["kind"]
        if kind == "average_active_students":
            total_publico["detail"] = (
                f"{_formatear_numero(total['numerator'], '')} alumnos activos en "
                f"{_formatear_numero(total['denominator'], '')} grupos"
            )
        elif kind == "occupancy":
            total_publico["detail"] = (
                f"{_formatear_numero(total['numerator'], '')} inscripciones activas "
                f"sobre {_formatear_numero(total['denominator'], '')} vacantes informadas"
            )
        elif kind == "state_ratio":
            total_publico["detail"] = (
                f"{_formatear_numero(total['numerator'], '')} registros del estado "
                f"sobre {_formatear_numero(total['denominator'], '')} registros incluidos"
            )
        elif kind == "distribution_ratio":
            total_publico["detail"] = (
                f"{_formatear_numero(total['numerator'], '')} relevamientos sobre "
                f"{_formatear_numero(total['denominator'], '')} incluidos"
            )

    return {
        "ok": True,
        "query": _consulta_publica(consulta, ciclos_db, cef_map, indicador),
        "total": total_publico,
        "chart": grafico,
        "table": tabla,
        "definition": indicador["definition"],
        "notes": _notas_resultado(consulta, indicador, total),
        "empty": bool(total["empty"]),
        "empty_message": (
            "No hay datos para los filtros seleccionados."
            if total["empty"]
            else ""
        ),
    }
