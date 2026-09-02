import datetime
import json
import threading
import time
import uuid

from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db import close_old_connections, connections
from django.db.models.functions import Trim
from django.http import JsonResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from .models import (
    AnalisisSgeRa,
    AuditoriaSgeRa,
    AuditoriaSgeRaEstado,
    FechaActualizacionComparativaSgeRa,
    ResumenSgeRa,
)
from .views_dash import filtrar_queryset_sge, obtener_cargo_usuario, resolver_contexto_sge


TIPOS_SITUACION = {
    'CUE_SIN_DATOS_RA_SGE': 'Sin filas auditadas en RA ni SGE',
    'CUE_SIN_CONTRAPARTE': 'Fuente sin contraparte',
    'NIVELES_DIFERENTES': 'Niveles diferentes',
    'GRADOS_DIFERENTES': 'Grados, años o salas diferentes',
    'SECCIONES_DIFERENTES': 'Secciones diferentes',
    'TURNOS_DIFERENTES': 'Turnos diferentes',
    'TIPOS_SECCION_DIFERENTES': 'Tipos de sección diferentes',
    'MATRICULA_DIFERENTE': 'Matrícula diferente',
    'MATRICULA_NO_UTILIZABLE': 'Matrícula sin información utilizable',
    'REGISTROS_REPETIDOS': 'Registros repetidos',
    'DATO_ESTRUCTURAL_INCOMPLETO': 'Datos estructurales incompletos',
    'ALUMNO_EN_VARIAS_SECCIONES': 'Alumno inscripto en más de una sección en SGE',
}

DIMENSIONES = {
    'COBERTURA_CUE': 'Cobertura del CUE-Anexo',
    'FUENTE': 'Presencia por fuente',
    'NIVEL': 'Nivel',
    'GRADO_ANIO_SALA': 'Grado/Año/Sala',
    'SECCION': 'Sección',
    'TURNO': 'Turno',
    'TIPO_SECCION': 'Tipo de sección',
    'MATRICULA': 'Matrícula',
}

COMPARABILIDADES = {
    'COMPARABLE': 'Comparación directa',
    'PARCIALMENTE_COMPARABLE': 'Comparación estructural parcial',
    'NO_COMPARABLE': 'Comparación no disponible',
}

COMPARABILIDAD_DESCRIPCIONES = {
    'COMPARABLE': 'Comparación directa.',
    'PARCIALMENTE_COMPARABLE': (
        'Las estructuras informadas son diferentes; por eso no corresponde '
        'comparar entre sí sus matrículas.'
    ),
    'NO_COMPARABLE': 'Con estos datos no puede realizarse una comparación directa.',
}

ACCIONES_REVISION = {
    'VERIFICAR_COBERTURA_FUENTES': (
        'Verificar la cobertura del CUE-Anexo en ambas fuentes dentro del '
        'alcance auditado.'
    ),
    'VERIFICAR_CONTRAPARTE_CUE': (
        'Verificar la presencia del CUE-Anexo en ambas fuentes.'
    ),
    'VERIFICAR_NIVELES': 'Confirmar los niveles informados en ambas fuentes.',
    'VERIFICAR_GRADOS_ANIOS_SALAS': (
        'Confirmar los grados, años o salas informados en ambas fuentes.'
    ),
    'VERIFICAR_SECCIONES': 'Confirmar las secciones informadas en ambas fuentes.',
    'VERIFICAR_TURNOS': 'Confirmar los turnos informados en ambas fuentes.',
    'VERIFICAR_TIPOS_SECCION': (
        'Confirmar los tipos de sección informados en ambas fuentes.'
    ),
    'VERIFICAR_REGISTROS_REPETIDOS': (
        'Revisar los registros repetidos antes de comparar matrícula.'
    ),
    'VERIFICAR_INSCRIPCION_MULTISECCION': (
        'Revisar la inscripción SGE y confirmar cuál de las secciones '
        'asociadas corresponde.'
    ),
    'VERIFICAR_MATRICULA_INFORMADA': (
        'Verificar la matrícula no utilizable antes de realizar la comparación.'
    ),
    'VERIFICAR_MATRICULA': (
        'Confirmar la matrícula correspondiente a la misma estructura en ambas '
        'fuentes.'
    ),
    'COMPLETAR_NIVEL': 'Verificar y completar el nivel faltante.',
    'COMPLETAR_GRADO_ANIO_SALA': (
        'Verificar y completar el grado, año o sala faltante.'
    ),
    'COMPLETAR_SECCION': 'Verificar y completar la sección faltante.',
    'COMPLETAR_TURNO': 'Verificar y completar el turno faltante.',
    'COMPLETAR_TIPO_SECCION': (
        'Verificar y completar el tipo de sección faltante.'
    ),
}

ESTADOS_FILTRO = {'con_situaciones', 'todos', 'sin_diferencias'}
SITUACION_FIELDS = (
    'id',
    'cueanexo',
    'tipo_situacion',
    'orden',
    'contexto_nivel',
    'contexto_grado',
    'contexto_seccion',
    'contexto_turno',
    'contexto_tipo_secc',
    'titulo',
    'valor_ra',
    'valor_sge',
    'mensaje',
    'detalle',
    'bloquea_revision',
    'motivo_bloqueo',
    'dimension_codigo',
    'categoria_operativa',
    'comparabilidad_codigo',
    'resumen_diferencia',
    'accion_revision_codigo',
    'periodo_ra',
    'periodo_sge',
    'valor_ra_tipo',
    'valor_sge_tipo',
    'valor_ra_numero',
    'valor_sge_numero',
    'diferencia_absoluta',
    'diferencia_sge_menos_ra',
    'comparacion_confiable',
    'motivo_no_comparable_codigo',
    'causa_sin_datos_codigo',
    'detalle_version',
)

ANALISIS_FIELDS = (
    'id',
    'sistema',
    'nivel',
    'grado',
    'seccion',
    'turno',
    'tipo_secc',
    'total',
)

RESUMEN_FIELDS = (
    'cueanexo',
    'escuela',
    'region',
    'estado_actual',
    'cantidad_situaciones_total',
    'cantidad_bloqueos_total',
    'situaciones_por_tipo',
    'bloqueos_por_tipo',
    'estado_codigo',
    'estado',
)

ESTRUCTURA_FIELDS = ('nivel', 'grado', 'seccion', 'turno', 'tipo_secc')
CONTEXTO_FIELDS = {
    'nivel': 'contexto_nivel',
    'grado': 'contexto_grado',
    'seccion': 'contexto_seccion',
    'turno': 'contexto_turno',
    'tipo_secc': 'contexto_tipo_secc',
}
DIMENSION_FIELDS = {
    'NIVEL': 'nivel',
    'GRADO_ANIO_SALA': 'grado',
    'SECCION': 'seccion',
    'TURNO': 'turno',
    'TIPO_SECCION': 'tipo_secc',
    'MATRICULA': 'matricula',
}
TIPO_DIMENSIONES = {
    'NIVELES_DIFERENTES': 'NIVEL',
    'GRADOS_DIFERENTES': 'GRADO_ANIO_SALA',
    'SECCIONES_DIFERENTES': 'SECCION',
    'TURNOS_DIFERENTES': 'TURNO',
    'TIPOS_SECCION_DIFERENTES': 'TIPO_SECCION',
    'MATRICULA_DIFERENTE': 'MATRICULA',
    'MATRICULA_NO_UTILIZABLE': 'MATRICULA',
    'REGISTROS_REPETIDOS': 'ESTRUCTURA',
    'DATO_ESTRUCTURAL_INCOMPLETO': 'ESTRUCTURA',
}
CAMPOS_DATO_ESTRUCTURAL_INCOMPLETO = {
    'COMPLETAR_NIVEL': 'nivel',
    'COMPLETAR_GRADO_ANIO_SALA': 'grado',
    'COMPLETAR_SECCION': 'seccion',
    'COMPLETAR_TURNO': 'turno',
    'COMPLETAR_TIPO_SECCION': 'tipo_secc',
}


def _texto(value):
    return '' if value is None else str(value)


def _cueanexo(value):
    return _texto(value).strip()


def _etiqueta_codigo(catalogo, codigo, desconocido):
    if not codigo:
        return ''
    return catalogo.get(codigo, desconocido)


def _etiqueta_fuente(fuente, periodo):
    if periodo is None:
        return fuente
    return f'{fuente} {periodo}'


def _etiqueta_motivo_no_comparable(codigo):
    if not codigo:
        return ''
    return 'Este hallazgo no permite una comparación directa.'


def _etiqueta_causa_sin_datos(codigo, tipo_situacion):
    if tipo_situacion == 'CUE_SIN_DATOS_RA_SGE':
        return 'Sin filas auditadas en RA ni SGE.'
    if not codigo:
        return ''
    return 'No se encontraron filas auditadas para este hallazgo.'


def _etiqueta_bloqueo(codigo):
    if codigo == 'INSCRIPCION_EN_MULTIPLES_SECCIONES':
        return (
            'La inscripción SGE está asociada a varias secciones y requiere '
            'revisión.'
        )
    if codigo == 'CLAVE_HOJA_NO_UNICA':
        return 'Hay más de un registro para la misma estructura.'
    if codigo == 'TOTAL_NO_UTILIZABLE':
        return 'La matrícula debe completarse o corregirse.'
    if codigo and (
        codigo.endswith('_SIN_INFORMACION')
        or codigo.startswith('COMPLETAR_')
    ):
        return 'Falta un dato estructural obligatorio.'
    return 'Hay datos a corregir en esta estructura.'


def _catalogo_tipos_situacion():
    return [
        {'codigo': codigo, 'etiqueta': etiqueta}
        for codigo, etiqueta in TIPOS_SITUACION.items()
    ]


def _parametros_comparativa(request):
    estado = request.GET.get('estado', 'con_situaciones').strip()
    if estado not in ESTADOS_FILTRO:
        estado = 'con_situaciones'

    tipo_situacion = request.GET.get('tipo_situacion', '').strip()
    if tipo_situacion not in TIPOS_SITUACION or estado == 'sin_diferencias':
        tipo_situacion = ''

    return {
        'estado': estado,
        'region': request.GET.get('region', '').strip(),
        'cueanexo': request.GET.get('cueanexo', '').strip(),
        'establecimiento': request.GET.get('establecimiento', '').strip(),
        'tipo_situacion': tipo_situacion,
        'detalle_cueanexo': _cueanexo(request.GET.get('detalle_cueanexo', '')),
    }


def _queryset_resumen_autorizado(contexto_sge):
    queryset = ResumenSgeRa.objects.using('sge_nacion')

    if contexto_sge["alcance"] == "cue":
        cueanexos = contexto_sge.get("cueanexos_permitidos") or []
        if not cueanexos:
            return queryset.none()
        return queryset.filter(cueanexo__in=cueanexos)

    return filtrar_queryset_sge(
        queryset,
        contexto_sge,
        campo_region='region',
        campo_cueanexo='cueanexo',
    )


def _opciones_regiones(queryset):
    regiones = {
        _texto(region).strip()
        for region in queryset.values_list('region', flat=True)
        if _texto(region).strip()
    }
    return sorted(regiones, key=str.casefold)


def _filtrar_resumen(queryset, params, auditoria_valida):
    if params['region']:
        queryset = queryset.filter(region__iexact=params['region'])
    if params['cueanexo']:
        queryset = queryset.filter(cueanexo__icontains=params['cueanexo'])
    if params['establecimiento']:
        queryset = queryset.filter(escuela__icontains=params['establecimiento'])
    if params['estado'] == 'con_situaciones':
        queryset = queryset.filter(tiene_situaciones=True)
    elif params['estado'] == 'sin_diferencias':
        if not auditoria_valida:
            return queryset.none()
        queryset = queryset.filter(tiene_situaciones=False)
    if params['tipo_situacion']:
        queryset = queryset.filter(
            situaciones_por_tipo__has_key=params['tipo_situacion'],
        )
    return queryset.order_by('region', 'cueanexo', 'escuela')


def _serializar_auditoria(estado):
    fecha = estado.ultimo_refresco_exitoso_en if estado else None
    return {
        'valida': bool(estado and estado.valida),
        'estado_base': estado.estado_base if estado else None,
        'estado_auditoria': estado.estado_auditoria if estado else None,
        'ultimo_refresco_exitoso_en': fecha.isoformat() if fecha else None,
        'alcance': estado.alcance if estado else None,
        'detalle_estado': estado.detalle_estado if estado else None,
    }


def _serializar_situacion(row):
    detalle = row.get('detalle')
    dimension_codigo = row.get('dimension_codigo')
    comparabilidad_codigo = row.get('comparabilidad_codigo')
    accion_revision_codigo = row.get('accion_revision_codigo')
    motivo_no_comparable_codigo = row.get('motivo_no_comparable_codigo')
    causa_sin_datos_codigo = row.get('causa_sin_datos_codigo')
    periodo_ra = row.get('periodo_ra')
    periodo_sge = row.get('periodo_sge')
    return {
        'id': row.get('id'),
        'tipo_situacion': row.get('tipo_situacion'),
        'orden': row.get('orden'),
        'contexto_nivel': row.get('contexto_nivel'),
        'contexto_grado': row.get('contexto_grado'),
        'contexto_seccion': row.get('contexto_seccion'),
        'contexto_turno': row.get('contexto_turno'),
        'contexto_tipo_secc': row.get('contexto_tipo_secc'),
        'titulo': row.get('titulo'),
        'valor_ra': row.get('valor_ra'),
        'valor_sge': row.get('valor_sge'),
        'mensaje': row.get('mensaje'),
        'bloquea_revision': bool(row.get('bloquea_revision')),
        'motivo_bloqueo': row.get('motivo_bloqueo'),
        'mensaje_bloqueo': (
            _etiqueta_bloqueo(row.get('motivo_bloqueo'))
            if row.get('bloquea_revision')
            else ''
        ),
        'detalle': detalle if isinstance(detalle, dict) else {},
        'dimension_codigo': dimension_codigo,
        'dimension_etiqueta': _etiqueta_codigo(
            DIMENSIONES,
            dimension_codigo,
            'Revisión',
        ),
        'categoria_operativa': row.get('categoria_operativa'),
        'comparabilidad_codigo': comparabilidad_codigo,
        'comparabilidad_etiqueta': _etiqueta_codigo(
            COMPARABILIDADES,
            comparabilidad_codigo,
            'Información de comparabilidad no disponible.',
        ),
        'comparabilidad_descripcion': _etiqueta_codigo(
            COMPARABILIDAD_DESCRIPCIONES,
            comparabilidad_codigo,
            'Información de comparabilidad no disponible.',
        ),
        'resumen_diferencia': row.get('resumen_diferencia'),
        'accion_revision_codigo': accion_revision_codigo,
        'accion_revision_etiqueta': _etiqueta_codigo(
            ACCIONES_REVISION,
            accion_revision_codigo,
            'Verificación pendiente según la auditoría.',
        ),
        'periodo_ra': periodo_ra,
        'periodo_sge': periodo_sge,
        'etiqueta_ra': _etiqueta_fuente('RA', periodo_ra),
        'etiqueta_sge': _etiqueta_fuente('SGE', periodo_sge),
        'valor_ra_tipo': row.get('valor_ra_tipo'),
        'valor_sge_tipo': row.get('valor_sge_tipo'),
        'valor_ra_numero': row.get('valor_ra_numero'),
        'valor_sge_numero': row.get('valor_sge_numero'),
        'diferencia_absoluta': row.get('diferencia_absoluta'),
        'diferencia_sge_menos_ra': row.get('diferencia_sge_menos_ra'),
        'comparacion_confiable': row.get('comparacion_confiable'),
        'motivo_no_comparable_codigo': motivo_no_comparable_codigo,
        'motivo_no_comparable_etiqueta': _etiqueta_motivo_no_comparable(
            motivo_no_comparable_codigo,
        ),
        'causa_sin_datos_codigo': causa_sin_datos_codigo,
        'causa_sin_datos_etiqueta': _etiqueta_causa_sin_datos(
            causa_sin_datos_codigo,
            row.get('tipo_situacion'),
        ),
        'detalle_version': row.get('detalle_version'),
    }


def _obtener_situaciones(cueanexos):
    cueanexos_permitidos = set(cueanexos)
    if not cueanexos_permitidos:
        return {}

    queryset = (
        AuditoriaSgeRa.objects.using('sge_nacion')
        .annotate(cueanexo_limpio=Trim('cueanexo'))
        .filter(cueanexo_limpio__in=cueanexos_permitidos)
        .values(*SITUACION_FIELDS)
        .order_by('orden', 'id')
    )

    situaciones_por_cue = {}
    for row in queryset:
        cueanexo = _cueanexo(row.get('cueanexo'))
        if cueanexo not in cueanexos_permitidos:
            continue
        situaciones_por_cue.setdefault(cueanexo, []).append(
            _serializar_situacion(row)
        )
    return situaciones_por_cue


def _normalizar_estructura(value):
    if value is None:
        return None
    return _texto(value).strip()


def _serializar_fila_analisis(row):
    return {
        'id': row.get('id'),
        'nivel': _normalizar_estructura(row.get('nivel')),
        'grado': _normalizar_estructura(row.get('grado')),
        'seccion': _normalizar_estructura(row.get('seccion')),
        'turno': _normalizar_estructura(row.get('turno')),
        'tipo_secc': _normalizar_estructura(row.get('tipo_secc')),
        'total': row.get('total'),
    }


def _obtener_filas_analisis(cueanexo):
    queryset = (
        AnalisisSgeRa.objects.using('sge_nacion')
        .annotate(cueanexo_limpio=Trim('cueanexo'))
        .filter(
            cueanexo_limpio=cueanexo,
            sistema__in=('RA', 'SGE'),
        )
        .values(*ANALISIS_FIELDS)
        .order_by(
            'sistema',
            'nivel',
            'grado',
            'seccion',
            'turno',
            'tipo_secc',
            'id',
        )
    )

    filas = {'RA': [], 'SGE': []}
    for row in queryset:
        sistema = _texto(row.get('sistema')).strip()
        if sistema in filas:
            filas[sistema].append(_serializar_fila_analisis(row))
    return filas


def _orden_valor_estructura(value):
    if value is None:
        return (1, '', '')
    texto = _texto(value)
    return (0, texto, '')


def _valor_detalle_estructurado(value, campo=None):
    if isinstance(value, dict):
        preferred_keys = []
        if campo:
            preferred_keys.append('total' if campo == 'matricula' else campo)
        preferred_keys.extend(('etiqueta', 'texto', 'valor', 'descripcion'))
        for key in preferred_keys:
            item = value.get(key)
            if item is not None and not isinstance(item, (dict, list)):
                return _normalizar_estructura(item)
        return None
    if value is None or isinstance(value, (dict, list)):
        return None
    return _normalizar_estructura(value)


def _valores_detalle(detalle, *keys, campo=None):
    if not isinstance(detalle, dict):
        return set()
    valores = set()
    for key in keys:
        value = detalle.get(key)
        items = value if isinstance(value, list) else [value]
        for item in items:
            normalizado = _valor_detalle_estructurado(item, campo=campo)
            if normalizado is not None:
                valores.add(normalizado)
    return valores


def _dimension_situacion(situacion):
    dimension = situacion.get('dimension_codigo')
    if dimension in DIMENSION_FIELDS or dimension in ('ESTRUCTURA', 'FUENTE', 'COBERTURA_CUE'):
        return dimension
    return TIPO_DIMENSIONES.get(situacion.get('tipo_situacion'))


def _contexto_situacion(situacion, campo):
    return _normalizar_estructura(
        situacion.get(CONTEXTO_FIELDS.get(campo, ''))
    )


def _fila_coincide_contexto(row, situacion, campos):
    return all(
        row.get(campo) == _contexto_situacion(situacion, campo)
        for campo in campos
    )


def _fila_coincide_antecedentes(row, situacion, campo_objetivo):
    if campo_objetivo not in ESTRUCTURA_FIELDS:
        return False
    indice = ESTRUCTURA_FIELDS.index(campo_objetivo)
    for campo in ESTRUCTURA_FIELDS[:indice]:
        if row.get(campo) != _contexto_situacion(situacion, campo):
            return False
    return True


def _valores_objetivo_situacion(situacion, source, campo_objetivo):
    detalle = situacion.get('detalle')
    source_key = source.lower()
    solo_key = f'solo_{source_key}'
    valores_key = f'valores_{source_key}'
    if isinstance(detalle, dict) and solo_key in detalle:
        return _valores_detalle(
            detalle,
            solo_key,
            campo=campo_objetivo,
        )
    if isinstance(detalle, dict) and valores_key in detalle:
        valores = _valores_detalle(
            detalle,
            valores_key,
            campo=campo_objetivo,
        )
        if 'comunes' in detalle:
            valores -= _valores_detalle(
                detalle,
                'comunes',
                campo=campo_objetivo,
            )
        return valores

    valor_fuente = _normalizar_estructura(
        situacion.get(f'valor_{source_key}')
    )
    if valor_fuente is not None:
        return {valor_fuente}
    if campo_objetivo in ESTRUCTURA_FIELDS:
        contexto = _contexto_situacion(situacion, campo_objetivo)
        if contexto is not None:
            return {contexto}
    return None


def _id_evidencia(value):
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def _filas_evidencia(situacion, source):
    detalle = situacion.get('detalle')
    if not isinstance(detalle, dict):
        return []
    detalle_fuente = detalle.get(source.lower())
    if not isinstance(detalle_fuente, dict):
        return []
    filas = detalle_fuente.get('filas')
    if not isinstance(filas, list):
        return []
    return [fila for fila in filas if isinstance(fila, dict)]


def _ids_filas_evidencia(situacion, source, condicion=None):
    ids = set()
    for fila in _filas_evidencia(situacion, source):
        if condicion is not None and not condicion(fila):
            continue
        fila_id = _id_evidencia(fila.get('id'))
        if fila_id is not None:
            ids.add(fila_id)
    return ids


def _ids_registros_repetidos(situacion, source):
    return _ids_filas_evidencia(
        situacion,
        source,
        lambda fila: (
            isinstance(fila.get('calidad_registros_repetidos'), list)
            and bool(fila['calidad_registros_repetidos'])
        ),
    )


def _matricula_no_utilizable(value):
    if value is None:
        return True
    try:
        return value < 0
    except (TypeError, ValueError):
        return False


def _valor_estructural_sin_informacion(value):
    if value is None:
        return True
    if not isinstance(value, str):
        return False
    normalizado = ''.join(value.split()).casefold()
    return not normalizado or normalizado == 'sininformación'


def _campo_dato_estructural_incompleto(situacion):
    return CAMPOS_DATO_ESTRUCTURAL_INCOMPLETO.get(
        situacion.get('accion_revision_codigo')
    )


def _situacion_afecta_fila(situacion, row, source):
    tipo = situacion.get('tipo_situacion')
    if tipo == 'CUE_SIN_CONTRAPARTE':
        return True
    if tipo == 'CUE_SIN_DATOS_RA_SGE':
        return False

    fila_id = _id_evidencia(row.get('id'))
    if tipo == 'ALUMNO_EN_VARIAS_SECCIONES':
        return (
            source == 'SGE'
            and fila_id is not None
            and fila_id in _ids_filas_evidencia(situacion, 'SGE')
        )
    if tipo == 'REGISTROS_REPETIDOS':
        return fila_id is not None and fila_id in _ids_registros_repetidos(
            situacion,
            source,
        )
    if tipo == 'MATRICULA_NO_UTILIZABLE':
        return fila_id is not None and fila_id in _ids_filas_evidencia(
            situacion,
            source,
            lambda fila: _matricula_no_utilizable(fila.get('total')),
        )
    if tipo == 'DATO_ESTRUCTURAL_INCOMPLETO':
        campo_objetivo = _campo_dato_estructural_incompleto(situacion)
        return (
            campo_objetivo is not None
            and fila_id is not None
            and fila_id in _ids_filas_evidencia(
                situacion,
                source,
                lambda fila: _valor_estructural_sin_informacion(
                    fila.get(campo_objetivo)
                ),
            )
        )

    dimension = _dimension_situacion(situacion)
    if dimension in ('FUENTE', 'COBERTURA_CUE', None):
        return False
    if dimension == 'MATRICULA':
        return _fila_coincide_contexto(
            row,
            situacion,
            ESTRUCTURA_FIELDS,
        )
    if dimension == 'ESTRUCTURA':
        return _fila_coincide_contexto(
            row,
            situacion,
            ESTRUCTURA_FIELDS,
        )

    campo_objetivo = DIMENSION_FIELDS.get(dimension)
    if not campo_objetivo:
        return False
    detalle = situacion.get('detalle')
    if (
        campo_objetivo in ESTRUCTURA_FIELDS
        and isinstance(detalle, dict)
        and detalle.get('modo_hallazgo') == 'DESCENDIENTE_RAMAS_EXCLUSIVAS'
    ):
        campo_origen = DIMENSION_FIELDS.get(
            detalle.get('dimension_divergencia_origen')
        )
        if campo_origen not in ESTRUCTURA_FIELDS:
            return False
        indice_origen = ESTRUCTURA_FIELDS.index(campo_origen)
        indice_objetivo = ESTRUCTURA_FIELDS.index(campo_objetivo)
        if indice_origen >= indice_objetivo:
            return False
        if not _fila_coincide_contexto(
            row,
            situacion,
            ESTRUCTURA_FIELDS[:indice_origen],
        ):
            return False
        ramas_exclusivas = _valores_detalle(
            detalle,
            f'ramas_exclusivas_{source.lower()}',
            campo=campo_origen,
        )
        if row.get(campo_origen) not in ramas_exclusivas:
            return False
    elif not _fila_coincide_antecedentes(row, situacion, campo_objetivo):
        return False
    if (
        tipo == 'DATO_ESTRUCTURAL_INCOMPLETO'
        and row.get(campo_objetivo) in (None, '')
    ):
        return True

    valores = _valores_objetivo_situacion(
        situacion,
        source,
        campo_objetivo,
    )
    if valores is not None:
        return row.get(campo_objetivo) in valores
    return row.get(campo_objetivo) is None


def _mensajes_situacion(situacion):
    if (
        situacion.get('tipo_situacion') == 'REGISTROS_REPETIDOS'
        and situacion.get('mensaje_bloqueo')
    ):
        return [situacion['mensaje_bloqueo']]

    mensajes = []
    accion = _texto(situacion.get('accion_revision_etiqueta')).strip()
    if accion:
        mensajes.append(accion)
    if situacion.get('mensaje_bloqueo'):
        mensajes.append(situacion['mensaje_bloqueo'])
    return mensajes


def _nuevo_marcado():
    return {
        'situacion_ids': [],
        'fuentes_afectadas': [],
        'bloquea_revision': False,
        'mensajes': [],
    }


def _agregar_marcado(destino, situacion, fuentes, incluir_mensajes=True):
    situacion_id = situacion.get('id')
    if situacion_id not in destino['situacion_ids']:
        destino['situacion_ids'].append(situacion_id)
    for source in fuentes:
        if source not in destino['fuentes_afectadas']:
            destino['fuentes_afectadas'].append(source)
    destino['bloquea_revision'] = (
        destino['bloquea_revision']
        or bool(situacion.get('bloquea_revision'))
    )
    if incluir_mensajes:
        for mensaje in _mensajes_situacion(situacion):
            if mensaje not in destino['mensajes']:
                destino['mensajes'].append(mensaje)


def _agrupar_filas_por_campo(filas, campo):
    grupos = {}
    for fila in filas:
        grupos.setdefault(fila.get(campo), []).append(fila)
    return grupos


def _fuentes_afectadas(situacion, filas_por_sistema):
    return [
        source
        for source in ('RA', 'SGE')
        if any(
            _situacion_afecta_fila(situacion, fila, source)
            for fila in filas_por_sistema.get(source, [])
        )
    ]


def _situacion_apunta_campo(situacion, campo, filas_por_sistema):
    if situacion.get('tipo_situacion') == 'DATO_ESTRUCTURAL_INCOMPLETO':
        campo_objetivo = _campo_dato_estructural_incompleto(situacion)
        return campo == campo_objetivo and any(
            _situacion_afecta_fila(situacion, fila, source)
            for source in ('RA', 'SGE')
            for fila in filas_por_sistema.get(source, [])
        )
    dimension = _dimension_situacion(situacion)
    if dimension == 'ESTRUCTURA':
        if situacion.get('tipo_situacion') == 'REGISTROS_REPETIDOS':
            return campo == 'matricula'
        return campo == 'matricula'
    return DIMENSION_FIELDS.get(dimension) == campo


def _anotar_dimension(
    arbol,
    nodos_por_fuente,
    filas_por_sistema,
    campo,
    situaciones_visibles,
    ids_con_nodo,
):
    for situacion in situaciones_visibles:
        if not _situacion_apunta_campo(
            situacion,
            campo,
            filas_por_sistema,
        ):
            continue
        fuentes = _fuentes_afectadas(situacion, filas_por_sistema)
        if not fuentes:
            continue
        _agregar_marcado(arbol, situacion, fuentes)
        ids_con_nodo.add(situacion.get('id'))
        for source in fuentes:
            for nodo, filas in nodos_por_fuente[source]:
                if any(
                    _situacion_afecta_fila(situacion, fila, source)
                    for fila in filas
                ):
                    _agregar_marcado(
                        nodo,
                        situacion,
                        [source],
                        incluir_mensajes=False,
                    )


def _finalizar_nodo(nodo):
    nodo['afectado'] = bool(nodo['situacion_ids'])
    hijo = nodo.get('hijos')
    nodo['contiene_situacion'] = (
        nodo['afectado']
        or bool(hijo and hijo.get('contiene_situacion'))
    )
    return nodo


def _finalizar_arbol(arbol, colecciones):
    arbol['afectado'] = bool(arbol['situacion_ids'])
    arbol['contiene_situacion'] = (
        arbol['afectado']
        or any(
            nodo.get('contiene_situacion')
            for coleccion in colecciones
            for nodo in coleccion
        )
    )
    return arbol


def _construir_hoja_fuente(
    filas,
    source,
    situaciones_visibles,
    ids_con_nodo,
):
    hoja = {
        **_nuevo_marcado(),
        'dimension': 'matricula',
        'filas': filas,
    }
    filas_por_sistema = {'RA': [], 'SGE': []}
    filas_por_sistema[source] = filas
    for situacion in situaciones_visibles:
        if not _situacion_apunta_campo(
            situacion,
            'matricula',
            filas_por_sistema,
        ):
            continue
        fuentes = _fuentes_afectadas(situacion, filas_por_sistema)
        if not fuentes:
            continue
        _agregar_marcado(hoja, situacion, fuentes)
        ids_con_nodo.add(situacion.get('id'))
    hoja['afectado'] = bool(hoja['situacion_ids'])
    hoja['contiene_situacion'] = hoja['afectado']
    return hoja


def _construir_subarbol_fuente(
    filas,
    source,
    profundidad,
    situaciones_visibles,
    ids_con_nodo,
):
    if profundidad == len(ESTRUCTURA_FIELDS):
        return _construir_hoja_fuente(
            filas,
            source,
            situaciones_visibles,
            ids_con_nodo,
        )

    campo = ESTRUCTURA_FIELDS[profundidad]
    grupos = _agrupar_filas_por_campo(filas, campo)
    arbol = {
        **_nuevo_marcado(),
        'dimension': campo,
        'nodos': [],
    }
    nodos_por_fuente = {'RA': [], 'SGE': []}
    for valor in sorted(grupos, key=_orden_valor_estructura):
        filas_nodo = grupos[valor]
        nodo = {
            **_nuevo_marcado(),
            'valor': valor,
        }
        arbol['nodos'].append(nodo)
        nodos_por_fuente[source].append((nodo, filas_nodo))

    filas_por_sistema = {'RA': [], 'SGE': []}
    filas_por_sistema[source] = filas
    _anotar_dimension(
        arbol,
        nodos_por_fuente,
        filas_por_sistema,
        campo,
        situaciones_visibles,
        ids_con_nodo,
    )
    for nodo, filas_nodo in nodos_por_fuente[source]:
        nodo['hijos'] = _construir_subarbol_fuente(
            filas_nodo,
            source,
            profundidad + 1,
            situaciones_visibles,
            ids_con_nodo,
        )
        _finalizar_nodo(nodo)
    return _finalizar_arbol(arbol, [arbol['nodos']])


def _construir_hoja_matricula(
    filas_ra,
    filas_sge,
    situaciones,
    situaciones_visibles,
    ids_con_nodo,
):
    hoja = {
        **_nuevo_marcado(),
        'dimension': 'matricula',
        'RA': filas_ra,
        'SGE': filas_sge,
        'matricula_comparable': False,
        'valor_ra_numero': None,
        'valor_sge_numero': None,
        'diferencia_absoluta': None,
        'diferencia_sge_menos_ra': None,
        'resumen_diferencia': '',
    }
    filas_por_sistema = {'RA': filas_ra, 'SGE': filas_sge}
    situaciones_matricula_visibles = []
    for situacion in situaciones_visibles:
        if not _situacion_apunta_campo(
            situacion,
            'matricula',
            filas_por_sistema,
        ):
            continue
        fuentes = _fuentes_afectadas(situacion, filas_por_sistema)
        if not fuentes:
            continue
        _agregar_marcado(hoja, situacion, fuentes)
        ids_con_nodo.add(situacion.get('id'))
        if _dimension_situacion(situacion) == 'MATRICULA':
            situaciones_matricula_visibles.append(situacion)

    bloquea_revision = any(
        situacion.get('bloquea_revision')
        and any(
            _situacion_afecta_fila(situacion, fila, source)
            for source in ('RA', 'SGE')
            for fila in filas_por_sistema[source]
        )
        for situacion in situaciones
    )
    hoja['bloquea_revision'] = hoja['bloquea_revision'] or bloquea_revision
    situacion_comparable = next(
        (
            situacion
            for situacion in situaciones_matricula_visibles
            if situacion.get('comparabilidad_codigo') == 'COMPARABLE'
            and situacion.get('comparacion_confiable') is True
            and not situacion.get('bloquea_revision')
        ),
        None,
    )
    if (
        len(filas_ra) == 1
        and len(filas_sge) == 1
        and not bloquea_revision
        and situacion_comparable
    ):
        hoja.update({
            'matricula_comparable': True,
            'valor_ra_numero': situacion_comparable.get('valor_ra_numero'),
            'valor_sge_numero': situacion_comparable.get('valor_sge_numero'),
            'diferencia_absoluta': situacion_comparable.get(
                'diferencia_absoluta'
            ),
            'diferencia_sge_menos_ra': situacion_comparable.get(
                'diferencia_sge_menos_ra'
            ),
            'resumen_diferencia': situacion_comparable.get(
                'resumen_diferencia'
            ),
        })
    hoja['afectado'] = bool(hoja['situacion_ids'])
    hoja['contiene_situacion'] = hoja['afectado']
    return hoja


def _construir_arbol_dual(
    filas_ra,
    filas_sge,
    profundidad,
    situaciones,
    situaciones_visibles,
    ids_con_nodo,
):
    if profundidad == len(ESTRUCTURA_FIELDS):
        return _construir_hoja_matricula(
            filas_ra,
            filas_sge,
            situaciones,
            situaciones_visibles,
            ids_con_nodo,
        )

    campo = ESTRUCTURA_FIELDS[profundidad]
    grupos_ra = _agrupar_filas_por_campo(filas_ra, campo)
    grupos_sge = _agrupar_filas_por_campo(filas_sge, campo)
    valores_ra = set(grupos_ra)
    valores_sge = set(grupos_sge)
    comunes = sorted(
        valores_ra & valores_sge,
        key=_orden_valor_estructura,
    )
    solo_ra = sorted(
        valores_ra - valores_sge,
        key=_orden_valor_estructura,
    )
    solo_sge = sorted(
        valores_sge - valores_ra,
        key=_orden_valor_estructura,
    )
    arbol = {
        **_nuevo_marcado(),
        'dimension': campo,
        'comunes': [],
        'solo_ra': [],
        'solo_sge': [],
    }
    nodos_por_fuente = {'RA': [], 'SGE': []}

    for valor in comunes:
        nodo = {
            **_nuevo_marcado(),
            'valor': valor,
        }
        arbol['comunes'].append(nodo)
        nodos_por_fuente['RA'].append((nodo, grupos_ra[valor]))
        nodos_por_fuente['SGE'].append((nodo, grupos_sge[valor]))
    for valor in solo_ra:
        nodo = {
            **_nuevo_marcado(),
            'valor': valor,
        }
        arbol['solo_ra'].append(nodo)
        nodos_por_fuente['RA'].append((nodo, grupos_ra[valor]))
    for valor in solo_sge:
        nodo = {
            **_nuevo_marcado(),
            'valor': valor,
        }
        arbol['solo_sge'].append(nodo)
        nodos_por_fuente['SGE'].append((nodo, grupos_sge[valor]))

    filas_por_sistema = {'RA': filas_ra, 'SGE': filas_sge}
    _anotar_dimension(
        arbol,
        nodos_por_fuente,
        filas_por_sistema,
        campo,
        situaciones_visibles,
        ids_con_nodo,
    )
    for nodo in arbol['comunes']:
        valor = nodo['valor']
        nodo['hijos'] = _construir_arbol_dual(
            grupos_ra[valor],
            grupos_sge[valor],
            profundidad + 1,
            situaciones,
            situaciones_visibles,
            ids_con_nodo,
        )
        _finalizar_nodo(nodo)
    for nodo in arbol['solo_ra']:
        valor = nodo['valor']
        nodo['hijos'] = _construir_subarbol_fuente(
            grupos_ra[valor],
            'RA',
            profundidad + 1,
            situaciones_visibles,
            ids_con_nodo,
        )
        _finalizar_nodo(nodo)
    for nodo in arbol['solo_sge']:
        valor = nodo['valor']
        nodo['hijos'] = _construir_subarbol_fuente(
            grupos_sge[valor],
            'SGE',
            profundidad + 1,
            situaciones_visibles,
            ids_con_nodo,
        )
        _finalizar_nodo(nodo)
    return _finalizar_arbol(
        arbol,
        [arbol['comunes'], arbol['solo_ra'], arbol['solo_sge']],
    )


def _construir_detalle_cue(cueanexo, filas_por_sistema, situaciones, situaciones_visibles):
    ids_con_nodo = set()
    arbol = _construir_arbol_dual(
        filas_por_sistema['RA'],
        filas_por_sistema['SGE'],
        0,
        situaciones,
        situaciones_visibles,
        ids_con_nodo,
    )
    situaciones_sin_nodo = [
        situacion.get('id')
        for situacion in situaciones_visibles
        if situacion.get('id') not in ids_con_nodo
    ]
    periodo_ra = next(
        (
            situacion.get('periodo_ra')
            for situacion in situaciones
            if situacion.get('periodo_ra') is not None
        ),
        None,
    )
    periodo_sge = next(
        (
            situacion.get('periodo_sge')
            for situacion in situaciones
            if situacion.get('periodo_sge') is not None
        ),
        None,
    )
    return {
        'cueanexo': cueanexo,
        'arbol': arbol,
        'situaciones': situaciones,
        'situaciones_visibles': situaciones_visibles,
        'situaciones_sin_nodo': situaciones_sin_nodo,
        'forzar_arbol_completo': any(
            situacion.get('tipo_situacion') == 'CUE_SIN_CONTRAPARTE'
            for situacion in situaciones_visibles
        ),
        'modo_default': 'solo_situaciones' if situaciones_visibles else 'ver_todo',
        'tiene_datos_ra': bool(filas_por_sistema['RA']),
        'tiene_datos_sge': bool(filas_por_sistema['SGE']),
        'periodo_ra': periodo_ra,
        'periodo_sge': periodo_sge,
    }


def _cantidad_resumen(value):
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _cantidad_por_tipo(value, tipo_situacion):
    if not isinstance(value, dict):
        return 0
    return _cantidad_resumen(value.get(tipo_situacion))


def _construir_filas_resumen(queryset, params, auditoria_valida):
    filas = []
    for row in queryset.values(*RESUMEN_FIELDS):
        cantidad_situaciones_total = _cantidad_resumen(
            row.get('cantidad_situaciones_total')
        )
        cantidad_bloqueos_total = _cantidad_resumen(
            row.get('cantidad_bloqueos_total')
        )
        cantidad_situaciones_visibles = cantidad_situaciones_total
        cantidad_bloqueos_visibles = cantidad_bloqueos_total
        if params['tipo_situacion']:
            cantidad_situaciones_visibles = _cantidad_por_tipo(
                row.get('situaciones_por_tipo'),
                params['tipo_situacion'],
            )
            cantidad_bloqueos_visibles = _cantidad_por_tipo(
                row.get('bloqueos_por_tipo'),
                params['tipo_situacion'],
            )
        estado_codigo = row.get('estado_codigo')
        estado = row.get('estado')
        if not auditoria_valida:
            estado_codigo = 'auditoria_no_disponible'
            estado = 'Auditoría no disponible'
        filas.append({
            'cueanexo': _cueanexo(row.get('cueanexo')),
            'region': _texto(row.get('region')).strip(),
            'establecimiento': _texto(row.get('escuela')).strip(),
            'estado_actual': _texto(row.get('estado_actual')).strip(),
            'cantidad_situaciones': cantidad_situaciones_visibles,
            'cantidad_situaciones_total': cantidad_situaciones_total,
            'cantidad_situaciones_visibles': cantidad_situaciones_visibles,
            'cantidad_bloqueos_total': cantidad_bloqueos_total,
            'cantidad_bloqueos_visibles': cantidad_bloqueos_visibles,
            'tiene_bloqueos_fuera_del_filtro': (
                bool(params['tipo_situacion'])
                and cantidad_bloqueos_total > cantidad_bloqueos_visibles
            ),
            'estado_codigo': estado_codigo,
            'estado': estado,
            'situaciones': [],
        })
    return filas


def _respuesta_resumen(filas):
    return {
        'cues_mostrados': len(filas),
        'cues_con_situaciones': sum(
            fila['cantidad_situaciones'] > 0 for fila in filas
        ),
        'situaciones': sum(fila['cantidad_situaciones'] for fila in filas),
    }


@method_decorator(login_required, name='dispatch')
class ComparativaSgeRaView(TemplateView):
    template_name = 'indicadoresie/seguimiento/comparativa_sge_ra.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contexto_sge = resolver_contexto_sge(self.request)
        resumen_queryset = _queryset_resumen_autorizado(contexto_sge)
        contexto_presentacion = contexto_sge.copy()
        if contexto_presentacion['alcance'] == 'cue':
            contexto_presentacion['mostrar_selector_cueanexo'] = False
        obj_fecha = FechaActualizacionComparativaSgeRa.objects.filter(id=1).first()
        context.update({
            'active_menu': 'comparativa_ra',
            'sge_context': contexto_presentacion,
            'cargo_usuario': contexto_sge['cargo'],
            'opciones_regiones': _opciones_regiones(resumen_queryset),
            'tipos_situacion': _catalogo_tipos_situacion(),
            'comparativa_ultima_fecha': obj_fecha.fecha if obj_fecha else None,
            'comparativa_fecha_version': (
                obj_fecha.fecha.isoformat() if obj_fecha and obj_fecha.fecha else ''
            ),
            'comparativa_is_admin': contexto_sge['cargo'] == 'Administrador',
        })
        return context


@login_required
def comparativa_sge_ra_json(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'Método no permitido.'}, status=405)

    params = _parametros_comparativa(request)
    contexto_sge = resolver_contexto_sge(request)
    resumen_autorizado = _queryset_resumen_autorizado(contexto_sge)
    estado_auditoria = (
        AuditoriaSgeRaEstado.objects.using('sge_nacion')
        .filter(pk=1)
        .first()
    )
    auditoria = _serializar_auditoria(estado_auditoria)

    if params['detalle_cueanexo']:
        cueanexo = params['detalle_cueanexo']
        if not resumen_autorizado.filter(cueanexo=cueanexo).exists():
            return JsonResponse(
                {'error': 'CUE-Anexo no disponible en el alcance autorizado.'},
                status=404,
            )

        situaciones = _obtener_situaciones([cueanexo]).get(cueanexo, [])
        situaciones_visibles = situaciones
        if params['tipo_situacion']:
            situaciones_visibles = [
                situacion
                for situacion in situaciones
                if situacion['tipo_situacion'] == params['tipo_situacion']
            ]
        detalle = _construir_detalle_cue(
            cueanexo,
            _obtener_filas_analisis(cueanexo),
            situaciones,
            situaciones_visibles,
        )
        return JsonResponse({
            'detalle_cue': detalle,
            'auditoria': auditoria,
        })

    resumen_filtrado = _filtrar_resumen(
        resumen_autorizado,
        params,
        auditoria['valida'],
    )
    filas = _construir_filas_resumen(
        resumen_filtrado,
        params,
        auditoria['valida'],
    )

    return JsonResponse({
        'data': filas,
        'resumen': _respuesta_resumen(filas),
        'auditoria': auditoria,
        'tipos_situacion': _catalogo_tipos_situacion(),
    })


# Actualización de fecha y materializadas exclusiva de Comparativa RA-SGE.
COMPARATIVA_SGE_RA_REFRESH_DB = 'sge_nacion'
COMPARATIVA_SGE_RA_REFRESH_JOB_CACHE_PREFIX = 'comparativa_sge_ra_refresh_job'
COMPARATIVA_SGE_RA_REFRESH_JOB_TIMEOUT = 30 * 60
COMPARATIVA_SGE_RA_REFRESH_LOCK_NAME = 'indicadoresie_comparativa_sge_ra_refresh'
COMPARATIVA_SGE_RA_MATERIALIZADAS = (
    'public.analisis_sge_ra',
    'public.auditoria_sge_ra',
    'public.resumen_sge_ra',
)


def _comparativa_job_cache_key(job_id):
    return f'{COMPARATIVA_SGE_RA_REFRESH_JOB_CACHE_PREFIX}:{job_id}'


def _comparativa_estado_base_job(job_id, started_at=None):
    job_started_at = started_at or timezone.now()
    return {
        'status': 'queued',
        'job_id': str(job_id),
        'step': 0,
        'total': 3,
        'percent': 0,
        'current_view': '',
        'message': 'Actualización de Comparativa RA-SGE en cola.',
        'started_at': job_started_at.isoformat(),
        'started_monotonic': time.monotonic(),
    }


def _comparativa_actualizar_estado_job(job_id, **updates):
    key = _comparativa_job_cache_key(job_id)
    state = cache.get(key) or _comparativa_estado_base_job(job_id)
    state.update(updates)
    cache.set(key, state, COMPARATIVA_SGE_RA_REFRESH_JOB_TIMEOUT)
    return state


def _comparativa_estado_job_para_respuesta(state):
    response = {
        key: value for key, value in state.items()
        if key != 'started_monotonic'
    }
    if 'elapsed_seconds' not in response:
        response['elapsed_seconds'] = round(
            time.monotonic() - state['started_monotonic'], 2
        )
    return response


def _comparativa_mensaje_error_refresh(exc):
    error = getattr(exc, '__cause__', None) or exc
    pgerror = getattr(error, 'pgerror', None)
    if pgerror:
        return str(pgerror).strip()
    diag = getattr(error, 'diag', None)
    message_primary = getattr(diag, 'message_primary', None)
    return str(message_primary).strip() if message_primary else str(exc)


def _monitorear_progreso_comparativa_sge_ra(job_id, backend_pid, stop_event):
    etapas_por_lock = (
        (
            'auditoria_sge_ra',
            1,
            33,
            'Auditoría RA-SGE',
            'Actualizando auditoría RA-SGE...',
        ),
        (
            'resumen_sge_ra',
            2,
            67,
            'Resumen RA-SGE',
            'Actualizando resumen RA-SGE...',
        ),
    )
    last_step = 0

    close_old_connections()
    try:
        monitor_connection = connections[COMPARATIVA_SGE_RA_REFRESH_DB]
        if not monitor_connection.get_autocommit():
            monitor_connection.set_autocommit(True)

        with monitor_connection.cursor() as cursor:
            while not stop_event.is_set():
                cursor.execute(
                    """
                    SELECT c.relname
                    FROM pg_locks l
                    INNER JOIN pg_class c ON c.oid = l.relation
                    INNER JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE l.pid = %s
                      AND l.granted
                      AND l.mode IN ('ExclusiveLock', 'AccessExclusiveLock')
                      AND n.nspname = 'public'
                      AND c.relname IN (
                          'analisis_sge_ra',
                          'auditoria_sge_ra',
                          'resumen_sge_ra'
                      );
                    """,
                    [backend_pid],
                )
                locked_relations = {row[0] for row in cursor.fetchall()}

                for relation_name, step, percent, label, message in etapas_por_lock:
                    if relation_name not in locked_relations or step <= last_step:
                        continue
                    if stop_event.is_set():
                        return
                    _comparativa_actualizar_estado_job(
                        job_id,
                        status='running',
                        step=step,
                        total=3,
                        percent=percent,
                        current_view=label,
                        message=message,
                    )
                    last_step = step
                    if step == 2:
                        return

                if stop_event.wait(0.25):
                    return
    except Exception:
        # El seguimiento no debe interferir con el CALL ni con su rollback.
        return
    finally:
        close_old_connections()
        connections.close_all()


def _ejecutar_refresh_comparativa_sge_ra_job(job_id, nueva_fecha):
    started_monotonic = time.monotonic()
    locked = False
    db_connection = None

    close_old_connections()
    try:
        _comparativa_actualizar_estado_job(
            job_id,
            status='running',
            message='Verificando conexión y materializadas de Comparativa...',
        )
        db_connection = connections[COMPARATIVA_SGE_RA_REFRESH_DB]
        expected_database = db_connection.settings_dict.get('NAME')
        if db_connection.vendor != 'postgresql' or not expected_database:
            raise RuntimeError('La conexión de Comparativa no tiene una base PostgreSQL configurada.')
        if db_connection.in_atomic_block:
            raise RuntimeError('El refresh de Comparativa no puede ejecutarse dentro de una transacción.')

        # El procedimiento hace COMMIT internos: CALL debe ejecutarse en autocommit.
        if not db_connection.get_autocommit():
            db_connection.set_autocommit(True)

        with db_connection.cursor() as cursor:
            cursor.execute('SELECT current_database();')
            if cursor.fetchone()[0] != str(expected_database):
                raise RuntimeError('La conexión de Comparativa no apunta a la base configurada.')

            cursor.execute(
                'SELECT pg_try_advisory_lock(hashtext(%s));',
                [COMPARATIVA_SGE_RA_REFRESH_LOCK_NAME],
            )
            locked = bool(cursor.fetchone()[0])
            if not locked:
                _comparativa_actualizar_estado_job(
                    job_id,
                    status='locked',
                    message='Ya hay una actualización de Comparativa RA-SGE en ejecución.',
                    elapsed_seconds=round(time.monotonic() - started_monotonic, 2),
                )
                return

            missing_views = []
            for qualified_name in COMPARATIVA_SGE_RA_MATERIALIZADAS:
                cursor.execute('SELECT to_regclass(%s);', [qualified_name])
                if cursor.fetchone()[0] is None:
                    missing_views.append(qualified_name)
            if missing_views:
                raise RuntimeError('Faltan materializadas: ' + ', '.join(missing_views))

            cursor.execute('SELECT pg_backend_pid();')
            refresh_backend_pid = cursor.fetchone()[0]
            _comparativa_actualizar_estado_job(
                job_id,
                status='running',
                step=0,
                total=3,
                percent=0,
                current_view='Análisis RA-SGE',
                message='Actualizando análisis RA-SGE...',
            )
            monitor_stop = threading.Event()
            monitor_thread = threading.Thread(
                target=_monitorear_progreso_comparativa_sge_ra,
                args=(job_id, refresh_backend_pid, monitor_stop),
                daemon=True,
            )
            monitor_thread.start()
            try:
                # El CALL conserva validaciones, rollback y publicación atómica V3.3.
                cursor.execute('CALL public.refrescar_auditoria_sge_ra();')
            finally:
                monitor_stop.set()
                monitor_thread.join(timeout=1)

            _comparativa_actualizar_estado_job(
                job_id,
                status='running',
                step=2,
                total=3,
                percent=67,
                current_view='Finalización',
                message='Actualizando fecha de Comparativa...',
            )
            # La fecha usa el router habitual, después de completar el procedimiento.
            FechaActualizacionComparativaSgeRa.objects.update_or_create(
                id=1,
                defaults={'fecha': nueva_fecha},
            )
            _comparativa_actualizar_estado_job(
                job_id,
                status='success',
                step=3,
                percent=100,
                current_view='',
                message='Actualización completada correctamente.',
                elapsed_seconds=round(time.monotonic() - started_monotonic, 2),
            )
    except Exception as exc:
        _comparativa_actualizar_estado_job(
            job_id,
            status='error',
            message=_comparativa_mensaje_error_refresh(exc),
            elapsed_seconds=round(time.monotonic() - started_monotonic, 2),
        )
    finally:
        if locked and db_connection is not None:
            try:
                with db_connection.cursor() as cursor:
                    cursor.execute(
                        'SELECT pg_advisory_unlock(hashtext(%s));',
                        [COMPARATIVA_SGE_RA_REFRESH_LOCK_NAME],
                    )
            except Exception:
                pass
        close_old_connections()
        # Son conexiones propias de este thread; cerrar también libera locks remanentes.
        connections.close_all()


@login_required
def actualizar_fecha_comparativa_sge_ra(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Método no permitido.'}, status=405)
    if obtener_cargo_usuario(request.user) != 'Administrador':
        return JsonResponse(
            {'status': 'error', 'message': 'No tiene permisos de administrador.'},
            status=403,
        )

    try:
        data = json.loads(request.body)
        if not isinstance(data, dict):
            raise ValueError('Se esperaba un objeto JSON.')
        nueva_fecha_str = data.get('fecha')
        if not nueva_fecha_str:
            return JsonResponse({'status': 'error', 'message': 'Fecha requerida.'}, status=400)
        nueva_fecha = timezone.make_aware(
            datetime.datetime.strptime(nueva_fecha_str, '%Y-%m-%dT%H:%M')
        )
        job_id = uuid.uuid4()
        job_started_at = timezone.now()
        cache.set(
            _comparativa_job_cache_key(job_id),
            _comparativa_estado_base_job(job_id, job_started_at),
            COMPARATIVA_SGE_RA_REFRESH_JOB_TIMEOUT,
        )
        thread = threading.Thread(
            target=_ejecutar_refresh_comparativa_sge_ra_job,
            args=(str(job_id), nueva_fecha),
            daemon=True,
        )
        thread.start()
        return JsonResponse(
            {
                'status': 'accepted',
                'job_id': str(job_id),
                'started_at': job_started_at.isoformat(),
                'message': 'Actualización de Comparativa RA-SGE iniciada.',
            },
            status=202,
        )
    except (ValueError, TypeError, UnicodeDecodeError):
        return JsonResponse({'status': 'error', 'message': 'Formato de fecha inválido.'}, status=400)
    except Exception as exc:
        return JsonResponse({'status': 'error', 'message': str(exc)}, status=500)


@login_required
def progreso_actualizar_fecha_comparativa_sge_ra(request, job_id):
    if request.method != 'GET':
        return JsonResponse({'status': 'error', 'message': 'Método no permitido.'}, status=405)
    if obtener_cargo_usuario(request.user) != 'Administrador':
        return JsonResponse(
            {'status': 'error', 'message': 'No tiene permisos de administrador.'},
            status=403,
        )
    state = cache.get(_comparativa_job_cache_key(job_id))
    if not state:
        return JsonResponse({'status': 'error', 'message': 'Job no encontrado.'}, status=404)
    return JsonResponse(_comparativa_estado_job_para_respuesta(state))


@login_required
def estado_fecha_comparativa_sge_ra(request):
    if request.method != 'GET':
        return JsonResponse({'status': 'error', 'message': 'Método no permitido.'}, status=405)
    # Mismo acceso autenticado que ComparativaSgeRaView; la versión no contiene datos territoriales.
    obj_fecha = FechaActualizacionComparativaSgeRa.objects.filter(id=1).first()
    fecha_iso = obj_fecha.fecha.isoformat() if obj_fecha and obj_fecha.fecha else ''
    estado_auditoria = (
        AuditoriaSgeRaEstado.objects.using('sge_nacion')
        .filter(id=1)
        .first()
    )

    def fecha_estado_iso(value):
        return value.isoformat() if value else None

    return JsonResponse({
        'status': 'success',
        'fecha_iso': fecha_iso,
        'version': fecha_iso,
        'refresh_auditoria': {
            'valida': bool(estado_auditoria.valida) if estado_auditoria else False,
            'estado_base': estado_auditoria.estado_base if estado_auditoria else None,
            'estado_auditoria': estado_auditoria.estado_auditoria if estado_auditoria else None,
            'ultimo_intento_en': fecha_estado_iso(
                estado_auditoria.ultimo_intento_en if estado_auditoria else None
            ),
            'ultimo_refresco_exitoso_en': fecha_estado_iso(
                estado_auditoria.ultimo_refresco_exitoso_en if estado_auditoria else None
            ),
            'ultimo_error_en': fecha_estado_iso(
                estado_auditoria.ultimo_error_en if estado_auditoria else None
            ),
            'detalle_estado': estado_auditoria.detalle_estado if estado_auditoria else None,
        },
    })
