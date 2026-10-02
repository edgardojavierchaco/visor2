from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q

from ..models import (
    AsociacionAnexoPof,
    CatalogoAnexoPof,
    HistorialAsociacionAnexoPof,
    HistorialCatalogoAnexoPof,
)


TIPO_PROPIETARIO_CUEANEXO = "CUEANEXO"
TIPO_PROPIETARIO_CUOF = "CUOF"
MAX_CODIGO_ANEXO_POF = 50
MAX_CUOF_ANEXO_POF = 100


def normalizar_codigo_anexo_pof(valor):
    """
    Normaliza un Código Anexo POF sin alterar su semántica.

    Conserva mayúsculas/minúsculas y ceros iniciales. Sólo elimina espacios
    exteriores y rechaza formatos incompatibles con la representación múltiple
    usada por el módulo.
    """
    codigo = str(valor or "").strip()

    if len(codigo) > MAX_CODIGO_ANEXO_POF:
        raise ValidationError({
            "codigo": (
                f"El Código Anexo POF no puede superar "
                f"{MAX_CODIGO_ANEXO_POF} caracteres."
            )
        })

    if "," in codigo:
        raise ValidationError({
            "codigo": "El Código Anexo POF no puede contener comas."
        })

    if any(not caracter.isprintable() for caracter in codigo):
        raise ValidationError({
            "codigo": (
                "El Código Anexo POF no puede contener saltos de línea "
                "ni caracteres de control."
            )
        })

    return codigo


def normalizar_cueanexo_anexo_pof(valor):
    cueanexo = str(valor or "").strip()

    if not cueanexo or len(cueanexo) != 9 or not cueanexo.isdigit():
        raise ValidationError({
            "cueanexo": "El CUEANEXO debe tener exactamente 9 dígitos."
        })

    return cueanexo


def normalizar_cuof_anexo_pof(valor):
    cuof = str(valor or "").strip()

    if not cuof:
        raise ValidationError({
            "cuof": (
                "El CUOF es obligatorio cuando Anexo POF no dispone "
                "de CUEANEXO."
            )
        })

    if len(cuof) > MAX_CUOF_ANEXO_POF:
        raise ValidationError({
            "cuof": f"El CUOF no puede superar {MAX_CUOF_ANEXO_POF} caracteres."
        })

    if any(not caracter.isprintable() for caracter in cuof):
        raise ValidationError({
            "cuof": "El CUOF no puede contener caracteres de control."
        })

    return cuof


def resolver_propietario_anexo_pof(
    *,
    cueanexo="",
    cuof="",
    es_proyecto_especial=False,
):
    """
    Resuelve el propietario canónico de Anexo POF.

    - Si existe CUEANEXO válido, siempre gana CUEANEXO.
    - CUOF sólo es fallback para Proyecto Especial cuando no existe CUEANEXO.
    - Reunida sin CUEANEXO es inconsistente y no cae silenciosamente a CUOF.
    """
    cueanexo = str(cueanexo or "").strip()
    cuof = str(cuof or "").strip()

    if cueanexo:
        return {
            "tipo": TIPO_PROPIETARIO_CUEANEXO,
            "valor": normalizar_cueanexo_anexo_pof(cueanexo),
        }

    if not es_proyecto_especial:
        raise ValidationError({
            "cueanexo": (
                "Anexo POF de una Reunida requiere un CUEANEXO válido."
            )
        })

    return {
        "tipo": TIPO_PROPIETARIO_CUOF,
        "valor": normalizar_cuof_anexo_pof(cuof),
    }


def resolver_propietario_anexo_pof_localizacion(localizacion):
    """
    Resuelve el propietario desde LocalizacionPof sin consultar la BD.

    LocalizacionPof.cueanexo es la identidad canónica del propietario. Sólo un
    Proyecto Especial sin CUEANEXO utiliza CUOF como fallback.
    """
    if localizacion is None:
        raise ValidationError({
            "localizacion": "Debe indicar una localización POF."
        })

    cueanexo = str(getattr(localizacion, "cueanexo", "") or "").strip()
    cuof = str(getattr(localizacion, "cuof", "") or "").strip()
    es_proyecto_especial = bool(
        getattr(localizacion, "proyecto_especial_id", None)
    )

    return resolver_propietario_anexo_pof(
        cueanexo=cueanexo,
        cuof=cuof,
        es_proyecto_especial=es_proyecto_especial,
    )


def normalizar_propietario_anexo_pof(propietario):
    """
    Valida una identidad ya resuelta y devuelve su forma canónica.
    """
    if not isinstance(propietario, dict):
        raise ValidationError({
            "propietario": "El propietario Anexo POF no es válido."
        })

    tipo = str(propietario.get("tipo") or "").strip().upper()
    valor = propietario.get("valor")

    if tipo == TIPO_PROPIETARIO_CUEANEXO:
        return {
            "tipo": TIPO_PROPIETARIO_CUEANEXO,
            "valor": normalizar_cueanexo_anexo_pof(valor),
        }

    if tipo == TIPO_PROPIETARIO_CUOF:
        return {
            "tipo": TIPO_PROPIETARIO_CUOF,
            "valor": normalizar_cuof_anexo_pof(valor),
        }

    raise ValidationError({
        "propietario": "El propietario debe ser CUEANEXO o CUOF."
    })


def _filtro_propietario(propietario):
    propietario = normalizar_propietario_anexo_pof(propietario)

    if propietario["tipo"] == TIPO_PROPIETARIO_CUEANEXO:
        return {
            "cueanexo": propietario["valor"],
            "cuof": "",
        }

    return {
        "cueanexo": "",
        "cuof": propietario["valor"],
    }


def _normalizar_id_positivo(valor, campo):
    try:
        valor = int(valor)
    except (TypeError, ValueError):
        valor = 0

    if valor <= 0:
        raise ValidationError({
            campo: "Debe indicar un identificador válido."
        })

    return valor


def listar_catalogo_anexo_pof(*, incluir_inactivos=False):
    queryset = CatalogoAnexoPof.objects.all()

    if not incluir_inactivos:
        queryset = queryset.filter(activo=True)

    return queryset.order_by("codigo", "id")


def _crear_historial_catalogo(*, catalogo, accion, origen, usuario):
    return HistorialCatalogoAnexoPof.objects.create(
        catalogo=catalogo,
        accion=accion,
        origen=origen,
        usuario=usuario,
    )


def crear_codigo_catalogo(
    *,
    codigo,
    usuario=None,
    origen=HistorialCatalogoAnexoPof.Origen.ADMINISTRACION,
):
    codigo = normalizar_codigo_anexo_pof(codigo)

    if not codigo:
        raise ValidationError({
            "codigo": "El Código Anexo POF no puede quedar vacío."
        })

    with transaction.atomic():
        existente = (
            CatalogoAnexoPof.objects
            .select_for_update()
            .filter(codigo=codigo)
            .first()
        )
        if existente is not None:
            raise ValidationError({
                "codigo": "Ya existe ese Código Anexo POF en el catálogo."
            })

        try:
            with transaction.atomic():
                catalogo = CatalogoAnexoPof.objects.create(
                    codigo=codigo,
                    activo=True,
                    creado_por=usuario,
                    usuario_actualizacion=usuario,
                )
        except IntegrityError as error:
            raise ValidationError({
                "codigo": "Ya existe ese Código Anexo POF en el catálogo."
            }) from error

        _crear_historial_catalogo(
            catalogo=catalogo,
            accion=HistorialCatalogoAnexoPof.Accion.CREAR,
            origen=origen,
            usuario=usuario,
        )

    return catalogo


def _obtener_catalogo_bloqueado(catalogo_id):
    catalogo_id = _normalizar_id_positivo(catalogo_id, "catalogo_id")

    try:
        return (
            CatalogoAnexoPof.objects
            .select_for_update()
            .get(pk=catalogo_id)
        )
    except CatalogoAnexoPof.DoesNotExist as error:
        raise ValidationError({
            "catalogo_id": "No existe el Código Anexo POF indicado."
        }) from error


def desactivar_codigo_catalogo(
    *,
    catalogo_id,
    usuario=None,
    origen=HistorialCatalogoAnexoPof.Origen.ADMINISTRACION,
):
    with transaction.atomic():
        catalogo = _obtener_catalogo_bloqueado(catalogo_id)

        if not catalogo.activo:
            return {
                "catalogo": catalogo,
                "modificado": False,
            }

        catalogo.activo = False
        catalogo.usuario_actualizacion = usuario
        catalogo.save(update_fields=[
            "activo",
            "usuario_actualizacion",
            "actualizado_en",
        ])

        _crear_historial_catalogo(
            catalogo=catalogo,
            accion=HistorialCatalogoAnexoPof.Accion.DESACTIVAR,
            origen=origen,
            usuario=usuario,
        )

        return {
            "catalogo": catalogo,
            "modificado": True,
        }


def reactivar_codigo_catalogo(
    *,
    catalogo_id,
    usuario=None,
    origen=HistorialCatalogoAnexoPof.Origen.ADMINISTRACION,
):
    with transaction.atomic():
        catalogo = _obtener_catalogo_bloqueado(catalogo_id)

        if catalogo.activo:
            return {
                "catalogo": catalogo,
                "modificado": False,
            }

        catalogo.activo = True
        catalogo.usuario_actualizacion = usuario
        catalogo.save(update_fields=[
            "activo",
            "usuario_actualizacion",
            "actualizado_en",
        ])

        _crear_historial_catalogo(
            catalogo=catalogo,
            accion=HistorialCatalogoAnexoPof.Accion.REACTIVAR,
            origen=origen,
            usuario=usuario,
        )

        return {
            "catalogo": catalogo,
            "modificado": True,
        }


def listar_asociaciones_propietario(*, propietario, incluir_inactivas=False):
    filtro = _filtro_propietario(propietario)

    queryset = (
        AsociacionAnexoPof.objects
        .filter(**filtro)
        .select_related("codigo_catalogo")
    )

    if not incluir_inactivas:
        queryset = queryset.filter(activo=True)

    return queryset.order_by("codigo_catalogo__codigo", "id")


def obtener_codigos_activos_propietario(*, propietario):
    """
    Devuelve sólo códigos con asociación vigente.

    No filtra CatalogoAnexoPof.activo: un código retirado del catálogo puede
    seguir siendo una asociación administrativa vigente.
    """
    return [
        asociacion.codigo_catalogo.codigo
        for asociacion in listar_asociaciones_propietario(
            propietario=propietario,
            incluir_inactivas=False,
        )
    ]


def obtener_codigos_activos_propietarios(*, propietarios):
    """
    Resuelve en bloque los códigos vigentes de múltiples propietarios.

    - Normaliza y deduplica CUEANEXO/CUOF antes de consultar.
    - Ejecuta una única consulta para todas las asociaciones activas.
    - Conserva propietarios sin códigos mediante listas vacías.
    - Ordena códigos por codigo ascendente, igual que la lectura individual.
    - No filtra CatalogoAnexoPof.activo: manda el estado de la asociación.

    El resultado se indexa por tuplas (tipo, valor) canónicas.
    """
    propietarios_normalizados = []
    claves_vistas = set()

    for propietario in propietarios or []:
        normalizado = normalizar_propietario_anexo_pof(propietario)
        clave = (normalizado["tipo"], normalizado["valor"])

        if clave in claves_vistas:
            continue

        claves_vistas.add(clave)
        propietarios_normalizados.append(normalizado)

    resultado = {
        (propietario["tipo"], propietario["valor"]): []
        for propietario in propietarios_normalizados
    }

    if not propietarios_normalizados:
        return resultado

    cueanexos = [
        propietario["valor"]
        for propietario in propietarios_normalizados
        if propietario["tipo"] == TIPO_PROPIETARIO_CUEANEXO
    ]
    cuofs = [
        propietario["valor"]
        for propietario in propietarios_normalizados
        if propietario["tipo"] == TIPO_PROPIETARIO_CUOF
    ]

    filtro_propietarios = Q()
    if cueanexos:
        filtro_propietarios |= Q(cueanexo__in=cueanexos, cuof="")
    if cuofs:
        filtro_propietarios |= Q(cueanexo="", cuof__in=cuofs)

    filas = (
        AsociacionAnexoPof.objects
        .filter(filtro_propietarios, activo=True)
        .values_list(
            "cueanexo",
            "cuof",
            "codigo_catalogo__codigo",
        )
        .order_by(
            "cueanexo",
            "cuof",
            "codigo_catalogo__codigo",
            "id",
        )
    )

    for cueanexo, cuof, codigo in filas:
        if cueanexo:
            clave = (TIPO_PROPIETARIO_CUEANEXO, cueanexo)
        else:
            clave = (TIPO_PROPIETARIO_CUOF, cuof)

        if clave in resultado:
            resultado[clave].append(codigo)

    return resultado


def _crear_historial_asociacion(*, asociacion, accion, origen, usuario):
    return HistorialAsociacionAnexoPof.objects.create(
        asociacion=asociacion,
        accion=accion,
        origen=origen,
        usuario=usuario,
    )


def asociar_codigo(
    *,
    propietario,
    catalogo_id,
    usuario=None,
    origen=HistorialAsociacionAnexoPof.Origen.ADMINISTRACION,
):
    filtro_propietario = _filtro_propietario(propietario)

    with transaction.atomic():
        catalogo = _obtener_catalogo_bloqueado(catalogo_id)

        if not catalogo.activo:
            raise ValidationError({
                "catalogo_id": (
                    "El Código Anexo POF está inactivo y no puede utilizarse "
                    "para nuevas asociaciones."
                )
            })

        asociacion = (
            AsociacionAnexoPof.objects
            .select_for_update()
            .filter(
                **filtro_propietario,
                codigo_catalogo=catalogo,
            )
            .first()
        )

        if asociacion is not None:
            if asociacion.activo:
                return {
                    "asociacion": asociacion,
                    "creado": False,
                    "reactivado": False,
                    "modificado": False,
                }

            asociacion.activo = True
            asociacion.usuario_actualizacion = usuario
            asociacion.save(update_fields=[
                "activo",
                "usuario_actualizacion",
                "actualizado_en",
            ])

            _crear_historial_asociacion(
                asociacion=asociacion,
                accion=HistorialAsociacionAnexoPof.Accion.REACTIVAR,
                origen=origen,
                usuario=usuario,
            )

            return {
                "asociacion": asociacion,
                "creado": False,
                "reactivado": True,
                "modificado": True,
            }

        try:
            with transaction.atomic():
                asociacion = AsociacionAnexoPof.objects.create(
                    **filtro_propietario,
                    codigo_catalogo=catalogo,
                    activo=True,
                    usuario_actualizacion=usuario,
                )
        except IntegrityError as error:
            asociacion = (
                AsociacionAnexoPof.objects
                .select_for_update()
                .filter(
                    **filtro_propietario,
                    codigo_catalogo=catalogo,
                )
                .first()
            )
            if asociacion is None:
                raise error

            if asociacion.activo:
                return {
                    "asociacion": asociacion,
                    "creado": False,
                    "reactivado": False,
                    "modificado": False,
                }

            asociacion.activo = True
            asociacion.usuario_actualizacion = usuario
            asociacion.save(update_fields=[
                "activo",
                "usuario_actualizacion",
                "actualizado_en",
            ])

            _crear_historial_asociacion(
                asociacion=asociacion,
                accion=HistorialAsociacionAnexoPof.Accion.REACTIVAR,
                origen=origen,
                usuario=usuario,
            )

            return {
                "asociacion": asociacion,
                "creado": False,
                "reactivado": True,
                "modificado": True,
            }

        _crear_historial_asociacion(
            asociacion=asociacion,
            accion=HistorialAsociacionAnexoPof.Accion.ASOCIAR,
            origen=origen,
            usuario=usuario,
        )

        return {
            "asociacion": asociacion,
            "creado": True,
            "reactivado": False,
            "modificado": True,
        }


def desactivar_asociacion(
    *,
    propietario,
    catalogo_id,
    usuario=None,
    origen=HistorialAsociacionAnexoPof.Origen.ADMINISTRACION,
):
    filtro_propietario = _filtro_propietario(propietario)

    with transaction.atomic():
        catalogo = _obtener_catalogo_bloqueado(catalogo_id)

        asociacion = (
            AsociacionAnexoPof.objects
            .select_for_update()
            .filter(
                **filtro_propietario,
                codigo_catalogo=catalogo,
            )
            .first()
        )

        if asociacion is None:
            raise ValidationError({
                "asociacion": (
                    "El Código Anexo POF no está asociado al propietario indicado."
                )
            })

        if not asociacion.activo:
            return {
                "asociacion": asociacion,
                "modificado": False,
            }

        asociacion.activo = False
        asociacion.usuario_actualizacion = usuario
        asociacion.save(update_fields=[
            "activo",
            "usuario_actualizacion",
            "actualizado_en",
        ])

        _crear_historial_asociacion(
            asociacion=asociacion,
            accion=HistorialAsociacionAnexoPof.Accion.DESACTIVAR,
            origen=origen,
            usuario=usuario,
        )

        return {
            "asociacion": asociacion,
            "modificado": True,
        }


def reactivar_asociacion(
    *,
    propietario,
    catalogo_id,
    usuario=None,
    origen=HistorialAsociacionAnexoPof.Origen.ADMINISTRACION,
):
    filtro_propietario = _filtro_propietario(propietario)

    with transaction.atomic():
        catalogo = _obtener_catalogo_bloqueado(catalogo_id)

        if not catalogo.activo:
            raise ValidationError({
                "catalogo_id": (
                    "Primero debe reactivar el código en el catálogo antes "
                    "de reactivar esta asociación."
                )
            })

        asociacion = (
            AsociacionAnexoPof.objects
            .select_for_update()
            .filter(
                **filtro_propietario,
                codigo_catalogo=catalogo,
            )
            .first()
        )

        if asociacion is None:
            raise ValidationError({
                "asociacion": (
                    "El Código Anexo POF nunca estuvo asociado al propietario indicado."
                )
            })

        if asociacion.activo:
            return {
                "asociacion": asociacion,
                "modificado": False,
            }

        asociacion.activo = True
        asociacion.usuario_actualizacion = usuario
        asociacion.save(update_fields=[
            "activo",
            "usuario_actualizacion",
            "actualizado_en",
        ])

        _crear_historial_asociacion(
            asociacion=asociacion,
            accion=HistorialAsociacionAnexoPof.Accion.REACTIVAR,
            origen=origen,
            usuario=usuario,
        )

        return {
            "asociacion": asociacion,
            "modificado": True,
        }


def aplicar_seleccion_propietario(
    *,
    propietario,
    catalogo_ids,
    usuario=None,
    origen=HistorialAsociacionAnexoPof.Origen.ADMINISTRACION,
):
    """
    Aplica de forma atómica el conjunto final de Códigos Anexo POF activos
    para un propietario CUEANEXO/CUOF.

    Los códigos ya asociados y vigentes se conservan aunque su catálogo haya
    sido retirado. Un código nuevo o una reactivación requiere catálogo activo.
    """
    propietario = normalizar_propietario_anexo_pof(propietario)

    if not isinstance(catalogo_ids, (list, tuple, set)):
        raise ValidationError({
            "catalogo_ids": "Debe enviar una lista de identificadores."
        })

    seleccion = []
    vistos = set()
    for valor in catalogo_ids:
        if isinstance(valor, bool):
            raise ValidationError({
                "catalogo_ids": "Todos los identificadores deben ser válidos."
            })
        catalogo_id = _normalizar_id_positivo(valor, "catalogo_ids")
        if catalogo_id in vistos:
            continue
        vistos.add(catalogo_id)
        seleccion.append(catalogo_id)

    seleccion_ids = set(seleccion)
    filtro_propietario = _filtro_propietario(propietario)

    with transaction.atomic():
        asociaciones_existentes = list(
            AsociacionAnexoPof.objects
            .select_for_update()
            .filter(**filtro_propietario)
            .select_related("codigo_catalogo")
        )
        activos_ids = {
            asociacion.codigo_catalogo_id
            for asociacion in asociaciones_existentes
            if asociacion.activo
        }

        desactivar_ids = sorted(activos_ids - seleccion_ids)
        activar_ids = sorted(seleccion_ids - activos_ids)

        modificados = 0

        for catalogo_id in desactivar_ids:
            resultado = desactivar_asociacion(
                propietario=propietario,
                catalogo_id=catalogo_id,
                usuario=usuario,
                origen=origen,
            )
            if resultado["modificado"]:
                modificados += 1

        for catalogo_id in activar_ids:
            resultado = asociar_codigo(
                propietario=propietario,
                catalogo_id=catalogo_id,
                usuario=usuario,
                origen=origen,
            )
            if resultado["modificado"]:
                modificados += 1

        asociaciones = list(
            listar_asociaciones_propietario(
                propietario=propietario,
                incluir_inactivas=True,
            )
        )

    return {
        "propietario": propietario,
        "asociaciones": asociaciones,
        "modificados": modificados,
    }


def obtener_historial_catalogo(*, catalogo_id):
    catalogo_id = _normalizar_id_positivo(catalogo_id, "catalogo_id")

    return (
        HistorialCatalogoAnexoPof.objects
        .filter(catalogo_id=catalogo_id)
        .select_related("catalogo", "usuario")
        .order_by("-fecha", "-id")
    )


def obtener_historial_propietario(*, propietario):
    filtro_propietario = _filtro_propietario(propietario)
    filtro_historial = {
        f"asociacion__{campo}": valor
        for campo, valor in filtro_propietario.items()
    }

    return (
        HistorialAsociacionAnexoPof.objects
        .filter(**filtro_historial)
        .select_related(
            "asociacion",
            "asociacion__codigo_catalogo",
            "usuario",
        )
        .order_by("-fecha", "-id")
    )
