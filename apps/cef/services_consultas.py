"""Listados CEF y estadísticas predefinidas; comparten alcance y exportación."""

import re
from collections import defaultdict
from dataclasses import replace
from datetime import datetime
from unicodedata import combining, normalize

from django.core.paginator import Paginator
from django.db.models import Count, DateField, Exists, OuterRef, Prefetch, Q, Sum, Value
from django.http import QueryDict
from django.utils import timezone

from . import services_metricas as motor
from .models import CefDocenteGrupo, CefGrupo


GRUPO_FILTROS = ("actividad", "eje", "nivel", "rango_etario", "turno", "grupo", "dia")
TERRITORIO = motor.FILTROS_TERRITORIO


def _columnas(*campos):
    return [{"key": key, "label": label, "default": visible, "type": tipo}
            for key, label, visible, tipo in campos]


CONTEXTO_COLUMNAS = (
    ("cef", "CEF", True, "text"), ("ciclo", "Ciclo", True, "text"),
)
GRUPO_COLUMNAS = (
    ("grupo", "Grupo", True, "text"), ("actividad", "Actividad", True, "text"),
    ("turno", "Turno", True, "text"), ("nivel", "Nivel", False, "text"),
    ("rango_etario", "Rango etario del grupo", False, "text"),
    ("eje", "Eje", False, "text"),
    ("dias", "Días", False, "text"), ("horario", "Horario", False, "text"),
    ("estado_grupo", "Estado del grupo", False, "text"),
)


def _columnas_persona(nombre, alumno):
    campos = [
        ("persona", nombre, True, "text"), ("documento", "Documento", True, "text"),
        ("cuil", "CUIL", False, "text"), *CONTEXTO_COLUMNAS,
        ("grupos", "Grupos", True, "relations"),
        ("actividad", "Actividades", False, "text"), ("turno", "Turnos", False, "text"),
        ("estado_banco", "Estado en el CEF", False, "text"),
        ("estado_relacion", "Estado de inscripción" if alumno else "Estado de asignación", False, "text"),
    ]
    campos.extend((
        ("sexo", "Sexo", False, "text"),
        ("fecha_nacimiento", "Fecha de nacimiento", False, "text"),
        ("edad", "Edad actual", False, "number"),
    ) if alumno else (("rol", "Roles", False, "text"),))
    return _columnas(*campos)


ENTIDADES = {
    "alumnos": {
        "label": "Alumnos", "icon": "fa-solid fa-user-group", "area": "alumnos",
        "indicator": "alumnos_banco_unicos", "source": "alumnos_banco", "unit": "alumnos",
        "search": "Nombre, apellido, documento o CUIL",
        "filters": (*GRUPO_FILTROS, "estado_banco", "estado_inscripcion", "estado_grupo",
                    "sexo", "edad", "fecha_alta", "fecha_inscripcion", *TERRITORIO),
        "columns": _columnas_persona("Alumno", True),
    },
    "profesores": {
        "label": "Profesores", "icon": "fa-solid fa-person-chalkboard", "area": "profesores",
        "indicator": "profesores_banco_unicos", "source": "docentes_banco", "unit": "profesores",
        "search": "Nombre, apellido, documento o CUIL",
        "filters": (*GRUPO_FILTROS, "rol", "estado_banco", "estado_asignacion", "estado_grupo",
                    "fecha_alta", "fecha_asignacion", *TERRITORIO),
        "columns": _columnas_persona("Profesor", False),
    },
    "grupos": {
        "label": "Grupos", "icon": "fa-solid fa-people-group", "area": "grupos",
        "indicator": "grupos_total", "source": "grupos", "unit": "grupos",
        "search": "Nombre del grupo, actividad o CEF",
        "filters": (*GRUPO_FILTROS, "estado_grupo", "cupo", *TERRITORIO),
        "columns": _columnas(*CONTEXTO_COLUMNAS, *GRUPO_COLUMNAS,
            ("cupo", "Cupo máximo", True, "number"),
            ("alumnos", "Alumnos con inscripción activa", True, "number"),
            ("profesores", "Profesores asignados", False, "text"),
            ("observaciones", "Observaciones", False, "text")),
    },
    "inventario": {
        "label": "Inventario", "icon": "fa-solid fa-boxes-stacked", "area": "inventario",
        "indicator": "unidades", "source": "inventario", "unit": "unidades",
        "search": "Material, estado o CEF",
        "filters": ("material", "estado_material", *TERRITORIO),
        "columns": _columnas(
            ("material", "Material", True, "text"), ("estado_material", "Estado del material", True, "text"),
            ("cantidad", "Cantidad", True, "number"), *CONTEXTO_COLUMNAS,
            ("observaciones", "Observaciones", False, "text")),
    },
    "asistencia": {
        "label": "Asistencia", "icon": "fa-solid fa-clipboard-user", "area": "asistencia",
        "indicator": "registros", "source": "asistencia", "unit": "registros de asistencia",
        "search": "Alumno, documento, actividad o CEF",
        "filters": (*GRUPO_FILTROS, "estado_asistencia", "fecha", "mes", *TERRITORIO),
        "columns": _columnas(
            ("persona", "Alumno", True, "text"), ("documento", "Documento", False, "text"),
            ("fecha", "Fecha", True, "text"), ("estado_asistencia", "Estado de asistencia", True, "text"),
            *CONTEXTO_COLUMNAS, *GRUPO_COLUMNAS),
    },
    "datos": {
        "label": "Datos adicionales", "icon": "fa-solid fa-list-check", "area": "relevamiento",
        "indicator": "relevamientos", "source": "relevamiento", "unit": "registros de datos adicionales",
        "search": "CUE-Anexo o nombre del establecimiento",
        "filters": ("beneficio", "financiamiento", "prestacion", "espacio_comedor", "orientacion", *TERRITORIO),
        "columns": _columnas(*CONTEXTO_COLUMNAS,
            ("cueanexo", "CUE-Anexo", False, "text"),
            ("beneficio", "Beneficio alimentario", True, "text"),
            ("prestacion", "Tipo de prestación", True, "text"),
            ("financiamiento", "Financiamiento", False, "text"),
            ("espacio_comedor", "Espacio comedor", True, "text"),
            ("orientacion", "Orientación", False, "text"),
            ("observaciones", "Observaciones", False, "text")),
    },
}

BUSQUEDA_CAMPOS = {
    "alumnos": {"persona": ("apellidos", "nombres"), "documento": ("nro_doc",), "cuil": ("cuil",), "cef": ()},
    "profesores": {"persona": ("docente_nombre_snapshot",), "documento": ("docente_dni_snapshot",), "cuil": ("docente_cuil",), "cef": ()},
    "grupos": {"grupo": ("nombre",), "actividad": ("actividad_nombre_snapshot", "actividad__nombre"), "cef": ()},
    "asistencia": {
        "persona": ("inscripcion__alumno__apellidos", "inscripcion__alumno__nombres"),
        "documento": ("inscripcion__alumno__nro_doc",), "cuil": ("inscripcion__alumno__cuil",),
        "grupo": ("jornada__grupo__nombre",),
        "actividad": ("jornada__grupo__actividad_nombre_snapshot", "jornada__grupo__actividad__nombre"),
        "turno": ("jornada__grupo__turno_nombre_snapshot", "jornada__grupo__turno__nombre"),
        "nivel": ("jornada__grupo__nivel_nombre_snapshot", "jornada__grupo__nivel__nombre"),
        "rango_etario": ("jornada__grupo__rango_etario_nombre_snapshot", "jornada__grupo__rango_etario__nombre"),
        "eje": ("jornada__grupo__eje_nombre_snapshot", "jornada__grupo__actividad__eje__nombre"),
        "dias": ("jornada__grupo__dias_funcionamiento__dia_semana__nombre",),
        "estado_grupo": ("jornada__grupo__estado",), "estado_asistencia": ("estado",), "cef": (),
    },
    "inventario": {"material": ("inventario_material__material_nombre_snapshot", "inventario_material__material__nombre"),
        "estado_material": ("estado__nombre", "estado_descripcion"), "cef": ()},
    "datos": {"cueanexo": ("cueanexo",), "cef": ()},
}
BUSQUEDA_ETIQUETAS = {"persona": "Alumno", "documento": "Documento", "cuil": "CUIL",
    "grupo": "Grupo", "actividad": "Actividad", "cef": "CEF", "material": "Material",
    "estado_material": "Estado", "cueanexo": "CUE-Anexo"}

BUSQUEDA_ASISTENCIA_TODOS = (
    "inscripcion__alumno__apellidos", "inscripcion__alumno__nombres",
    "inscripcion__alumno__nro_doc", "inscripcion__alumno__cuil",
    "jornada__grupo__nombre",
    "jornada__grupo__actividad_nombre_snapshot", "jornada__grupo__actividad__nombre",
    "jornada__grupo__eje_nombre_snapshot", "jornada__grupo__actividad__eje__nombre",
    "jornada__grupo__nivel_nombre_snapshot", "jornada__grupo__nivel__nombre",
    "jornada__grupo__rango_etario_nombre_snapshot", "jornada__grupo__rango_etario__nombre",
    "jornada__grupo__turno_nombre_snapshot", "jornada__grupo__turno__nombre",
    "jornada__grupo__dias_funcionamiento__dia_semana__nombre",
    "jornada__grupo__estado", "estado",
)
BUSQUEDA_ASISTENCIA_ESPECIAL = {"ciclo", "fecha", "horario"}

PREGUNTAS = {
    "alumnos_cef": ("alumnos", "¿Cuántos alumnos inscriptos tiene cada CEF?", "alumnos_inscriptos_activos", "cef", "", "bar"),
    "alumnos_actividad": ("alumnos", "¿En qué actividades participan más alumnos?", "alumnos_inscriptos_activos", "actividad", "", "bar"),
    "alumnos_ciclos": ("alumnos", "¿Cómo cambió la cantidad de alumnos entre ciclos?", "alumnos_inscriptos_activos", "ciclo", "", "line"),
    "profesores_rol": ("profesores", "¿Cómo se distribuyen los profesores asignados por rol?", "profesores_asignados_activos", "rol", "", "bar"),
    "grupos_ocupacion": ("grupos", "¿Qué porcentaje del cupo está ocupado en los grupos activos?", "ocupacion", "grupo", "", "bar"),
    "asistencia_mes": ("asistencia", "¿Cómo fue el presentismo mes a mes?", "porcentaje_presentes", "mes", "ciclo", "line"),
    "inventario_material": ("inventario", "¿Cuántas unidades hay de cada material?", "unidades", "material", "", "bar"),
    "datos_ciclo": ("datos", "¿Cuántos CEF tienen datos adicionales cargados por ciclo?", "cef_relevados", "ciclo", "", "bar"),
}
ESTADOS = {
    "estado_banco": "Estado en el CEF", "estado_inscripcion": "Estado de inscripción",
    "estado_asignacion": "Estado de asignación", "estado_grupo": "Estado del grupo",
    "estado_asistencia": "Estado de asistencia", "estado_material": "Estado del material",
}
FECHAS = {
    "fecha_alta": "Fecha de alta en el CEF", "fecha_inscripcion": "Fecha de inscripción",
    "fecha_asignacion": "Fecha de asignación",
}


def _campos_busqueda(entidad):
    campos = {columna["key"]: columna["label"] for columna in ENTIDADES[entidad]["columns"]}
    for campo in BUSQUEDA_CAMPOS[entidad]:
        if campo not in campos:
            campos[campo] = BUSQUEDA_ETIQUETAS.get(campo, campo.replace("_", " ").capitalize())
    return campos


def _normalizar_busqueda(valor):
    return "".join(c for c in normalize("NFD", str(valor).casefold()) if not combining(c))


def _texto_busqueda_fila(valor):
    if valor is None or valor == "":
        return motor.SIN_INFORMACION
    if isinstance(valor, (int, float)):
        return str(valor) + " " + motor._formatear_numero(valor, "")
    return str(valor)


def _buscar_filas(filas, texto, campo):
    """Busca una columna calculada sobre el resultado completo, antes de paginar."""
    terminos = _normalizar_busqueda(texto).replace(",", " ").split()

    def coincide(fila):
        texto_valor = _normalizar_busqueda(_texto_busqueda_fila(fila.get(campo)))
        return all(termino in texto_valor for termino in terminos)

    return [fila for fila in filas if coincide(fila)]


def _buscar_filas_todos(filas, texto, campos):
    """Busca sobre la fila pública completa para que "Todos" represente lo visible."""
    terminos = _normalizar_busqueda(texto).replace(",", " ").split()

    def coincide(fila):
        texto_valor = _normalizar_busqueda(" ".join(
            _texto_busqueda_fila(fila.get(campo)) for campo in campos
        ))
        return all(termino in texto_valor for termino in terminos)

    return [fila for fila in filas if coincide(fila)]


def _numero_grupo_busqueda(texto):
    coincidencia = re.search(
        r"\bgrupo\s+(?:n(?:ro)?\.?\s*)?(\d+)\b",
        _normalizar_busqueda(texto),
    )
    return int(coincidencia.group(1)) if coincidencia else None


def _fecha_busqueda(texto):
    for formato in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    return None


def _horas_busqueda(texto):
    horas = []
    for hora, minuto in re.findall(r"(?<!\d)(\d{1,2}):(\d{2})(?!\d)", str(texto)):
        try:
            valor = datetime.strptime(f"{hora}:{minuto}", "%H:%M").time()
        except ValueError:
            continue
        if valor not in horas:
            horas.append(valor)
    return tuple(horas)


def _cefs_busqueda(termino, cef_map):
    termino_normalizado = _normalizar_busqueda(termino)
    return [
        key for key, datos in cef_map.items()
        if termino_normalizado in _normalizar_busqueda(datos["label"])
    ]


def _busqueda_directa(entidad, campo):
    return (
        campo in BUSQUEDA_CAMPOS[entidad]
        or (entidad == "asistencia" and campo in BUSQUEDA_ASISTENCIA_ESPECIAL)
    )


def _ids_personas_todos(entidad, banco, relaciones, cef_map, texto, raices_alumno=None):
    """Reduce candidatos por ID/CUIL antes de construir las filas públicas."""
    alumno = entidad == "alumnos"
    identidad = "alumno_id" if alumno else "docente_cuil"
    encontrados = None
    sexo_map = motor._opciones_sexo_mapa({}) if alumno else {}

    for termino in texto.replace(",", " ").split():
        ids_termino = set()
        cefs = _cefs_busqueda(termino, cef_map)

        if alumno:
            campos_banco = ("estado",)
        else:
            campos_banco = (
                "docente_nombre_snapshot", "docente_dni_snapshot",
                "docente_cuil", "estado",
            )
        condicion_banco = Q()
        for campo in campos_banco:
            condicion_banco |= Q(**{campo + "__icontains": termino})
        condicion_banco |= Q(cueanexo__in=cefs)
        if termino.isdigit():
            condicion_banco |= Q(ciclo__anio=int(termino))
        ids_termino.update(
            banco.filter(condicion_banco).values_list(identidad, flat=True)
        )

        condicion_relacion = Q()
        if not alumno:
            for campo in ("docente_nombre_snapshot", "docente_dni_snapshot", "docente_cuil"):
                condicion_relacion |= Q(**{campo + "__icontains": termino})
        for campo in (
            "grupo__actividad_nombre_snapshot", "grupo__actividad__nombre",
            "grupo__turno_nombre_snapshot", "grupo__turno__nombre",
            "estado",
        ):
            condicion_relacion |= Q(**{campo + "__icontains": termino})
        if not alumno:
            condicion_relacion |= Q(rol__icontains=termino)
        condicion_relacion |= Q(grupo__cueanexo__in=cefs)
        if termino.isdigit():
            condicion_relacion |= Q(grupo__ciclo__anio=int(termino))
        ids_termino.update(
            relaciones.filter(condicion_relacion).values_list(identidad, flat=True)
        )

        if termino.isdigit():
            cantidad = int(termino)
            ids_termino.update(
                relaciones.order_by().values(identidad)
                .annotate(_consulta_grupos=Count("grupo_id", distinct=True))
                .filter(_consulta_grupos=cantidad)
                .values_list(identidad, flat=True)
            )

        if alumno and raices_alumno is not None:
            condicion_raiz = (
                Q(apellidos__icontains=termino)
                | Q(nombres__icontains=termino)
                | Q(nro_doc__icontains=termino)
                | Q(cuil__icontains=termino)
            )
            if termino.isdigit():
                condicion_raiz |= Q(_metrica_edad=int(termino))
            fecha = _fecha_busqueda(termino)
            if fecha is not None:
                condicion_raiz |= Q(fecha_nacimiento=fecha)
            termino_normalizado = _normalizar_busqueda(termino)
            sexos = [
                sexo_id for sexo_id, label in sexo_map.items()
                if termino_normalizado in _normalizar_busqueda(label)
            ]
            if sexos:
                condicion_raiz |= Q(sexo_id__in=sexos)
            ids_termino.update(
                raices_alumno.filter(condicion_raiz).values_list("pk", flat=True)
            )

        encontrados = ids_termino if encontrados is None else encontrados & ids_termino
        if not encontrados:
            break

    return encontrados or set()


def _filtro_definicion(entidad, clave, cef_map, cache, ciclos):
    area = ENTIDADES[entidad]["area"]
    if clave in FECHAS:
        label = FECHAS[clave]
        if clave == "fecha_alta":
            label = "Fecha de alta en el CEF"
        return {"key": clave, "label": label, "type": "date_range"}
    if clave in ESTADOS:
        area_estado = "asistencia" if clave == "estado_asistencia" else "inventario" if clave == "estado_material" else "grupos"
        definicion = motor._definicion_filtro(area_estado, "estado", cef_map, cache, ciclos)
        label = ESTADOS[clave]
        if clave == "estado_banco":
            label = "Estado en el CEF"
        return dict(definicion, key=clave, label=label)
    definicion = motor._definicion_filtro(area, clave, cef_map, cache, ciclos)
    if clave == "edad":
        definicion["label"] = "Edad actual"
    return definicion


def configurar_consultas(config):
    """Reutiliza catálogos y alcance ya preparados por Métricas."""
    cef_map = {item["value"]: item for item in config["cefs"]}
    ciclos = tuple(int(item["value"]) for item in config["ciclos"])
    cache = {}
    for area in config["areas"]:
        for filtro in area["filters"]:
            if "choices" in filtro:
                cache[(area["key"] if filtro["key"] == "estado" else "global", filtro["key"])] = filtro["choices"]
    config["entidades"] = [
        dict(key=key, label=meta["label"], icon=meta["icon"], columns=meta["columns"], search=meta["search"],
             search_fields=[{"value": campo, "label": label} for campo, label in _campos_busqueda(key).items()],
             filters=[_filtro_definicion(key, clave, cef_map, cache, ciclos) for clave in meta["filters"]])
        for key, meta in ENTIDADES.items()
    ]
    config["preguntas"] = []
    for key, (entidad, label, indicador, _, _, _) in PREGUNTAS.items():
        if key == "alumnos_ciclos" and len(ciclos) < 2:
            continue
        area = ENTIDADES[entidad]["area"]
        meta = motor.AREAS[area]["indicators"][indicador]
        etiquetas = motor._etiquetas_filtros_indicador(meta)
        filtros = [
            motor._definicion_filtro(area, clave, cef_map, cache, ciclos)
            for clave in meta["filters"]
            if clave != "codigo_ra"
        ]
        for filtro in filtros:
            filtro["label"] = etiquetas.get(filtro["key"], filtro["label"])
            if filtro["key"] == "estado" and entidad == "inventario":
                filtro["label"] = "Estado del material"
            if filtro["key"] == "edad":
                filtro["label"] = "Edad al inscribirse"
        config["preguntas"].append({"key": key, "entidad": entidad, "label": label, "filters": filtros})
    return config


def _resolver_listado(params, entidad, ciclos_db, cef_map):
    meta = ENTIDADES[entidad]
    buscar_campo = params.get("buscar_campo", "")
    if buscar_campo and buscar_campo not in _campos_busqueda(entidad):
        raise motor.MetricasValidationError("El campo de búsqueda no está permitido para este listado.")

    base = QueryDict(mutable=True)
    for key in ("ciclos", "cefs", "buscar", "pagina", "tamano"):
        if key in params:
            base.setlist(key, motor._parametro_lista(params, key))
    base.update({"area": meta["area"], "indicador": meta["indicator"], "agrupar": ""})
    consulta = motor._resolver_consulta(base, ciclos_db, cef_map)

    cef_map_contexto = {
        cueanexo: cef_map[cueanexo]
        for cueanexo in consulta.cefs
        if cueanexo in cef_map
    }
    cache = {}
    definiciones = [
        _filtro_definicion(
            entidad,
            clave,
            cef_map_contexto,
            cache,
            consulta.ciclos,
        )
        for clave in meta["filters"]
    ]
    permitidos = {"modo", "entidad", "ciclos", "cefs", "buscar", "buscar_campo", "pagina", "tamano", "columnas"}
    for filtro in definiciones:
        clave = "f_" + filtro["key"]
        permitidos.update((clave,) if filtro["type"] == "multi" else (clave + "_desde", clave + "_hasta"))
    if set(params.keys()) - permitidos:
        raise motor.MetricasValidationError("La consulta contiene opciones no permitidas para este listado.")

    filtros, publicos = {}, []
    for definicion in definiciones:
        key, label = definicion["key"], definicion["label"]
        if definicion["type"] == "multi":
            valores = motor._parametro_lista(params, "f_" + key)
            if not valores:
                continue
            opciones = {str(o["value"]): o["label"] for o in definicion["choices"]}
            if any(v not in opciones for v in valores):
                raise motor.MetricasValidationError(f"Hay valores no permitidos en {label}.")
            filtros[key] = {"type": "multi", "values": tuple(valores)}
            resumen = ", ".join(str(opciones[v]) for v in valores)
        else:
            limites = {}
            for lado in ("desde", "hasta"):
                valor = str(params.get(f"f_{key}_{lado}", "")).strip()
                limites[lado] = None if not valor else (
                    motor._valor_fecha(valor, label) if definicion["type"] == "date_range" else
                    motor._valor_entero(valor, label, definicion.get("min"), definicion.get("max"))
                )
            if all(v is None for v in limites.values()):
                continue
            if all(v is not None for v in limites.values()) and limites["desde"] > limites["hasta"]:
                raise motor.MetricasValidationError(f"El límite desde no puede superar al hasta en {label}.")
            filtros[key] = dict(type=definicion["type"], **limites)
            resumen = " · ".join(f"{k}: {v}" for k, v in limites.items() if v is not None)
        publicos.append({"key": key, "label": label, "summary": resumen})
    columnas = motor._parametro_lista(params, "columnas")
    if set(columnas) - {c["key"] for c in meta["columns"]}:
        raise motor.MetricasValidationError("La selección contiene columnas no permitidas.")
    return replace(consulta, filtros=filtros), publicos, columnas


def _scope(source, consulta, cef_map):
    fuente = motor.FUENTES[source]
    return fuente["model"].objects.filter(**{
        fuente["ciclo"] + "__in": consulta.ciclos,
        fuente["cef"] + "__in": motor._cefs_filtrados_por_territorio(consulta, cef_map),
    })


def _filtrar(qs, consulta, descriptores):
    filtros = {k: v for k, v in consulta.filtros.items() if k in descriptores}
    return motor._aplicar_filtros(qs, replace(consulta, filtros=filtros), {"filtros": descriptores})


def _buscar(
    qs,
    texto,
    campos,
    campo_cef=None,
    cef_map=None,
    *,
    entidad=None,
    buscar_campo="",
    campo_numero_grupo=None,
):
    if buscar_campo:
        campos = BUSQUEDA_CAMPOS[entidad][buscar_campo]
        if buscar_campo != "cef":
            campo_cef = None

    numero_grupo = _numero_grupo_busqueda(texto) if campo_numero_grupo else None
    requiere_distinct = any("dias_funcionamiento" in campo for campo in campos)

    for termino in texto.replace(",", " ").split():
        condicion = Q()
        for campo in campos:
            condicion |= Q(**{campo + "__icontains": termino})
        if campo_cef:
            condicion |= Q(**{campo_cef + "__in": _cefs_busqueda(termino, cef_map)})
        if campo_numero_grupo and numero_grupo is not None:
            condicion |= Q(**{campo_numero_grupo: numero_grupo})
        elif campo_numero_grupo and termino.isdigit():
            condicion |= Q(**{campo_numero_grupo: int(termino)})
        elif campo_numero_grupo and _normalizar_busqueda(termino) == "grupo" and campos:
            condicion |= Q(**{campos[0]: ""})
        qs = qs.filter(condicion)

    return qs.distinct() if requiere_distinct else qs


def _buscar_asistencia(qs, texto, cef_map, buscar_campo=""):
    """Resuelve en SQL la búsqueda de Asistencia, incluida la opción Todos."""
    prefijo = "jornada__grupo__"

    if buscar_campo in BUSQUEDA_CAMPOS["asistencia"]:
        return _buscar(
            qs,
            texto,
            BUSQUEDA_ASISTENCIA_TODOS,
            prefijo + "cueanexo",
            cef_map,
            entidad="asistencia",
            buscar_campo=buscar_campo,
            campo_numero_grupo=prefijo + "numero" if buscar_campo == "grupo" else None,
        )

    numero_grupo = _numero_grupo_busqueda(texto)
    for termino in texto.replace(",", " ").split():
        condicion = Q()

        if not buscar_campo:
            for campo in BUSQUEDA_ASISTENCIA_TODOS:
                condicion |= Q(**{campo + "__icontains": termino})
            condicion |= Q(**{prefijo + "cueanexo__in": _cefs_busqueda(termino, cef_map)})
            if numero_grupo is not None:
                condicion |= Q(**{prefijo + "numero": numero_grupo})
            elif _normalizar_busqueda(termino) == "grupo":
                condicion |= Q(**{prefijo + "nombre": ""})
            if termino.isdigit():
                numero = int(termino)
                condicion |= Q(**{prefijo + "numero": numero})
                condicion |= Q(**{prefijo + "ciclo__anio": numero})

            fecha = _fecha_busqueda(termino)
            if fecha is not None:
                condicion |= Q(jornada__fecha=fecha)

            horas = _horas_busqueda(termino)
            if len(horas) >= 2:
                condicion |= Q(**{
                    prefijo + "hora_inicio": horas[0],
                    prefijo + "hora_fin": horas[1],
                })
            elif horas:
                condicion |= Q(**{prefijo + "hora_inicio": horas[0]})
                condicion |= Q(**{prefijo + "hora_fin": horas[0]})

        elif buscar_campo == "ciclo":
            if termino.isdigit():
                condicion = Q(**{prefijo + "ciclo__anio": int(termino)})
            else:
                condicion = Q(pk__in=[])

        elif buscar_campo == "fecha":
            fecha = _fecha_busqueda(termino)
            condicion = Q(jornada__fecha=fecha) if fecha is not None else Q(pk__in=[])

        elif buscar_campo == "horario":
            horas = _horas_busqueda(termino)
            if len(horas) >= 2:
                condicion = Q(**{
                    prefijo + "hora_inicio": horas[0],
                    prefijo + "hora_fin": horas[1],
                })
            elif horas:
                condicion = (
                    Q(**{prefijo + "hora_inicio": horas[0]})
                    | Q(**{prefijo + "hora_fin": horas[0]})
                )
            else:
                condicion = Q(pk__in=[])

        qs = qs.filter(condicion)

    return qs.distinct()


def _fecha(valor):
    return valor.strftime("%d/%m/%Y") if valor else ""


def _unicos(valores):
    return " · ".join(dict.fromkeys(str(v) for v in valores if v not in (None, "")))


def _contexto(cue, ciclo, cef_map):
    # Un ciclo es una etiqueta/año, no una cantidad: debe mostrarse siempre como 2026.
    return {"cef": motor._cef_resultado(cue, cef_map), "cueanexo": cue, "ciclo": str(ciclo.anio)}


def _cargar_grupos(qs, prefijo=""):
    relaciones = ("ciclo", "actividad__eje", "actividad__codigo_ra", "codigo_ra_override", "nivel", "rango_etario", "turno")
    return qs.select_related(*(prefijo + campo for campo in relaciones)).prefetch_related(
        prefijo + "dias_funcionamiento__dia_semana"
    )


def _grupo(grupo, cef_map):
    datos = _contexto(grupo.cueanexo, grupo.ciclo, cef_map)
    datos.update({
        "grupo_id": grupo.pk, "grupo": grupo.nombre or f"Grupo {grupo.numero}",
        "actividad": grupo.actividad_nombre_snapshot or grupo.actividad.nombre,
        "eje": grupo.eje_nombre_snapshot or grupo.actividad.eje.nombre,
        "nivel": grupo.nivel_nombre_snapshot or grupo.nivel.nombre,
        "rango_etario": grupo.rango_etario_nombre_snapshot or grupo.rango_etario.nombre,
        "turno": grupo.turno_nombre_snapshot or grupo.turno.nombre,
        "dias": _unicos(d.dia_semana.nombre for d in grupo.dias_funcionamiento.all()),
        "horario": f"{grupo.hora_inicio:%H:%M}–{grupo.hora_fin:%H:%M}",
        "estado_grupo": grupo.get_estado_display(),
    })
    return datos


def _relacion(registro, alumno, cef_map):
    datos = _grupo(registro.grupo, cef_map)
    datos.update({
        "estado_relacion": registro.get_estado_display(),
        "desde": _fecha(registro.fecha_inscripcion if alumno else registro.fecha_desde),
        "hasta": _fecha(registro.fecha_baja if alumno else registro.fecha_hasta),
    })
    if not alumno:
        datos["rol"] = registro.get_rol_display()
    return datos


def _personas(entidad, consulta, cef_map, paginar, buscar_campo=""):
    alumno = entidad == "alumnos"
    identidad = "alumno_id" if alumno else "docente_cuil"
    source = "inscripciones" if alumno else "asignaciones"
    estado = "estado_inscripcion" if alumno else "estado_asignacion"
    fecha = "fecha_inscripcion" if alumno else "fecha_asignacion"
    banco = _scope(ENTIDADES[entidad]["source"], consulta, cef_map)
    relaciones = _scope(source, consulta, cef_map)
    filtros_banco = {"estado_banco": "estado", "fecha_alta": ("fecha", "fecha_alta")}
    filtros_relacion = {
        **motor._filtros_grupo("grupo__"), "estado_grupo": "grupo__estado",
        estado: "estado", fecha: ("fecha", "fecha_inscripcion" if alumno else "fecha_desde"),
    }
    filtros_relacion.pop("estado")
    if not alumno:
        filtros_relacion["rol"] = "rol"
    banco = _filtrar(banco, consulta, filtros_banco)
    relaciones = _filtrar(relaciones, consulta, filtros_relacion)
    # Cruces por persona + CEF + ciclo. Los filtros de actividad, turno, estado
    # y rol coinciden siempre sobre la misma inscripción/asignación.
    if set(consulta.filtros) & filtros_banco.keys():
        relaciones = relaciones.filter(Exists(banco.filter(**{
            identidad: OuterRef(identidad), "cueanexo": OuterRef("grupo__cueanexo"),
            "ciclo_id": OuterRef("grupo__ciclo_id"),
        })))
    if set(consulta.filtros) & filtros_relacion.keys():
        banco = banco.filter(Exists(relaciones.filter(**{
            identidad: OuterRef(identidad), "grupo__cueanexo": OuterRef("cueanexo"),
            "grupo__ciclo_id": OuterRef("ciclo_id"),
        })))
    if buscar_campo == "cef" and consulta.buscar:
        banco = _buscar(banco, consulta.buscar, (), "cueanexo", cef_map)
        relaciones = _buscar(relaciones, consulta.buscar, (), "grupo__cueanexo", cef_map)
    if alumno:
        modelo = banco.model._meta.get_field("alumno").remote_field.model
        raices = modelo.objects.filter(
            Exists(banco.filter(alumno_id=OuterRef("pk"))) |
            Exists(relaciones.filter(alumno_id=OuterRef("pk")))
        )
        raices = raices.annotate(_consulta_hoy=Value(timezone.localdate(), output_field=DateField()))
        raices = raices.annotate(_metrica_edad=motor._edad_historica_expresion("_consulta_hoy", "fecha_nacimiento"))
        raices = _filtrar(raices, consulta, {"sexo": "sexo_id", "edad": ("edad",)})
        if consulta.buscar and not buscar_campo:
            ids_busqueda = _ids_personas_todos(
                entidad, banco, relaciones, cef_map, consulta.buscar, raices
            )
            raices = raices.filter(pk__in=ids_busqueda)
        else:
            raices = _buscar(
                raices,
                consulta.buscar,
                ("apellidos", "nombres", "nro_doc", "cuil"),
                entidad=entidad,
                buscar_campo=buscar_campo,
            )
        raices = raices.order_by("apellidos", "nombres", "pk")
        registros, paginacion = motor._paginar_filas(raices, consulta, paginar)
        ids = [r.pk for r in registros]
    else:
        if consulta.buscar and not buscar_campo:
            raices = sorted(
                _ids_personas_todos(
                    entidad, banco, relaciones, cef_map, consulta.buscar
                )
            )
        else:
            campos = ("docente_nombre_snapshot", "docente_dni_snapshot", "docente_cuil")
            candidatos_banco = _buscar(
                banco, consulta.buscar, campos,
                entidad=entidad, buscar_campo=buscar_campo
            ).order_by().values_list(identidad, flat=True)
            candidatos_relacion = _buscar(
                relaciones, consulta.buscar, campos,
                entidad=entidad, buscar_campo=buscar_campo
            ).order_by().values_list(identidad, flat=True)
            raices = candidatos_banco.union(candidatos_relacion).order_by(identidad)
        ids, paginacion = motor._paginar_filas(raices, consulta, paginar)
        registros = ids
    bancos_por_id, relaciones_por_id = defaultdict(list), defaultdict(list)
    for registro in banco.filter(**{identidad + "__in": ids}).select_related("ciclo").order_by("-ciclo__anio", "-fecha_alta", "-pk"):
        bancos_por_id[getattr(registro, identidad)].append(registro)
    for registro in _cargar_grupos(relaciones.filter(**{identidad + "__in": ids}), "grupo__").order_by("-grupo__ciclo__anio", "grupo_id", "-pk"):
        relaciones_por_id[getattr(registro, identidad)].append(registro)
    sexo_map = motor._opciones_sexo_mapa({}) if alumno else {}
    filas = []
    for registro in registros:
        key = registro.pk if alumno else registro
        bancos, enlaces = bancos_por_id[key], relaciones_por_id[key]
        relaciones_publicas = [_relacion(r, alumno, cef_map) for r in enlaces]
        bancos_publicos = [dict(_contexto(r.cueanexo, r.ciclo, cef_map),
            estado_banco=r.get_estado_display(), desde=_fecha(r.fecha_alta), hasta=_fecha(r.fecha_baja)) for r in bancos]
        contextos = relaciones_publicas + bancos_publicos
        if alumno:
            fila = {
                "persona": motor._nombre_persona(registro.apellidos, registro.nombres),
                "documento": registro.nro_doc, "cuil": registro.cuil,
                "sexo": sexo_map.get(str(registro.sexo_id), motor.SIN_INFORMACION),
                "fecha_nacimiento": _fecha(registro.fecha_nacimiento), "edad": registro._metrica_edad,
            }
        else:
            datos = next((r for r in bancos + enlaces if r.docente_nombre_snapshot), None)
            fila = {"persona": datos.docente_nombre_snapshot if datos else key,
                    "documento": datos.docente_dni_snapshot if datos else "", "cuil": key}
        fila.update({
            "id": str(key), "cef": _unicos(r["cef"] for r in contextos),
            "ciclo": _unicos(r["ciclo"] for r in contextos),
            "grupos": len({r["grupo_id"] for r in relaciones_publicas}),
            "actividad": _unicos(r["actividad"] for r in relaciones_publicas),
            "turno": _unicos(r["turno"] for r in relaciones_publicas),
            "estado_banco": _unicos(r["estado_banco"] for r in bancos_publicos),
            "estado_relacion": _unicos(r["estado_relacion"] for r in relaciones_publicas),
            "rol": _unicos(r.get("rol") for r in relaciones_publicas),
            "relations": relaciones_publicas, "bank": bancos_publicos,
        })
        filas.append(fila)
    total = paginacion["total_rows"] if paginacion else len(filas)
    return filas, paginacion, total


def _registros(entidad, consulta, cef_map, paginar, buscar_campo=""):
    source = ENTIDADES[entidad]["source"]
    qs = _scope(source, consulta, cef_map)
    descriptores = dict(motor.FUENTES[source]["filtros"])
    if "estado" in descriptores:
        clave = {"grupos": "estado_grupo", "asistencia": "estado_asistencia", "inventario": "estado_material"}[entidad]
        descriptores[clave] = descriptores.pop("estado")
    qs = _filtrar(qs, consulta, descriptores)
    if entidad in {"grupos", "asistencia"}:
        prefijo = "" if entidad == "grupos" else "jornada__grupo__"
        if entidad == "asistencia":
            qs = qs.select_related("inscripcion__alumno", "jornada")
            qs = _buscar_asistencia(qs, consulta.buscar, cef_map, buscar_campo)
        else:
            campos = ("nombre", "actividad_nombre_snapshot", "actividad__nombre")
            qs = _buscar(
                qs,
                consulta.buscar,
                campos,
                "cueanexo",
                cef_map,
                entidad=entidad,
                buscar_campo=buscar_campo,
                campo_numero_grupo="numero" if buscar_campo == "grupo" else None,
            )
        qs = _cargar_grupos(qs, prefijo)
        if entidad == "grupos":
            qs = motor._anotar_alumnos_activos(qs).prefetch_related(Prefetch(
                "docentes", queryset=CefDocenteGrupo.objects.filter(estado="activo").order_by("rol", "docente_cuil"),
                to_attr="consulta_docentes"
            )).order_by("cueanexo", "-ciclo__anio", "actividad__nombre", "numero", "pk")
        else:
            qs = qs.order_by("-jornada__fecha", "jornada__grupo_id", "inscripcion__alumno_id", "pk")
    elif entidad == "inventario":
        qs = _buscar(qs, consulta.buscar, ("inventario_material__material_nombre_snapshot",
            "inventario_material__material__nombre", "estado__nombre", "estado_descripcion"),
            "inventario_material__cueanexo", cef_map, entidad=entidad, buscar_campo=buscar_campo)
        qs = qs.select_related("inventario_material__ciclo", "inventario_material__material", "estado").order_by(
            "inventario_material__material__nombre", "inventario_material__cueanexo", "inventario_material__ciclo__anio", "pk")
    else:
        qs = _buscar(qs, consulta.buscar, ("cueanexo",), "cueanexo", cef_map, entidad=entidad, buscar_campo=buscar_campo)
        qs = qs.select_related("ciclo", "beneficio_alimentario_gratuito", "fuente_financiamiento",
            "prestacion_tipo", "espacio_comedor", "c_orientacion").order_by("cueanexo", "-ciclo__anio", "pk")
    unidades = (qs.aggregate(total=Sum("cantidad"))["total"] or 0) if entidad == "inventario" else None
    registros, paginacion = motor._paginar_filas(qs, consulta, paginar)
    filas = []
    for r in registros:
        if entidad == "grupos":
            fila = dict(_grupo(r, cef_map), cupo=r.cupo_maximo, alumnos=r._metrica_alumnos_activos,
                profesores=_unicos((d.docente_nombre_snapshot or d.docente_cuil) + " (" + d.get_rol_display() + ")"
                                    for d in r.consulta_docentes), observaciones=r.observaciones)
        elif entidad == "asistencia":
            alumno = r.inscripcion.alumno
            fila = dict(_grupo(r.jornada.grupo, cef_map), persona=motor._nombre_persona(alumno.apellidos, alumno.nombres),
                documento=alumno.nro_doc, fecha=_fecha(r.jornada.fecha), estado_asistencia=r.get_estado_display())
        elif entidad == "inventario":
            inv = r.inventario_material
            fila = dict(_contexto(inv.cueanexo, inv.ciclo, cef_map),
                material=inv.material_nombre_snapshot or inv.material.nombre,
                estado_material=r.estado.nombre if r.estado_id else r.estado_descripcion,
                cantidad=r.cantidad, observaciones=inv.observaciones)
        else:
            fila = dict(_contexto(r.cueanexo, r.ciclo, cef_map), observaciones=r.observaciones)
            for clave, snapshot, campo in (
                ("beneficio", "beneficio_nombre_snapshot", "beneficio_alimentario_gratuito"),
                ("financiamiento", "fuente_nombre_snapshot", "fuente_financiamiento"),
                ("prestacion", "prestacion_nombre_snapshot", "prestacion_tipo"),
                ("espacio_comedor", "espacio_comedor_nombre_snapshot", "espacio_comedor"),
                ("orientacion", "orientacion_nombre_snapshot", "c_orientacion"),
            ):
                fila[clave] = getattr(r, snapshot) or getattr(r, campo).nombre
        fila["id"] = str(r.pk)
        filas.append(fila)
    total = unidades if entidad == "inventario" else paginacion["total_rows"] if paginacion else len(filas)
    return filas, paginacion, total


def ejecutar_listado(params, paginar=True):
    entidad = params.get("entidad", "alumnos")
    if entidad not in ENTIDADES:
        raise motor.MetricasValidationError("El listado solicitado no está disponible.")
    ciclos_db, cef_map = motor._cargar_ciclos(), motor._cargar_cefs()
    consulta, filtros, columnas = _resolver_listado(params, entidad, ciclos_db, cef_map)
    funcion = _personas if entidad in {"alumnos", "profesores"} else _registros
    buscar_campo = params.get("buscar_campo", "")
    if consulta.buscar and not buscar_campo and entidad not in {"asistencia", "alumnos", "profesores"}:
        # "Todos" debe representar la fila pública completa. Asistencia y
        # personas se reducen antes en SQL/IDs para evitar materializar listados grandes.
        filas, _, _ = funcion(entidad, replace(consulta, buscar=""), cef_map, False)
        filas = _buscar_filas_todos(
            filas,
            consulta.buscar,
            [columna["key"] for columna in ENTIDADES[entidad]["columns"]],
        )
        total = sum(fila["cantidad"] for fila in filas) if entidad == "inventario" else len(filas)
        filas, paginacion = motor._paginar_filas(filas, consulta, paginar)
    elif buscar_campo and not _busqueda_directa(entidad, buscar_campo):
        if consulta.buscar:
            # Las columnas calculadas se buscan sobre la misma proyección que ve
            # la persona usuaria, preservando filtros y alcance.
            filas, _, _ = funcion(entidad, replace(consulta, buscar=""), cef_map, False)
            filas = _buscar_filas(filas, consulta.buscar, buscar_campo)
            total = sum(fila["cantidad"] for fila in filas) if entidad == "inventario" else len(filas)
            filas, paginacion = motor._paginar_filas(filas, consulta, paginar)
        else:
            filas, paginacion, total = funcion(entidad, consulta, cef_map, paginar)
    else:
        filas, paginacion, total = funcion(entidad, consulta, cef_map, paginar, buscar_campo)
    meta = ENTIDADES[entidad]
    columnas_resultado = [c for c in meta["columns"] if paginar or not columnas or c["key"] in columnas]
    detalle_columnas = _columnas(*CONTEXTO_COLUMNAS, *GRUPO_COLUMNAS,
        ("estado_relacion", "Estado de inscripción" if entidad == "alumnos" else "Estado de asignación", True, "text"),
        ("desde", "Desde", True, "text"), ("hasta", "Hasta", True, "text"))
    if entidad == "profesores":
        detalle_columnas += _columnas(("rol", "Rol", True, "text"))
    return {
        "mode": "listados", "entity": entidad,
        "query": {
            "area_label": meta["label"], "indicador_label": "Listado de " + meta["label"],
            "ciclos": [{"label": str(c["anio"])} for c in ciclos_db if c["pk"] in consulta.ciclos],
            "cefs": [{"label": motor._cef_resultado(c, cef_map)} for c in consulta.cefs],
            "todos_cef": consulta.todos_cef, "filters": filtros, "buscar": consulta.buscar,
        },
        "total": {"value": total, "formatted": motor._formatear_numero(total, ""), "unit": meta["unit"]},
        "table": {"kind": "records", "columns": columnas_resultado, "rows": filas, "pagination": paginacion,
            "detail_columns": detalle_columnas,
            "bank_columns": _columnas(*CONTEXTO_COLUMNAS,
                ("estado_banco", "Estado en el CEF", True, "text"),
                ("desde", "Alta en el CEF", True, "text"), ("hasta", "Baja en el CEF", True, "text"))},
        "definition": "Resultados que coinciden con los CEF, ciclos, filtros y búsqueda seleccionados.",
        "notes": ["Una fila por persona. El detalle incluye sólo los grupos y registros en el CEF que coinciden con los filtros, dentro de los CEF y ciclos seleccionados."] if entidad in {"alumnos", "profesores"} else [],
    }




def _cef_corto_estadistica(cef):
    nombre = str(cef.get("nombre") or "")
    coincidencia = re.search(r"\bN(?:RO\.?|[º°])?\s*0*(\d+)\b", nombre, re.IGNORECASE)
    if coincidencia:
        return "CEF " + coincidencia.group(1)
    return "CEF " + str(cef.get("value") or "")


def _cefs_cortos_estadistica(cefs):
    bases = defaultdict(list)
    for cef in cefs:
        bases[_cef_corto_estadistica(cef)].append(str(cef.get("value") or ""))
    resultado = {}
    for cef in cefs:
        value = str(cef.get("value") or "")
        base = _cef_corto_estadistica(cef)
        resultado[value] = base if len(bases[base]) == 1 else f"{base} · {value}"
    return resultado


def _grupo_corto_estadistica(grupo):
    actividad = (
        grupo.actividad_nombre_snapshot
        or (grupo.actividad.nombre if grupo.actividad_id else "")
        or "Actividad sin información"
    )
    nombre = (grupo.nombre or "").strip() or f"Grupo {grupo.numero}"
    if _normalizar_busqueda(nombre).startswith(_normalizar_busqueda(actividad)):
        return nombre
    return f"{actividad} · {nombre}"


def _paginar_estadistica_personalizada(filas, params, paginar):
    if not paginar:
        return filas, None
    try:
        tamano = int(params.get("tamano") or 25)
    except (TypeError, ValueError):
        tamano = 25
    try:
        pagina_solicitada = int(params.get("pagina") or 1)
    except (TypeError, ValueError):
        pagina_solicitada = 1
    paginador = Paginator(filas, tamano)
    pagina = paginador.get_page(pagina_solicitada)
    return list(pagina.object_list), {
        "page": pagina.number,
        "page_size": tamano,
        "total_rows": paginador.count,
        "pages": paginador.num_pages,
        "from": pagina.start_index(),
        "to": pagina.end_index(),
    }


def _personalizar_ocupacion_grupos(resultado, params, paginar):
    """Presentación legible de la ocupación cuando se cruzan varios CEF/ciclos."""
    tabla = resultado.get("table") or {}
    filas = list(tabla.get("rows") or [])
    query = resultado.get("query") or {}
    cefs = list(query.get("cefs") or [])
    ciclos = list(query.get("ciclos") or [])
    varios_cef = len(cefs) > 1
    varios_ciclos = len(ciclos) > 1

    ids = {
        int(fila["grupo_key"])
        for fila in filas
        if str(fila.get("grupo_key") or "").isdigit()
    }
    grupos = {
        grupo.pk: grupo
        for grupo in CefGrupo.objects.filter(pk__in=ids).select_related("ciclo", "actividad")
    }
    cef_por_codigo = {str(cef.get("value") or ""): cef for cef in cefs}
    cef_corto = _cefs_cortos_estadistica(cefs)
    orden_cef = {str(cef.get("value") or ""): indice for indice, cef in enumerate(cefs)}
    orden_ciclo = {
        int(ciclo.get("anio")): indice
        for indice, ciclo in enumerate(ciclos)
        if ciclo.get("anio") is not None
    }

    filas_personalizadas = []
    for fila in filas:
        try:
            grupo_id = int(fila.get("grupo_key"))
        except (TypeError, ValueError):
            grupo_id = None
        grupo = grupos.get(grupo_id)
        if grupo is None:
            filas_personalizadas.append(dict(fila))
            continue

        codigo_cef = str(grupo.cueanexo)
        actividad = (
            grupo.actividad_nombre_snapshot
            or (grupo.actividad.nombre if grupo.actividad_id else "")
            or ""
        )
        nueva = dict(fila)
        nueva["grupo"] = _grupo_corto_estadistica(grupo)
        if varios_cef:
            nueva["cef"] = cef_corto.get(codigo_cef, codigo_cef)
        if varios_ciclos:
            nueva["ciclo"] = grupo.ciclo.anio
        nueva["_orden"] = (
            orden_cef.get(codigo_cef, len(orden_cef)),
            orden_ciclo.get(grupo.ciclo.anio, len(orden_ciclo)),
            _normalizar_busqueda(actividad),
            grupo.numero,
            grupo.pk,
        )
        filas_personalizadas.append(nueva)

    filas_personalizadas.sort(key=lambda fila: fila.get("_orden", (9999, 9999, "", 9999, 9999)))
    for fila in filas_personalizadas:
        fila.pop("_orden", None)

    columnas_metricas = [
        columna for columna in (tabla.get("columns") or [])
        if columna.get("key") != "grupo"
    ]
    columnas = []
    if varios_cef:
        columnas.append({"key": "cef", "label": "CEF"})
    if varios_ciclos:
        columnas.append({"key": "ciclo", "label": "Ciclo"})
    columnas.append({"key": "grupo", "label": "Grupo"})
    columnas.extend(columnas_metricas)

    filas_paginadas, paginacion = _paginar_estadistica_personalizada(
        filas_personalizadas, params, paginar
    )
    tabla["columns"] = columnas
    tabla["rows"] = filas_paginadas
    tabla["pagination"] = paginacion

    total = resultado.get("total") or {}
    total["label"] = "Ocupación total de los grupos seleccionados"
    cantidad_grupos = len(filas_personalizadas)
    detalle = (
        f"{motor._formatear_numero(total.get('numerator'), '')} inscripciones activas "
        f"sobre un cupo total informado de "
        f"{motor._formatear_numero(total.get('denominator'), '')}"
    )
    detalle += f" · {cantidad_grupos} " + ("grupo" if cantidad_grupos == 1 else "grupos")
    total["detail"] = detalle

    grafico = resultado.get("chart") or {}
    claves = [str(clave) for clave in (grafico.get("keys") or [])]
    if claves and not grafico.get("omitted"):
        etiquetas = []
        etiquetas_completas = []
        categorias = []
        for clave in claves:
            grupo = grupos.get(int(clave)) if clave.isdigit() else None
            if grupo is None:
                etiquetas.append(clave)
                etiquetas_completas.append(clave)
                categorias.append({"key": clave, "label": "", "cycle": ""})
                continue
            codigo_cef = str(grupo.cueanexo)
            grupo_corto = _grupo_corto_estadistica(grupo)
            etiquetas.append(grupo_corto)
            categorias.append({
                "key": codigo_cef,
                "label": cef_corto.get(codigo_cef, codigo_cef) if varios_cef else "",
                "cycle": str(grupo.ciclo.anio) if varios_ciclos else "",
            })

            cef_completo = cef_por_codigo.get(codigo_cef, {}).get("label") or codigo_cef
            etiquetas_completas.append(
                f"{cef_completo} · {grupo_corto} · {grupo.ciclo.anio}"
            )

        # Sólo el gráfico sigue el orden CEF/ciclo/grupo ya resuelto para la tabla.
        orden_grafico = {
            str(fila.get("grupo_key")): indice
            for indice, fila in enumerate(filas_personalizadas)
        }
        indices = sorted(
            range(len(etiquetas)),
            key=lambda indice: orden_grafico.get(claves[indice], len(orden_grafico) + indice),
        )
        grafico["labels"] = [etiquetas[indice] for indice in indices]
        grafico["full_labels"] = [etiquetas_completas[indice] for indice in indices]
        grafico["category_groups"] = [categorias[indice] for indice in indices]
        grafico["keys"] = [claves[indice] for indice in indices]
        for serie in grafico.get("series") or []:
            datos = list(serie.get("data") or [])
            serie["data"] = [datos[indice] if indice < len(datos) else None for indice in indices]
        grafico["presentation"] = "grupos_ocupacion"
        grafico["orientation"] = "vertical"
        grafico["max_value"] = 100
        grafico["value_suffix"] = " %"

    return resultado


def ejecutar_estadistica(params, paginar=True):
    key = params.get("pregunta", "")
    if key not in PREGUNTAS:
        raise motor.MetricasValidationError("Elegí una pregunta estadística disponible.")
    entidad, label, indicador, agrupar, comparar, grafico = PREGUNTAS[key]
    if params.get("entidad", entidad) != entidad:
        raise motor.MetricasValidationError("La pregunta no corresponde a la categoría seleccionada.")
    base = params.copy()
    for key_control in ("modo", "entidad", "pregunta", "columnas"):
        base.pop(key_control, None)
    base.pop("f_codigo_ra", None)
    if any(k in base for k in ("area", "indicador", "agrupar", "comparar", "grafico", "vista", "buscar")):
        raise motor.MetricasValidationError("La presentación de esta estadística ya está definida.")
    base.update({"area": ENTIDADES[entidad]["area"], "indicador": indicador, "agrupar": agrupar,
                 "comparar": comparar, "grafico": grafico, "vista": "resumen"})
    personalizar_ocupacion = key == "grupos_ocupacion"
    resultado = motor.ejecutar_consulta_metricas(
        base,
        paginar_detalle=False if personalizar_ocupacion else paginar,
    )
    resultado.update(mode="estadisticas", entity=entidad, question=label)
    if personalizar_ocupacion:
        resultado = _personalizar_ocupacion_grupos(resultado, params, paginar)
    if entidad == "inventario":
        resultado["notes"].append(
            "Esta estadística incluye unidades con estado asociado al catálogo. "
            "Los registros antiguos que sólo tienen una descripción de estado también se pueden consultar en Listados."
        )
    return resultado


def ejecutar_consulta(params, paginar=True):
    modo = params.get("modo", "listados")
    if modo == "listados":
        return ejecutar_listado(params, paginar)
    if modo == "estadisticas":
        return ejecutar_estadistica(params, paginar)
    raise motor.MetricasValidationError("El modo de consulta no está permitido.")