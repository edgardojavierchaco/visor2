# -*- coding: utf-8 -*-

from collections import defaultdict

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator
from django.db import IntegrityError, transaction
from django.db.models import Prefetch
from django.utils import timezone

from .models import (
    CefAlumnoCef,
    CefCiclo,
    CefDatosRelevamiento,
    CefDocenteCef,
    CefDocenteGrupo,
    CefGrupo,
    CefGrupoDiaFuncionamiento,
    CefInscripcion,
    CefInventarioMaterial,
    CefInventarioMaterialEstado,
    CefTurno,
    normalizar_cueanexo,
    solo_digitos,
)


CATEGORIAS_ANUALES = (
    ("turnos", "Turnos"),
    ("datos_relevamiento", "Datos adicionales"),
    ("grupos", "Grupos activos"),
    ("dias", "Días de funcionamiento"),
    ("alumnos", "Alumnos activos"),
    ("docentes", "Profesores activos"),
    ("inscripciones", "Inscripciones activas"),
    ("asignaciones", "Asignaciones activas"),
    ("inventario_materiales", "Materiales de inventario"),
    ("inventario_distribuciones", "Distribuciones de inventario"),
)


def _contadores_vacios():
    return {
        clave: {"encontrados": 0, "proyectables": 0}
        for clave, _ in CATEGORIAS_ANUALES
    }


def _resultado_base(ciclo_origen):
    destino_anio = ciclo_origen.anio + 1
    return {
        "origen": {
            "id": ciclo_origen.pk,
            "anio": ciclo_origen.anio,
            "actual": ciclo_origen.actual,
            "cerrado": ciclo_origen.cerrado,
        },
        "destino_anio": destino_anio,
        "destino_existente": False,
        "fecha_generacion_prevista": timezone.localdate(),
        "requiere_cierre": not ciclo_origen.cerrado,
        "puede_generar": ciclo_origen.cerrado and not ciclo_origen.actual,
        "bloqueado": False,
        "categorias": [
            {"clave": clave, "label": label}
            for clave, label in CATEGORIAS_ANUALES
        ],
        "totales": _contadores_vacios(),
        "cantidad_cueanexos": 0,
        "por_cef": [],
        "errores": [],
        "advertencias": [],
        "proyeccion": {
            "turnos": [],
            "grupos": [],
            "turnos_origen_ids": [],
            "datos_relevamiento_origen_ids": [],
            "grupos_origen_ids": [],
            "dias_origen_ids": [],
            "alumnos_origen_ids": [],
            "docentes_origen_ids": [],
            "inscripciones_origen_ids": [],
            "asignaciones_origen_ids": [],
            "inventario_materiales_origen_ids": [],
            "inventario_distribuciones_origen_ids": [],
        },
    }


def _agregar_detalle(lista, codigo, mensaje, cueanexo=""):
    lista.append(
        {
            "codigo": codigo,
            "cueanexo": str(cueanexo or ""),
            "mensaje": mensaje,
        }
    )


def _cue_normalizado_valido(cueanexo):
    valor = str(cueanexo or "")
    normalizado = normalizar_cueanexo(valor)
    return normalizado if normalizado and normalizado == valor else ""


def _rotulo_grupo(grupo):
    actividad = (
        grupo.actividad_nombre_snapshot
        or getattr(grupo.actividad, "nombre", "")
        or "Actividad sin nombre"
    )
    return f"{actividad} Nro. {grupo.numero}"


def _nombre_alumno(inscripcion, banco=None):
    if banco and banco.alumno_nombre_snapshot:
        return banco.alumno_nombre_snapshot
    alumno = getattr(inscripcion, "alumno", None)
    apellidos = str(getattr(alumno, "apellidos", "") or "").strip()
    nombres = str(getattr(alumno, "nombres", "") or "").strip()
    nombre = ", ".join(parte for parte in (apellidos, nombres) if parte)
    return nombre or "Alumno sin nombre disponible"


def _superponen_horarios(grupo_a, grupo_b):
    """Mantener equivalente a la fórmula estricta de Fase 4."""

    return (
        grupo_a.hora_inicio < grupo_b.hora_fin
        and grupo_b.hora_inicio < grupo_a.hora_fin
    )


def _anio_maximo_ciclo():
    limites = [
        validador.limit_value
        for validador in CefCiclo._meta.get_field("anio").validators
        if isinstance(validador, MaxValueValidator)
    ]
    return min(limites) if limites else None


def origen_anual_previsualizable(ciclo_origen):
    """Acepta el actual abierto o el último ciclo cerrado sin sucesor."""

    if ciclo_origen.actual and not ciclo_origen.cerrado:
        return True
    if not ciclo_origen.cerrado or ciclo_origen.actual:
        return False
    return not CefCiclo.objects.filter(anio__gt=ciclo_origen.anio).exists()


def prevalidar_generacion_anual(ciclo_origen):
    """Proyecta en memoria la generación N+1 sin producir escrituras."""

    resultado = _resultado_base(ciclo_origen)
    errores = resultado["errores"]
    advertencias = resultado["advertencias"]
    destino_anio = resultado["destino_anio"]

    if not origen_anual_previsualizable(ciclo_origen):
        _agregar_detalle(
            errores,
            "origen_anual_no_valido",
            (
                "La previsualización anual sólo puede ejecutarse sobre el ciclo "
                "actual abierto o sobre el último ciclo cerrado sin sucesor."
            ),
        )
        resultado["bloqueado"] = True
        resultado["totales"]["errores"] = len(errores)
        resultado["totales"]["advertencias"] = len(advertencias)
        for categoria in resultado["categorias"]:
            categoria["total"] = resultado["totales"][categoria["clave"]]
        return resultado

    anio_maximo = _anio_maximo_ciclo()
    if anio_maximo is not None and destino_anio > anio_maximo:
        _agregar_detalle(
            errores,
            "destino_fuera_de_rango",
            (
                f"El ciclo proyectado {destino_anio} supera el máximo admitido "
                f"de {anio_maximo}."
            ),
        )

    destino_existente = (
        CefCiclo.objects.filter(anio=destino_anio)
        .only("pk", "anio")
        .first()
    )
    resultado["destino_existente"] = destino_existente is not None
    if destino_existente is not None:
        _agregar_detalle(
            errores,
            "destino_preexistente",
            (
                f"Ya existe el ciclo {destino_anio}. La generación anual automática "
                "no puede continuar sobre un ciclo destino preexistente."
            ),
        )

    turnos = list(
        CefTurno.objects.filter(ciclo=ciclo_origen).order_by(
            "orden",
            "nombre",
            "pk",
        )
    )
    relevamientos = list(
        CefDatosRelevamiento.objects.filter(ciclo=ciclo_origen).order_by(
            "cueanexo",
            "pk",
        )
    )
    dias_queryset = CefGrupoDiaFuncionamiento.objects.select_related(
        "dia_semana"
    ).order_by(
        "dia_semana__orden",
        "dia_semana__numero",
        "pk",
    )
    grupos = list(
        CefGrupo.objects.filter(ciclo=ciclo_origen)
        .select_related(
            "actividad",
            "turno",
            "nivel",
            "rango_etario",
            "codigo_ra_override",
        )
        .prefetch_related(
            Prefetch(
                "dias_funcionamiento",
                queryset=dias_queryset,
                to_attr="dias_prevalidacion",
            )
        )
        .order_by("cueanexo", "actividad__nombre", "numero", "pk")
    )
    alumnos = list(
        CefAlumnoCef.objects.filter(
            ciclo=ciclo_origen,
            estado=CefAlumnoCef.Estado.ACTIVO,
        ).order_by("cueanexo", "alumno_id", "pk")
    )
    docentes = list(
        CefDocenteCef.objects.filter(
            ciclo=ciclo_origen,
            estado=CefDocenteCef.Estado.ACTIVO,
        ).order_by("cueanexo", "docente_cuil", "pk")
    )
    inscripciones = list(
        CefInscripcion.objects.filter(
            grupo__ciclo=ciclo_origen,
            estado=CefInscripcion.Estado.ACTIVO,
        )
        .select_related("alumno", "grupo", "grupo__actividad")
        .order_by("grupo__cueanexo", "alumno_id", "grupo_id", "pk")
    )
    asignaciones = list(
        CefDocenteGrupo.objects.filter(
            grupo__ciclo=ciclo_origen,
            estado=CefDocenteGrupo.Estado.ACTIVO,
        )
        .select_related("grupo", "grupo__actividad")
        .order_by("grupo__cueanexo", "docente_cuil", "grupo_id", "rol", "pk")
    )
    distribuciones_queryset = (
        CefInventarioMaterialEstado.objects.select_related("estado")
        .order_by("estado_id", "estado_normalizado", "pk")
    )
    inventario = list(
        CefInventarioMaterial.objects.filter(ciclo=ciclo_origen)
        .select_related("material")
        .prefetch_related(
            Prefetch(
                "distribuciones_estado",
                queryset=distribuciones_queryset,
                to_attr="distribuciones_prevalidacion",
            )
        )
        .order_by("cueanexo", "material__orden", "material__nombre", "pk")
    )

    por_cef = {}

    def contar(cueanexo, categoria, encontrados=0, proyectables=0):
        cue = str(cueanexo or "") or "(sin CUE-Anexo)"
        if cue not in por_cef:
            por_cef[cue] = {
                "cueanexo": cue,
                "conteos": _contadores_vacios(),
            }
        contador = por_cef[cue]["conteos"][categoria]
        contador["encontrados"] += encontrados
        contador["proyectables"] += proyectables

    invalidos_turnos = set()
    turnos_por_nombre = defaultdict(list)
    for turno in turnos:
        turnos_por_nombre[(turno.nombre or "").strip().casefold()].append(turno)
        if (
            not turno.hora_desde_referencia
            or not turno.hora_hasta_referencia
            or turno.hora_hasta_referencia <= turno.hora_desde_referencia
        ):
            invalidos_turnos.add(turno.pk)
            _agregar_detalle(
                errores,
                f"turno_horario_invalido_{turno.pk}",
                f'El turno "{turno.nombre}" no posee un rango horario válido.',
            )
    for nombre, coincidencias in turnos_por_nombre.items():
        if nombre and len(coincidencias) > 1:
            invalidos_turnos |= {turno.pk for turno in coincidencias}
            _agregar_detalle(
                errores,
                f"turno_nombre_duplicado_{nombre}",
                f'El nombre de turno "{coincidencias[0].nombre}" está duplicado en el ciclo origen.',
            )

    turnos_validos = [turno for turno in turnos if turno.pk not in invalidos_turnos]
    resultado["totales"]["turnos"]["encontrados"] = len(turnos)
    resultado["totales"]["turnos"]["proyectables"] = len(turnos_validos)
    resultado["proyeccion"]["turnos_origen_ids"] = [
        turno.pk for turno in turnos_validos
    ]
    resultado["proyeccion"]["turnos"] = [
        {
            "turno_origen_id": turno.pk,
            "nombre_destino": turno.nombre,
            "hora_desde_referencia": turno.hora_desde_referencia,
            "hora_hasta_referencia": turno.hora_hasta_referencia,
            "activo": turno.activo,
            "orden": turno.orden,
        }
        for turno in turnos_validos
    ]
    turnos_validos_ids = {turno.pk for turno in turnos_validos}

    invalidos_relevamiento = set()
    relevamientos_por_cue = defaultdict(list)
    for relevamiento in relevamientos:
        contar(relevamiento.cueanexo, "datos_relevamiento", encontrados=1)
        cue = _cue_normalizado_valido(relevamiento.cueanexo)
        if not cue:
            invalidos_relevamiento.add(relevamiento.pk)
            _agregar_detalle(
                errores,
                f"relevamiento_cue_invalido_{relevamiento.pk}",
                "Existe una fila de datos adicionales con CUE-Anexo inválido.",
                relevamiento.cueanexo,
            )
        relevamientos_por_cue[cue or str(relevamiento.cueanexo)].append(relevamiento)
    for cue, coincidencias in relevamientos_por_cue.items():
        if len(coincidencias) > 1:
            invalidos_relevamiento |= {item.pk for item in coincidencias}
            _agregar_detalle(
                errores,
                f"relevamiento_duplicado_{cue}",
                f"El CEF {cue} posee más de una fila de datos adicionales en el ciclo origen.",
                cue,
            )
    relevamientos_validos = [
        item for item in relevamientos if item.pk not in invalidos_relevamiento
    ]
    for relevamiento in relevamientos_validos:
        contar(relevamiento.cueanexo, "datos_relevamiento", proyectables=1)
    resultado["totales"]["datos_relevamiento"]["encontrados"] = len(relevamientos)
    resultado["totales"]["datos_relevamiento"]["proyectables"] = len(
        relevamientos_validos
    )
    resultado["proyeccion"]["datos_relevamiento_origen_ids"] = [
        item.pk for item in relevamientos_validos
    ]

    grupos_por_id = {grupo.pk: grupo for grupo in grupos}
    grupos_activos = [
        grupo for grupo in grupos if grupo.estado == CefGrupo.Estado.ACTIVO
    ]
    invalidos_grupos = set()
    grupos_por_clave = defaultdict(list)
    dias_validos_por_grupo = {}
    for grupo in grupos_activos:
        contar(grupo.cueanexo, "grupos", encontrados=1)
        dias = list(grupo.dias_prevalidacion)
        contar(grupo.cueanexo, "dias", encontrados=len(dias))
        cue = _cue_normalizado_valido(grupo.cueanexo)
        if not cue:
            invalidos_grupos.add(grupo.pk)
            _agregar_detalle(
                errores,
                f"grupo_cue_invalido_{grupo.pk}",
                f"El grupo {_rotulo_grupo(grupo)} posee un CUE-Anexo inválido.",
                grupo.cueanexo,
            )
        grupos_por_clave[
            (cue or str(grupo.cueanexo), grupo.actividad_id, grupo.numero)
        ].append(grupo)
        if grupo.turno.ciclo_id != ciclo_origen.pk:
            invalidos_grupos.add(grupo.pk)
            _agregar_detalle(
                errores,
                f"grupo_turno_otro_ciclo_{grupo.pk}",
                (
                    f"El grupo {_rotulo_grupo(grupo)} del CEF {grupo.cueanexo} "
                    "referencia un turno de otro ciclo."
                ),
                grupo.cueanexo,
            )
        elif grupo.turno_id not in turnos_validos_ids:
            invalidos_grupos.add(grupo.pk)
            _agregar_detalle(
                errores,
                f"grupo_turno_no_proyectable_{grupo.pk}",
                (
                    f"El grupo {_rotulo_grupo(grupo)} del CEF {grupo.cueanexo} "
                    "no puede resolver un turno válido para el ciclo proyectado."
                ),
                grupo.cueanexo,
            )
        if (
            not grupo.hora_inicio
            or not grupo.hora_fin
            or grupo.hora_fin <= grupo.hora_inicio
        ):
            invalidos_grupos.add(grupo.pk)
            _agregar_detalle(
                errores,
                f"grupo_horario_invalido_{grupo.pk}",
                f"El grupo {_rotulo_grupo(grupo)} posee un horario inválido.",
                grupo.cueanexo,
            )
        elif grupo.turno_id in turnos_validos_ids and (
            grupo.hora_inicio < grupo.turno.hora_desde_referencia
            or grupo.hora_fin > grupo.turno.hora_hasta_referencia
        ):
            invalidos_grupos.add(grupo.pk)
            _agregar_detalle(
                errores,
                f"grupo_fuera_turno_{grupo.pk}",
                (
                    f"El horario de {_rotulo_grupo(grupo)} no está contenido "
                    f'en el turno "{grupo.turno.nombre}".'
                ),
                grupo.cueanexo,
            )
        if not dias:
            invalidos_grupos.add(grupo.pk)
            _agregar_detalle(
                errores,
                f"grupo_sin_dias_{grupo.pk}",
                (
                    f"El grupo {_rotulo_grupo(grupo)} del CEF {grupo.cueanexo} "
                    "está activo pero no posee días de funcionamiento."
                ),
                grupo.cueanexo,
            )
        dias_por_id = defaultdict(list)
        for dia in dias:
            dias_por_id[dia.dia_semana_id].append(dia)
            numero_dia = getattr(dia.dia_semana, "numero", None)
            if not dia.dia_semana_id or numero_dia not in range(1, 8):
                invalidos_grupos.add(grupo.pk)
                _agregar_detalle(
                    errores,
                    f"grupo_dia_invalido_{grupo.pk}_{dia.pk}",
                    f"El grupo {_rotulo_grupo(grupo)} contiene un día de funcionamiento inválido.",
                    grupo.cueanexo,
                )
        for dia_id, coincidencias in dias_por_id.items():
            if len(coincidencias) > 1:
                invalidos_grupos.add(grupo.pk)
                _agregar_detalle(
                    errores,
                    f"grupo_dia_duplicado_{grupo.pk}_{dia_id}",
                    f"El grupo {_rotulo_grupo(grupo)} posee un día de funcionamiento duplicado.",
                    grupo.cueanexo,
                )
        dias_validos_por_grupo[grupo.pk] = dias
    for clave, coincidencias in grupos_por_clave.items():
        if len(coincidencias) > 1:
            invalidos_grupos |= {grupo.pk for grupo in coincidencias}
            cue = clave[0]
            _agregar_detalle(
                errores,
                f"grupo_duplicado_{cue}_{clave[1]}_{clave[2]}",
                (
                    f"El CEF {cue} posee más de un grupo activo con la misma "
                    "actividad y número."
                ),
                cue,
            )
    grupos_validos = [
        grupo for grupo in grupos_activos if grupo.pk not in invalidos_grupos
    ]
    grupos_validos_ids = {grupo.pk for grupo in grupos_validos}
    dias_validos = [
        dia
        for grupo in grupos_validos
        for dia in dias_validos_por_grupo.get(grupo.pk, [])
    ]
    for grupo in grupos_validos:
        contar(grupo.cueanexo, "grupos", proyectables=1)
        contar(
            grupo.cueanexo,
            "dias",
            proyectables=len(dias_validos_por_grupo.get(grupo.pk, [])),
        )
    resultado["totales"]["grupos"]["encontrados"] = len(grupos_activos)
    resultado["totales"]["grupos"]["proyectables"] = len(grupos_validos)
    resultado["totales"]["dias"]["encontrados"] = sum(
        len(grupo.dias_prevalidacion) for grupo in grupos_activos
    )
    resultado["totales"]["dias"]["proyectables"] = len(dias_validos)
    resultado["proyeccion"]["grupos_origen_ids"] = [
        grupo.pk for grupo in grupos_validos
    ]
    resultado["proyeccion"]["grupos"] = [
        {
            "grupo_origen_id": grupo.pk,
            "cueanexo": grupo.cueanexo,
            "rotulo_origen": _rotulo_grupo(grupo),
            "anio_origen": ciclo_origen.anio,
            "anio_destino": destino_anio,
            "turno_origen_id": grupo.turno_id,
        }
        for grupo in grupos_validos
    ]
    resultado["proyeccion"]["dias_origen_ids"] = [dia.pk for dia in dias_validos]

    alumnos_por_clave = defaultdict(list)
    invalidos_alumnos = set()
    for alumno in alumnos:
        contar(alumno.cueanexo, "alumnos", encontrados=1)
        cue = _cue_normalizado_valido(alumno.cueanexo)
        if not cue:
            invalidos_alumnos.add(alumno.pk)
            _agregar_detalle(
                errores,
                f"alumno_cue_invalido_{alumno.pk}",
                "Existe un período activo de alumno con CUE-Anexo inválido.",
                alumno.cueanexo,
            )
        alumnos_por_clave[(cue or str(alumno.cueanexo), alumno.alumno_id)].append(alumno)
    for clave, coincidencias in alumnos_por_clave.items():
        if len(coincidencias) > 1:
            invalidos_alumnos |= {item.pk for item in coincidencias}
            cue = clave[0]
            nombre = coincidencias[0].alumno_nombre_snapshot or "Alumno sin nombre disponible"
            _agregar_detalle(
                errores,
                f"alumno_activo_duplicado_{cue}_{clave[1]}",
                f"El alumno {nombre} posee más de un período activo en el CEF {cue}.",
                cue,
            )
    alumnos_validos = [item for item in alumnos if item.pk not in invalidos_alumnos]
    bancos_alumno_validos = {
        (item.cueanexo, item.alumno_id): item for item in alumnos_validos
    }
    for alumno in alumnos_validos:
        contar(alumno.cueanexo, "alumnos", proyectables=1)
    resultado["totales"]["alumnos"]["encontrados"] = len(alumnos)
    resultado["totales"]["alumnos"]["proyectables"] = len(alumnos_validos)
    resultado["proyeccion"]["alumnos_origen_ids"] = [
        item.pk for item in alumnos_validos
    ]

    docentes_por_clave = defaultdict(list)
    invalidos_docentes = set()
    for docente in docentes:
        contar(docente.cueanexo, "docentes", encontrados=1)
        cue = _cue_normalizado_valido(docente.cueanexo)
        cuil = solo_digitos(docente.docente_cuil)
        if not cue:
            invalidos_docentes.add(docente.pk)
            _agregar_detalle(
                errores,
                f"docente_cue_invalido_{docente.pk}",
                "Existe un período activo de profesor con CUE-Anexo inválido.",
                docente.cueanexo,
            )
        if len(cuil) != 11 or cuil != docente.docente_cuil:
            invalidos_docentes.add(docente.pk)
            _agregar_detalle(
                errores,
                f"docente_cuil_invalido_{docente.pk}",
                (
                    f"El profesor {docente.docente_nombre_snapshot or docente.docente_cuil} "
                    "posee un CUIL no normalizado o inválido."
                ),
                docente.cueanexo,
            )
        docentes_por_clave[(cue or str(docente.cueanexo), cuil)].append(docente)
    for clave, coincidencias in docentes_por_clave.items():
        if len(coincidencias) > 1:
            invalidos_docentes |= {item.pk for item in coincidencias}
            cue, cuil = clave
            nombre = coincidencias[0].docente_nombre_snapshot or cuil
            _agregar_detalle(
                errores,
                f"docente_activo_duplicado_{cue}_{cuil}",
                f"El profesor {nombre} posee más de un período activo en el CEF {cue}.",
                cue,
            )
    docentes_validos = [item for item in docentes if item.pk not in invalidos_docentes]
    bancos_docente_validos = {
        (item.cueanexo, item.docente_cuil): item for item in docentes_validos
    }
    for docente in docentes_validos:
        contar(docente.cueanexo, "docentes", proyectables=1)
    resultado["totales"]["docentes"]["encontrados"] = len(docentes)
    resultado["totales"]["docentes"]["proyectables"] = len(docentes_validos)
    resultado["proyeccion"]["docentes_origen_ids"] = [
        item.pk for item in docentes_validos
    ]

    invalidas_inscripciones = set()
    inscripciones_por_clave = defaultdict(list)
    for inscripcion in inscripciones:
        grupo = grupos_por_id[inscripcion.grupo_id]
        contar(grupo.cueanexo, "inscripciones", encontrados=1)
        inscripciones_por_clave[(inscripcion.grupo_id, inscripcion.alumno_id)].append(
            inscripcion
        )
        banco = bancos_alumno_validos.get((grupo.cueanexo, inscripcion.alumno_id))
        nombre = _nombre_alumno(inscripcion, banco)
        if grupo.estado != CefGrupo.Estado.ACTIVO:
            invalidas_inscripciones.add(inscripcion.pk)
            _agregar_detalle(
                errores,
                f"inscripcion_activa_grupo_baja_{inscripcion.pk}",
                (
                    f"El alumno {nombre} tiene una inscripción activa en "
                    f"{_rotulo_grupo(grupo)}, pero el grupo está en baja."
                ),
                grupo.cueanexo,
            )
        elif grupo.pk not in grupos_validos_ids:
            invalidas_inscripciones.add(inscripcion.pk)
        if banco is None:
            invalidas_inscripciones.add(inscripcion.pk)
            _agregar_detalle(
                errores,
                f"inscripcion_sin_banco_{inscripcion.pk}",
                (
                    f"El alumno {nombre} tiene una inscripción activa en "
                    f"{_rotulo_grupo(grupo)} pero no posee un período activo "
                    f"en el banco del CEF {grupo.cueanexo} para el ciclo {ciclo_origen.anio}."
                ),
                grupo.cueanexo,
            )
    for clave, coincidencias in inscripciones_por_clave.items():
        if len(coincidencias) > 1:
            invalidas_inscripciones |= {item.pk for item in coincidencias}
            grupo = grupos_por_id[clave[0]]
            nombre = _nombre_alumno(coincidencias[0])
            _agregar_detalle(
                errores,
                f"inscripcion_activa_duplicada_{clave[0]}_{clave[1]}",
                (
                    f"El alumno {nombre} posee más de una inscripción activa "
                    f"en {_rotulo_grupo(grupo)}."
                ),
                grupo.cueanexo,
            )

    candidatas_conflicto = [
        item for item in inscripciones if item.pk not in invalidas_inscripciones
    ]
    por_alumno_cef = defaultdict(list)
    for inscripcion in candidatas_conflicto:
        grupo = grupos_por_id[inscripcion.grupo_id]
        por_alumno_cef[(inscripcion.alumno_id, grupo.cueanexo)].append(inscripcion)
    for clave, relaciones in sorted(por_alumno_cef.items(), key=lambda item: item[0]):
        relaciones = sorted(relaciones, key=lambda item: (item.grupo_id, item.pk))
        for indice, inscripcion_a in enumerate(relaciones):
            grupo_a = grupos_por_id[inscripcion_a.grupo_id]
            dias_a = {
                dia.dia_semana_id
                for dia in dias_validos_por_grupo.get(grupo_a.pk, [])
            }
            for inscripcion_b in relaciones[indice + 1:]:
                grupo_b = grupos_por_id[inscripcion_b.grupo_id]
                if grupo_a.pk == grupo_b.pk:
                    continue
                if grupo_a.actividad_id == grupo_b.actividad_id:
                    continue
                dias_b = {
                    dia.dia_semana_id
                    for dia in dias_validos_por_grupo.get(grupo_b.pk, [])
                }
                if not dias_a.intersection(dias_b):
                    continue
                if not _superponen_horarios(grupo_a, grupo_b):
                    continue
                invalidas_inscripciones.add(inscripcion_a.pk)
                invalidas_inscripciones.add(inscripcion_b.pk)
                banco = bancos_alumno_validos.get((clave[1], clave[0]))
                nombre = _nombre_alumno(inscripcion_a, banco)
                _agregar_detalle(
                    errores,
                    (
                        f"conflicto_horario_{clave[1]}_{clave[0]}_"
                        f"{min(grupo_a.pk, grupo_b.pk)}_{max(grupo_a.pk, grupo_b.pk)}"
                    ),
                    (
                        f"El alumno {nombre} tendría un conflicto horario en el CEF "
                        f"{clave[1]} entre {_rotulo_grupo(grupo_a)} y "
                        f"{_rotulo_grupo(grupo_b)}."
                    ),
                    clave[1],
                )
    inscripciones_validas = [
        item for item in inscripciones if item.pk not in invalidas_inscripciones
    ]
    for inscripcion in inscripciones_validas:
        contar(inscripcion.grupo.cueanexo, "inscripciones", proyectables=1)
    resultado["totales"]["inscripciones"]["encontrados"] = len(inscripciones)
    resultado["totales"]["inscripciones"]["proyectables"] = len(
        inscripciones_validas
    )
    resultado["proyeccion"]["inscripciones_origen_ids"] = [
        item.pk for item in inscripciones_validas
    ]

    invalidas_asignaciones = set()
    asignaciones_por_docente = defaultdict(list)
    asignaciones_por_rol = defaultdict(list)
    roles_validos = {valor for valor, _ in CefDocenteGrupo.Rol.choices}
    for asignacion in asignaciones:
        grupo = grupos_por_id[asignacion.grupo_id]
        contar(grupo.cueanexo, "asignaciones", encontrados=1)
        cuil = solo_digitos(asignacion.docente_cuil)
        asignaciones_por_docente[(grupo.pk, cuil)].append(asignacion)
        asignaciones_por_rol[(grupo.pk, asignacion.rol)].append(asignacion)
        nombre = asignacion.docente_nombre_snapshot or asignacion.docente_cuil
        if grupo.estado != CefGrupo.Estado.ACTIVO:
            invalidas_asignaciones.add(asignacion.pk)
            _agregar_detalle(
                errores,
                f"asignacion_activa_grupo_baja_{asignacion.pk}",
                (
                    f"El profesor {nombre} posee una asignación activa en "
                    f"{_rotulo_grupo(grupo)}, pero el grupo está en baja."
                ),
                grupo.cueanexo,
            )
        elif grupo.pk not in grupos_validos_ids:
            invalidas_asignaciones.add(asignacion.pk)
        if len(cuil) != 11 or cuil != asignacion.docente_cuil:
            invalidas_asignaciones.add(asignacion.pk)
            _agregar_detalle(
                errores,
                f"asignacion_cuil_invalido_{asignacion.pk}",
                f"La asignación activa de {nombre} posee un CUIL inválido.",
                grupo.cueanexo,
            )
        if (grupo.cueanexo, cuil) not in bancos_docente_validos:
            invalidas_asignaciones.add(asignacion.pk)
            _agregar_detalle(
                errores,
                f"asignacion_sin_banco_{asignacion.pk}",
                (
                    f"El profesor {nombre} está asignado activamente a "
                    f"{_rotulo_grupo(grupo)} pero no posee un período activo "
                    f"en el banco del CEF {grupo.cueanexo} para el ciclo {ciclo_origen.anio}."
                ),
                grupo.cueanexo,
            )
        if asignacion.rol not in roles_validos:
            invalidas_asignaciones.add(asignacion.pk)
            _agregar_detalle(
                errores,
                f"asignacion_rol_invalido_{asignacion.pk}",
                (
                    f"La asignación activa de {nombre} en {_rotulo_grupo(grupo)} "
                    f'posee el rol inválido "{asignacion.rol}".'
                ),
                grupo.cueanexo,
            )
    for clave, coincidencias in asignaciones_por_docente.items():
        if len(coincidencias) > 1:
            invalidas_asignaciones |= {item.pk for item in coincidencias}
            grupo = grupos_por_id[clave[0]]
            nombre = coincidencias[0].docente_nombre_snapshot or clave[1]
            _agregar_detalle(
                errores,
                f"asignacion_docente_duplicado_{clave[0]}_{clave[1]}",
                (
                    f"El profesor {nombre} posee más de una asignación activa "
                    f"en {_rotulo_grupo(grupo)}."
                ),
                grupo.cueanexo,
            )
    for clave, coincidencias in asignaciones_por_rol.items():
        if len(coincidencias) > 1:
            invalidas_asignaciones |= {item.pk for item in coincidencias}
            grupo = grupos_por_id[clave[0]]
            rol = dict(CefDocenteGrupo.Rol.choices).get(clave[1], clave[1])
            _agregar_detalle(
                errores,
                f"asignacion_rol_duplicado_{clave[0]}_{clave[1]}",
                (
                    f"El grupo {_rotulo_grupo(grupo)} posee más de un profesor "
                    f"activo con el rol {rol}."
                ),
                grupo.cueanexo,
            )
    asignaciones_validas = [
        item for item in asignaciones if item.pk not in invalidas_asignaciones
    ]
    for asignacion in asignaciones_validas:
        contar(asignacion.grupo.cueanexo, "asignaciones", proyectables=1)
    resultado["totales"]["asignaciones"]["encontrados"] = len(asignaciones)
    resultado["totales"]["asignaciones"]["proyectables"] = len(
        asignaciones_validas
    )
    resultado["proyeccion"]["asignaciones_origen_ids"] = [
        item.pk for item in asignaciones_validas
    ]

    inventario_por_clave = defaultdict(list)
    invalidos_inventario = set()
    invalidas_distribuciones = set()
    distribuciones = []
    for item in inventario:
        contar(item.cueanexo, "inventario_materiales", encontrados=1)
        cue = _cue_normalizado_valido(item.cueanexo)
        if not cue:
            invalidos_inventario.add(item.pk)
            _agregar_detalle(
                errores,
                f"inventario_cue_invalido_{item.pk}",
                "Existe una cabecera de inventario con CUE-Anexo inválido.",
                item.cueanexo,
            )
        inventario_por_clave[(cue or str(item.cueanexo), item.material_id)].append(item)
        estados_por_id = defaultdict(list)
        for distribucion in item.distribuciones_prevalidacion:
            distribuciones.append(distribucion)
            contar(item.cueanexo, "inventario_distribuciones", encontrados=1)
            estados_por_id[distribucion.estado_id].append(distribucion)
            material = item.material_nombre_snapshot or item.material.nombre
            if distribucion.estado_id is None:
                invalidas_distribuciones.add(distribucion.pk)
                invalidos_inventario.add(item.pk)
                _agregar_detalle(
                    errores,
                    f"inventario_estado_legacy_{distribucion.pk}",
                    (
                        f'El material "{material}" del CEF {item.cueanexo} posee una '
                        "distribución legacy sin estado de catálogo reconstruible."
                    ),
                    item.cueanexo,
                )
            elif not str(distribucion.estado.nombre or "").strip():
                invalidas_distribuciones.add(distribucion.pk)
                invalidos_inventario.add(item.pk)
                _agregar_detalle(
                    errores,
                    f"inventario_estado_incoherente_{distribucion.pk}",
                    (
                        f'El material "{material}" del CEF {item.cueanexo} referencia '
                        "un estado de catálogo sin nombre."
                    ),
                    item.cueanexo,
                )
            if distribucion.cantidad is None or distribucion.cantidad <= 0:
                invalidas_distribuciones.add(distribucion.pk)
                invalidos_inventario.add(item.pk)
                _agregar_detalle(
                    errores,
                    f"inventario_cantidad_invalida_{distribucion.pk}",
                    (
                        f'El material "{material}" del CEF {item.cueanexo} posee '
                        "una distribución con cantidad no positiva."
                    ),
                    item.cueanexo,
                )
        for estado_id, coincidencias in estados_por_id.items():
            if estado_id is not None and len(coincidencias) > 1:
                invalidas_distribuciones |= {item.pk for item in coincidencias}
                invalidos_inventario.add(item.pk)
                material = item.material_nombre_snapshot or item.material.nombre
                _agregar_detalle(
                    errores,
                    f"inventario_estado_duplicado_{item.pk}_{estado_id}",
                    (
                        f'El material "{material}" del CEF {item.cueanexo} posee '
                        "el mismo estado de catálogo más de una vez."
                    ),
                    item.cueanexo,
                )
    for clave, coincidencias in inventario_por_clave.items():
        if len(coincidencias) > 1:
            invalidos_inventario |= {item.pk for item in coincidencias}
            cue = clave[0]
            material = coincidencias[0].material_nombre_snapshot or coincidencias[0].material.nombre
            _agregar_detalle(
                errores,
                f"inventario_material_duplicado_{cue}_{clave[1]}",
                f'El material "{material}" está duplicado en el inventario del CEF {cue}.',
                cue,
            )
    inventario_valido = [item for item in inventario if item.pk not in invalidos_inventario]
    inventario_valido_ids = {item.pk for item in inventario_valido}
    distribuciones_validas = [
        item
        for item in distribuciones
        if item.pk not in invalidas_distribuciones
        and item.inventario_material_id in inventario_valido_ids
    ]
    for item in inventario_valido:
        contar(item.cueanexo, "inventario_materiales", proyectables=1)
    inventario_por_id = {item.pk: item for item in inventario}
    for distribucion in distribuciones_validas:
        cabecera = inventario_por_id[distribucion.inventario_material_id]
        contar(cabecera.cueanexo, "inventario_distribuciones", proyectables=1)
    resultado["totales"]["inventario_materiales"]["encontrados"] = len(inventario)
    resultado["totales"]["inventario_materiales"]["proyectables"] = len(
        inventario_valido
    )
    resultado["totales"]["inventario_distribuciones"]["encontrados"] = len(
        distribuciones
    )
    resultado["totales"]["inventario_distribuciones"]["proyectables"] = len(
        distribuciones_validas
    )
    resultado["proyeccion"]["inventario_materiales_origen_ids"] = [
        item.pk for item in inventario_valido
    ]
    resultado["proyeccion"]["inventario_distribuciones_origen_ids"] = [
        item.pk for item in distribuciones_validas
    ]

    if not grupos_activos:
        _agregar_detalle(
            advertencias,
            "origen_sin_grupos_activos",
            f"El ciclo {ciclo_origen.anio} no posee grupos activos para proyectar.",
        )
    cues_con_relevamiento = {
        item.cueanexo for item in relevamientos if _cue_normalizado_valido(item.cueanexo)
    }
    for cue in sorted(por_cef):
        if not _cue_normalizado_valido(cue):
            continue
        if cue not in cues_con_relevamiento:
            _agregar_detalle(
                advertencias,
                f"cef_sin_relevamiento_{cue}",
                f"El CEF {cue} no posee datos adicionales en el ciclo origen.",
                cue,
            )

    errores.sort(key=lambda item: (item["cueanexo"], item["codigo"], item["mensaje"]))
    advertencias.sort(
        key=lambda item: (item["cueanexo"], item["codigo"], item["mensaje"])
    )
    resultado["por_cef"] = [por_cef[cue] for cue in sorted(por_cef)]
    resultado["cantidad_cueanexos"] = sum(
        1 for cue in por_cef if _cue_normalizado_valido(cue)
    )
    resultado["totales"]["errores"] = len(errores)
    resultado["totales"]["advertencias"] = len(advertencias)
    for categoria in resultado["categorias"]:
        categoria["total"] = resultado["totales"][categoria["clave"]]
    resultado["bloqueado"] = bool(errores)
    return resultado


def _objetos_proyectados(modelo, ids, *select_related):
    queryset = modelo.objects.filter(pk__in=ids).order_by("pk")
    if select_related:
        queryset = queryset.select_related(*select_related)
    return list(queryset)


def _bulk_create_con_mapa(modelo, origenes, construir):
    nuevos = [construir(origen) for origen in origenes]
    if nuevos:
        modelo.objects.bulk_create(nuevos)
    return {
        origen.pk: nuevo
        for origen, nuevo in zip(origenes, nuevos)
    }


def _mensaje_prevalidacion_bloqueada(resultado):
    mensajes = [item["mensaje"] for item in resultado.get("errores", [])]
    detalle = " ".join(mensajes[:3])
    if len(mensajes) > 3:
        detalle = f"{detalle} Hay {len(mensajes) - 3} inconsistencias adicionales."
    return detalle or "La prevalidación anual detectó inconsistencias bloqueantes."


def generar_ciclo_siguiente(ciclo_origen, user):
    """Genera N+1 de forma atómica a partir del último ciclo ya cerrado."""

    ciclo_origen_id = getattr(ciclo_origen, "pk", ciclo_origen)
    if not ciclo_origen_id:
        raise ValidationError("El ciclo origen no es válido.")

    try:
        with transaction.atomic():
            origen = (
                CefCiclo.objects.select_for_update()
                .filter(pk=ciclo_origen_id)
                .first()
            )
            if origen is None:
                raise ValidationError("El ciclo origen no existe.")
            if not origen.cerrado:
                raise ValidationError(
                    f"El ciclo {origen.anio} aún está abierto. Cerralo antes de "
                    f"generar el ciclo {origen.anio + 1}."
                )
            if origen.actual:
                raise ValidationError(
                    "Un ciclo cerrado no puede continuar marcado como ciclo actual."
                )

            resultado = prevalidar_generacion_anual(origen)
            if resultado["bloqueado"]:
                raise ValidationError(_mensaje_prevalidacion_bloqueada(resultado))

            fecha_generacion = timezone.localdate()
            destino_anio = origen.anio + 1

            # La marca de actual se aplica al terminar toda la copia, dentro de
            # esta misma transacción.
            destino = CefCiclo.objects.create(
                anio=destino_anio,
                descripcion="",
                fecha_inicio=None,
                fecha_fin=None,
                activo=True,
                actual=False,
                cerrado=False,
                creado_por=user,
                actualizado_por=user,
            )

            proyeccion = resultado["proyeccion"]

            turnos_origen = _objetos_proyectados(
                CefTurno,
                proyeccion["turnos_origen_ids"],
            )
            turnos_mapa = _bulk_create_con_mapa(
                CefTurno,
                turnos_origen,
                lambda item: CefTurno(
                    ciclo=destino,
                    nombre=item.nombre,
                    hora_desde_referencia=item.hora_desde_referencia,
                    hora_hasta_referencia=item.hora_hasta_referencia,
                    activo=item.activo,
                    orden=item.orden,
                    creado_por=user,
                    actualizado_por=user,
                ),
            )

            relevamientos_origen = _objetos_proyectados(
                CefDatosRelevamiento,
                proyeccion["datos_relevamiento_origen_ids"],
            )
            relevamientos_nuevos = [
                CefDatosRelevamiento(
                    ciclo=destino,
                    cueanexo=item.cueanexo,
                    beneficio_alimentario_gratuito_id=(
                        item.beneficio_alimentario_gratuito_id
                    ),
                    fuente_financiamiento_id=item.fuente_financiamiento_id,
                    prestacion_tipo_id=item.prestacion_tipo_id,
                    espacio_comedor_id=item.espacio_comedor_id,
                    c_orientacion_id=item.c_orientacion_id,
                    observaciones=item.observaciones,
                    beneficio_codigo_snapshot=item.beneficio_codigo_snapshot,
                    beneficio_nombre_snapshot=item.beneficio_nombre_snapshot,
                    fuente_codigo_snapshot=item.fuente_codigo_snapshot,
                    fuente_nombre_snapshot=item.fuente_nombre_snapshot,
                    prestacion_codigo_snapshot=item.prestacion_codigo_snapshot,
                    prestacion_nombre_snapshot=item.prestacion_nombre_snapshot,
                    espacio_comedor_codigo_snapshot=(
                        item.espacio_comedor_codigo_snapshot
                    ),
                    espacio_comedor_nombre_snapshot=(
                        item.espacio_comedor_nombre_snapshot
                    ),
                    orientacion_codigo_snapshot=item.orientacion_codigo_snapshot,
                    orientacion_nombre_snapshot=item.orientacion_nombre_snapshot,
                    creado_por=user,
                    actualizado_por=user,
                )
                for item in relevamientos_origen
            ]
            CefDatosRelevamiento.objects.bulk_create(relevamientos_nuevos)

            grupos_origen = _objetos_proyectados(
                CefGrupo,
                proyeccion["grupos_origen_ids"],
            )
            grupos_mapa = _bulk_create_con_mapa(
                CefGrupo,
                grupos_origen,
                lambda item: CefGrupo(
                    cueanexo=item.cueanexo,
                    ciclo=destino,
                    actividad_id=item.actividad_id,
                    numero=item.numero,
                    nombre=item.nombre,
                    nivel_id=item.nivel_id,
                    rango_etario_id=item.rango_etario_id,
                    turno=turnos_mapa[item.turno_id],
                    hora_inicio=item.hora_inicio,
                    hora_fin=item.hora_fin,
                    cupo_maximo=item.cupo_maximo,
                    estado=CefGrupo.Estado.ACTIVO,
                    fecha_baja=None,
                    motivo_baja="",
                    grupo_origen=item,
                    codigo_ra_override_id=item.codigo_ra_override_id,
                    motivo_codigo_ra_override=item.motivo_codigo_ra_override,
                    actividad_nombre_snapshot=item.actividad_nombre_snapshot,
                    eje_nombre_snapshot=item.eje_nombre_snapshot,
                    codigo_ra_snapshot=item.codigo_ra_snapshot,
                    codigo_ra_descripcion_snapshot=(
                        item.codigo_ra_descripcion_snapshot
                    ),
                    turno_nombre_snapshot=item.turno_nombre_snapshot,
                    turno_hora_desde_snapshot=item.turno_hora_desde_snapshot,
                    turno_hora_hasta_snapshot=item.turno_hora_hasta_snapshot,
                    nivel_nombre_snapshot=item.nivel_nombre_snapshot,
                    rango_etario_nombre_snapshot=item.rango_etario_nombre_snapshot,
                    observaciones=item.observaciones,
                    creado_por=user,
                    actualizado_por=user,
                ),
            )

            dias_origen = _objetos_proyectados(
                CefGrupoDiaFuncionamiento,
                proyeccion["dias_origen_ids"],
            )
            dias_nuevos = [
                CefGrupoDiaFuncionamiento(
                    grupo=grupos_mapa[item.grupo_id],
                    dia_semana_id=item.dia_semana_id,
                    observaciones=item.observaciones,
                    creado_por=user,
                    actualizado_por=user,
                )
                for item in dias_origen
            ]
            CefGrupoDiaFuncionamiento.objects.bulk_create(dias_nuevos)

            alumnos_origen = _objetos_proyectados(
                CefAlumnoCef,
                proyeccion["alumnos_origen_ids"],
            )
            alumnos_nuevos = [
                CefAlumnoCef(
                    cueanexo=item.cueanexo,
                    ciclo=destino,
                    alumno_id=item.alumno_id,
                    estado=CefAlumnoCef.Estado.ACTIVO,
                    fecha_alta=fecha_generacion,
                    fecha_baja=None,
                    motivo_baja="",
                    alumno_nombre_snapshot=item.alumno_nombre_snapshot,
                    alumno_documento_snapshot=item.alumno_documento_snapshot,
                    alumno_cuil_snapshot=item.alumno_cuil_snapshot,
                    observaciones=item.observaciones,
                    creado_por=user,
                    actualizado_por=user,
                )
                for item in alumnos_origen
            ]
            CefAlumnoCef.objects.bulk_create(alumnos_nuevos)

            docentes_origen = _objetos_proyectados(
                CefDocenteCef,
                proyeccion["docentes_origen_ids"],
            )
            docentes_nuevos = [
                CefDocenteCef(
                    cueanexo=item.cueanexo,
                    ciclo=destino,
                    docente_cuil=item.docente_cuil,
                    estado=CefDocenteCef.Estado.ACTIVO,
                    fecha_alta=fecha_generacion,
                    fecha_baja=None,
                    motivo_baja="",
                    docente_nombre_snapshot=item.docente_nombre_snapshot,
                    docente_dni_snapshot=item.docente_dni_snapshot,
                    docente_estado_bnh_snapshot=item.docente_estado_bnh_snapshot,
                    observaciones=item.observaciones,
                    creado_por=user,
                    actualizado_por=user,
                )
                for item in docentes_origen
            ]
            CefDocenteCef.objects.bulk_create(docentes_nuevos)

            inscripciones_origen = _objetos_proyectados(
                CefInscripcion,
                proyeccion["inscripciones_origen_ids"],
            )
            inscripciones_nuevas = [
                CefInscripcion(
                    grupo=grupos_mapa[item.grupo_id],
                    alumno_id=item.alumno_id,
                    estado=CefInscripcion.Estado.ACTIVO,
                    fecha_inscripcion=fecha_generacion,
                    fecha_baja=None,
                    motivo_baja="",
                    observaciones=item.observaciones,
                    creado_por=user,
                    actualizado_por=user,
                )
                for item in inscripciones_origen
            ]
            CefInscripcion.objects.bulk_create(inscripciones_nuevas)

            asignaciones_origen = _objetos_proyectados(
                CefDocenteGrupo,
                proyeccion["asignaciones_origen_ids"],
            )
            asignaciones_nuevas = [
                CefDocenteGrupo(
                    grupo=grupos_mapa[item.grupo_id],
                    docente_cuil=item.docente_cuil,
                    rol=item.rol,
                    estado=CefDocenteGrupo.Estado.ACTIVO,
                    fecha_desde=fecha_generacion,
                    fecha_hasta=None,
                    motivo_baja="",
                    docente_nombre_snapshot=item.docente_nombre_snapshot,
                    docente_dni_snapshot=item.docente_dni_snapshot,
                    docente_estado_bnh_snapshot=item.docente_estado_bnh_snapshot,
                    observaciones=item.observaciones,
                    creado_por=user,
                    actualizado_por=user,
                )
                for item in asignaciones_origen
            ]
            CefDocenteGrupo.objects.bulk_create(asignaciones_nuevas)

            inventario_origen = _objetos_proyectados(
                CefInventarioMaterial,
                proyeccion["inventario_materiales_origen_ids"],
            )
            inventario_mapa = _bulk_create_con_mapa(
                CefInventarioMaterial,
                inventario_origen,
                lambda item: CefInventarioMaterial(
                    cueanexo=item.cueanexo,
                    ciclo=destino,
                    material_id=item.material_id,
                    cantidad=item.cantidad,
                    estado_descripcion=item.estado_descripcion,
                    material_nombre_snapshot=item.material_nombre_snapshot,
                    observaciones=item.observaciones,
                    creado_por=user,
                    actualizado_por=user,
                ),
            )

            distribuciones_origen = _objetos_proyectados(
                CefInventarioMaterialEstado,
                proyeccion["inventario_distribuciones_origen_ids"],
            )
            distribuciones_nuevas = [
                CefInventarioMaterialEstado(
                    inventario_material=inventario_mapa[
                        item.inventario_material_id
                    ],
                    estado_id=item.estado_id,
                    estado_descripcion=item.estado_descripcion,
                    estado_normalizado=item.estado_normalizado,
                    cantidad=item.cantidad,
                    creado_por=user,
                    actualizado_por=user,
                )
                for item in distribuciones_origen
            ]
            CefInventarioMaterialEstado.objects.bulk_create(
                distribuciones_nuevas
            )

            destino.actual = True
            destino.actualizado_por = user
            destino.save(
                update_fields=[
                    "actual",
                    "actualizado_por",
                    "actualizado_en",
                ]
            )

            conteos = {
                "cef": resultado["cantidad_cueanexos"],
                "turnos": len(turnos_origen),
                "datos_relevamiento": len(relevamientos_origen),
                "grupos": len(grupos_origen),
                "dias": len(dias_origen),
                "alumnos": len(alumnos_origen),
                "docentes": len(docentes_origen),
                "inscripciones": len(inscripciones_origen),
                "asignaciones": len(asignaciones_origen),
                "inventario_materiales": len(inventario_origen),
                "inventario_distribuciones": len(distribuciones_origen),
            }
            return {
                "ciclo_origen": origen,
                "ciclo_destino": destino,
                "fecha": fecha_generacion,
                "usuario": user.get_username(),
                "conteos": conteos,
            }
    except IntegrityError as exc:
        raise ValidationError(
            "No se pudo generar el ciclo porque los datos cambiaron durante la operación. "
            "No se realizó ningún cambio."
        ) from exc
