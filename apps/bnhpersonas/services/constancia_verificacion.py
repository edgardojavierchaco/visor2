import hashlib
import json

from django.db import transaction
from django.utils import timezone

from ..models import ConstanciaServicio
from .crud import audit, snapshot as model_snapshot


def _texto(value):
    return str(value or '').strip()


def _descripcion(obj, *attrs):
    if obj is None:
        return ''
    for attr in attrs:
        value = getattr(obj, attr, None)
        if value not in (None, ''):
            return _texto(value)
    return _texto(obj)


def _fecha(value):
    return value.isoformat() if value else None


def _decimal(value):
    if value is None:
        return None
    return str(value)


def iterar_servicios_constancia(actividades):
    """
    Expande cada actividad en las ubicaciones curriculares realmente registradas.

    No agrupa, no aplica distinct() y no elimina duplicados entre actividades.
    Si una actividad posee varias ubicaciones (sección múltiple), cada componente
    se emite como una fila independiente. Si no posee detalles de ubicación, se
    conserva una fila basada en los campos históricos de RegistroActividades.
    """
    for actividad in actividades:
        manager = getattr(actividad, 'ubicaciones_curriculares', None)
        ubicaciones = list(manager.all()) if manager is not None else []

        if ubicaciones:
            for ubicacion in ubicaciones:
                yield actividad, ubicacion
        else:
            yield actividad, None


def construir_snapshot_constancia(*, persona, cueanexo, nom_est, actividades, emitida_en):
    servicios = []

    for a in actividades:
        manager = getattr(a, 'ubicaciones_curriculares', None)
        ubicaciones = list(manager.all()) if manager is not None else []
        es_multiple = (
            _texto(getattr(a, 'tipo_ubicacion', '')).upper() == 'MULTIPLE'
            and len(ubicaciones) > 1
        )
        filas = ubicaciones if ubicaciones else [None]

        for indice, ubicacion in enumerate(filas):
            grado_obj = (
                getattr(ubicacion, 'grado_anio', None)
                if ubicacion is not None
                else getattr(a, 'grado_anio', None)
            )
            seccion_obj = (
                getattr(ubicacion, 'seccion', None)
                if ubicacion is not None
                else getattr(a, 'secciones', None)
            )
            turno = (
                getattr(ubicacion, 'turno', '')
                if ubicacion is not None
                else getattr(a, 'turno', '')
            )

            es_ultimo_componente = indice == len(filas) - 1

            servicios.append({
                'id_actividad': a.pk,
                'id_ubicacion': getattr(ubicacion, 'pk', None),
                'id_puesto': _texto(getattr(a, 'id_puesto', '')),
                'tipo_ubicacion': _texto(getattr(a, 'tipo_ubicacion', '')),
                'es_seccion_multiple': es_multiple,
                'fin_bloque_multiple': bool(es_multiple and es_ultimo_componente),
                'tipo_personal': _descripcion(getattr(a, 'tipo_personal', None), 'descripcion'),
                'modalidad': _descripcion(getattr(a, 'modalidad', None), 'descrip_modalidad'),
                'nivel': _descripcion(getattr(a, 'niveles', None), 'descrip_nivel'),
                'cargo_ceic': _descripcion(getattr(a, 'ceic', None), 'descripcion') or 'NO CORRESPONDE',
                'situacion_revista': _descripcion(getattr(a, 'sit_revista', None), 'descrip_sitrev'),
                'condicion_actividad': _descripcion(getattr(a, 'cond_actividad', None), 'denominacion'),
                'tipo_designacion': _descripcion(getattr(a, 't_designacion', None), 'desigfunc_descripcion'),
                'turno': _texto(turno),
                'espacio_curricular': _descripcion(getattr(a, 'espacio_curricular', None), 'nombre')
                    or _descripcion(getattr(a, 'espacios', None), 'descrip_titulo'),
                'grado_anio': _descripcion(grado_obj, 'nombre_grado_anio'),
                'seccion': _descripcion(seccion_obj, 'nombre_seccion'),
                # En sección múltiple la carga pertenece al puesto completo: no se
                # repite en cada componente. Se informa una sola vez al final.
                'carga_horaria': None if es_multiple else _decimal(getattr(a, 'carga_horaria', None)),
                'carga_horaria_total': (
                    _decimal(getattr(a, 'carga_horaria', None))
                    if es_multiple and es_ultimo_componente
                    else None
                ),
                'fecha_inicio': _fecha(getattr(a, 'f_desde', None)),
                'fecha_fin': _fecha(getattr(a, 'f_hasta', None)),
                'estado': _texto(getattr(a, 'estado', '')),
                'validacion': _texto(getattr(a, 'validacion', '')),
            })

    return {
        'version_snapshot': 3,
        'emitida_en': emitida_en.isoformat(),
        'persona': {
            'id': persona.pk,
            'cuil': _texto(getattr(persona, 'cuil', '')),
            'dni': _texto(getattr(persona, 'dni', '')),
            'apellido': _texto(getattr(persona, 'apellido', '')),
            'nombre': _texto(getattr(persona, 'nombre', '')),
        },
        'institucion': {
            'cueanexo': _texto(cueanexo),
            'nombre': _texto(nom_est),
        },
        'servicios': servicios,
    }


def serializar_snapshot(snapshot):
    return json.dumps(
        snapshot,
        ensure_ascii=False,
        sort_keys=True,
        separators=(',', ':'),
    ).encode('utf-8')


def calcular_hash_contenido(snapshot):
    return hashlib.sha256(serializar_snapshot(snapshot)).hexdigest()


def verificar_integridad_constancia(constancia):
    return constancia.hash_contenido == calcular_hash_contenido(constancia.snapshot or {})


def mascara_cuil(cuil):
    digits = ''.join(ch for ch in _texto(cuil) if ch.isdigit())
    if len(digits) != 11:
        return 'Dato protegido'
    # 27-******89-1
    return f'{digits[:2]}-******{digits[8:10]}-{digits[10]}'


@transaction.atomic
def crear_constancia_servicio(*, usuario, persona, cueanexo, nom_est, actividades):
    emitida_en = timezone.now()
    snapshot = construir_snapshot_constancia(
        persona=persona,
        cueanexo=cueanexo,
        nom_est=nom_est,
        actividades=actividades,
        emitida_en=emitida_en,
    )
    hash_contenido = calcular_hash_contenido(snapshot)

    obj = ConstanciaServicio.objects.create(
        persona=persona,
        cueanexo=str(cueanexo),
        nom_est=str(nom_est),
        fecha_emision=emitida_en,
        usuario_emisor=usuario,
        snapshot=snapshot,
        hash_contenido=hash_contenido,
    )
    obj.numero = f'CS-{emitida_en.year}-{obj.pk:08d}'
    obj.save(update_fields=['numero'])

    audit(
        usuario,
        obj,
        'EMITIR_CONSTANCIA',
        before={},
        cue=obj.cueanexo,
    )
    return obj


@transaction.atomic
def registrar_hash_pdf(constancia_id, pdf_bytes):
    obj = ConstanciaServicio.objects.select_for_update().get(pk=constancia_id)
    obj.hash_pdf = hashlib.sha256(pdf_bytes).hexdigest()
    obj.save(update_fields=['hash_pdf'])
    return obj


@transaction.atomic
def anular_constancia(*, usuario, constancia_id, motivo):
    motivo = _texto(motivo)
    if len(motivo) < 5:
        raise ValueError('Indique un motivo de anulación de al menos 5 caracteres.')

    obj = ConstanciaServicio.objects.select_for_update().get(pk=constancia_id)
    if obj.estado == ConstanciaServicio.ESTADO_ANULADA:
        return obj

    before = model_snapshot(obj)
    obj.estado = ConstanciaServicio.ESTADO_ANULADA
    obj.fecha_anulacion = timezone.now()
    obj.usuario_anulacion = usuario
    obj.motivo_anulacion = motivo
    obj.save(update_fields=[
        'estado',
        'fecha_anulacion',
        'usuario_anulacion',
        'motivo_anulacion',
    ])
    audit(
        usuario,
        obj,
        'ANULAR_CONSTANCIA',
        before=before,
        reason=motivo,
        cue=obj.cueanexo,
    )
    return obj
