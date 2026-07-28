from django.core.paginator import Paginator
from decimal import Decimal

from django.db import OperationalError, ProgrammingError
from django.db.models import Prefetch, Q

from ..models import CargoPof, SnapshotPadronLocalizacionPof
from .filtros_pof_service import (
    NIVEL_TODOS,
    MENSAJE_FILTROS_INVALIDOS,
    construir_chips_filtros_cargos,
    filtros_cargos_suficientes,
    filtros_tienen_intencion,
    obtener_mensaje_filtros_insuficientes_cargos,
    querystring_limpio_cargos,
    validar_anio_filtro,
    validar_ceic_filtro,
    validar_cueanexo_filtro,
    validar_cuof_filtro,
    validar_estado_pof_filtro,
    validar_nivel_filtro,
    validar_unidad_cantidad_filtro,
)
from .niveles_service import (
    NIVELES_VALIDOS,
    limpiar_texto,
    obtener_anio_activo,
    obtener_nombre_nivel,
)


PAGE_SIZE_OPTIONS = (10, 30, 50, 100)


def _obtener_page_size(request):
    try:
        page_size = int(request.GET.get("page_size", PAGE_SIZE_OPTIONS[0]))
    except (TypeError, ValueError):
        return PAGE_SIZE_OPTIONS[0]

    return page_size if page_size in PAGE_SIZE_OPTIONS else PAGE_SIZE_OPTIONS[0]


def _obtener_filtros_consulta(request):
    filtros, _ = _obtener_filtros_consulta_con_errores(request)
    return filtros


def _obtener_filtros_consulta_con_errores(request):
    """
    Normaliza filtros GET de Administración de cargos y conserva errores.

    - Reutiliza reglas comunes de filtros POF.
    - Evita aplicar valores inválidos al QuerySet.
    - Mantiene contexto de Proyecto Especial cuando viene en la URL.
    """
    cabecera_tipo = limpiar_texto(request.GET.get("cabecera_tipo", ""), 30).upper()
    proyecto_especial_id = limpiar_texto(request.GET.get("proyecto_especial_id", ""), 20)
    filtros = {
        "anio": "",
        "nivel": "",
        "cueanexo": "",
        "cuof": "",
        "ceic": "",
        "estado_pof": "",
        "unidad_cantidad": "",
        "cabecera_tipo": cabecera_tipo if cabecera_tipo == "PROYECTO_ESPECIAL" else "",
        "proyecto_especial_id": proyecto_especial_id if proyecto_especial_id.isdigit() else "",
    }
    errores = {}
    validadores = {
        "anio": validar_anio_filtro,
        "cueanexo": validar_cueanexo_filtro,
        "cuof": validar_cuof_filtro,
        "ceic": validar_ceic_filtro,
        "estado_pof": validar_estado_pof_filtro,
        "unidad_cantidad": validar_unidad_cantidad_filtro,
    }
    for clave, validador in validadores.items():
        valor, error = validador(request.GET.get(clave, ""))
        filtros[clave] = valor
        if error:
            errores[clave] = error
    nivel, error = validar_nivel_filtro(request.GET.get("nivel", ""))
    filtros["nivel"] = nivel
    if error:
        errores["nivel"] = error
    return filtros, errores


def _obtener_cargos_queryset():
    snapshots_vigentes = SnapshotPadronLocalizacionPof.objects.filter(
        vigente=True
    ).order_by("-fecha_snapshot")

    return (
        CargoPof.objects.select_related(
            "localizacion",
            "localizacion__reunida",
            "localizacion__proyecto_especial",
            "lote_carga",
        )
        .prefetch_related(
            Prefetch(
                "localizacion__snapshots_padron",
                queryset=snapshots_vigentes,
                to_attr="snapshots_vigentes",
            )
        )
        .order_by("-actualizado_en", "-id")
    )


def _aplicar_filtros_cargos(queryset, filtros):
    if filtros["proyecto_especial_id"]:
        queryset = queryset.filter(localizacion__proyecto_especial_id=filtros["proyecto_especial_id"])

    if filtros["anio"]:
        queryset = queryset.filter(
            Q(localizacion__reunida__anio=filtros["anio"])
            | Q(localizacion__proyecto_especial__anio=filtros["anio"])
        )

    if filtros["nivel"] and filtros["nivel"] != NIVEL_TODOS and not filtros["proyecto_especial_id"]:
        queryset = queryset.filter(localizacion__reunida__nivel=filtros["nivel"])

    if filtros["cueanexo"]:
        queryset = queryset.filter(localizacion__cueanexo=filtros["cueanexo"])

    if filtros["cuof"] and not filtros["cueanexo"]:
        queryset = queryset.filter(localizacion__cuof__iexact=filtros["cuof"])

    if filtros["ceic"]:
        queryset = queryset.filter(ceic=int(filtros["ceic"]))

    if filtros["estado_pof"]:
        queryset = queryset.filter(estado_pof=filtros["estado_pof"])

    if filtros["unidad_cantidad"]:
        queryset = queryset.filter(unidad_cantidad=filtros["unidad_cantidad"])

    return queryset


def _obtener_snapshot_vigente(localizacion):
    snapshots = getattr(localizacion, "snapshots_vigentes", [])
    return snapshots[0] if snapshots else None


def _valor_o_guion(valor):
    return valor if valor not in (None, "") else "—"


def _cantidad_texto(valor):
    numero = Decimal(valor)
    if numero == numero.to_integral_value():
        return str(int(numero))
    return str(numero.quantize(Decimal("0.01")))


def _derivar_cue(cueanexo):
    cueanexo = str(cueanexo or "").strip()
    return cueanexo[:7] if cueanexo.isdigit() and len(cueanexo) >= 7 else "—"


def _derivar_anexo(cueanexo):
    cueanexo = str(cueanexo or "").strip()
    return cueanexo[-2:] if cueanexo.isdigit() and len(cueanexo) >= 9 else "—"


def _resumir_cabecera(localizacion):
    reunida = localizacion.reunida
    if reunida:
        return f"Reunida {reunida.anio} - {reunida.get_nivel_display()}"

    proyecto = localizacion.proyecto_especial
    if proyecto:
        return f"Proyecto Especial - {proyecto.nombre}"

    return "—"


def _resumir_establecimiento(localizacion):
    snapshot = _obtener_snapshot_vigente(localizacion)
    if not snapshot:
        return "—"

    return _valor_o_guion(
        snapshot.nombre_establecimiento or snapshot.numero_establecimiento
    )


def _serializar_cargo(cargo):
    localizacion = cargo.localizacion

    return {
        "id": cargo.id,
        "cabecera": _resumir_cabecera(localizacion),
        "cue": _derivar_cue(localizacion.cueanexo),
        "anexo": _derivar_anexo(localizacion.cueanexo),
        "establecimiento": _resumir_establecimiento(localizacion),
        "unidad": cargo.get_unidad_cantidad_display(),
        "ceic": _valor_o_guion(cargo.ceic),
        "cargo": _valor_o_guion(cargo.cargo),
        "cantidad": _cantidad_texto(cargo.cantidad),
        "puntos": cargo.puntos_asignados,
        "estado": cargo.get_estado_pof_display(),
        "estado_clase": cargo.estado_pof.lower(),
        "actualizado_en": cargo.actualizado_en,
    }


def _obtener_page_range(paginator, page_obj):
    if hasattr(paginator, "get_elided_page_range"):
        return paginator.get_elided_page_range(
            number=page_obj.number,
            on_each_side=2,
            on_ends=1,
        )
    return paginator.page_range


def construir_contexto_consulta(request):
    filtros, errores_filtros = _obtener_filtros_consulta_con_errores(request)
    page_size = _obtener_page_size(request)
    hay_intencion_filtros = filtros_tienen_intencion(filtros)
    filtros_cargos_validos = filtros_cargos_suficientes(filtros)

    filtros_suficientes = (
        not errores_filtros
        and (
            filtros_cargos_validos
            or not hay_intencion_filtros
        )
    )

    mostrar_mensaje_filtros = hay_intencion_filtros and not filtros_suficientes

    queryset = _obtener_cargos_queryset()

    if errores_filtros:
        queryset = queryset.none()
    elif hay_intencion_filtros:
        if filtros_cargos_validos:
            queryset = _aplicar_filtros_cargos(queryset, filtros)
        else:
            queryset = queryset.none()

    try:
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(request.GET.get("page", 1))
        total_registros = paginator.count
        cargos = [_serializar_cargo(cargo) for cargo in page_obj.object_list]
        tabla_cargos_no_migrada = False
    except (ProgrammingError, OperationalError):
        paginator = Paginator([], page_size)
        page_obj = paginator.get_page(1)
        total_registros = 0
        cargos = []
        tabla_cargos_no_migrada = True

    query_params = request.GET.copy()
    query_params.pop("page", None)
    query_params["page_size"] = str(page_size)

    for nombre, valor in filtros.items():
        if valor:
            query_params[nombre] = valor
        else:
            query_params.pop(nombre, None)

    tiene_contexto = bool(filtros["anio"] and filtros["nivel"] and filtros["nivel"] != NIVEL_TODOS)
    tiene_contexto_proyecto = bool(
        filtros["cabecera_tipo"] == "PROYECTO_ESPECIAL"
        and filtros["proyecto_especial_id"]
    )

    return {
        "anio_activo": filtros["anio"] if tiene_contexto or tiene_contexto_proyecto else "",
        "anio_filtro": filtros["anio"] or obtener_anio_activo(request, permitir_vacio=True),
        "nivel_activo": "Todos los niveles" if filtros["nivel"] == NIVEL_TODOS else obtener_nombre_nivel(filtros["nivel"]),
        "nivel_codigo": filtros["nivel"] if tiene_contexto else "",
        "cabecera_tipo_activa": filtros["cabecera_tipo"],
        "proyecto_especial_id_activo": filtros["proyecto_especial_id"],
        "niveles": NIVELES_VALIDOS,
        "opciones_estado_pof": CargoPof.EstadoPof.choices,
        "opciones_unidad_cantidad": CargoPof.UnidadCantidad.choices,
        "filtros": filtros,
        "errores_filtros": errores_filtros,
        "filtros_activos": construir_chips_filtros_cargos(request, filtros, errores_filtros),
        "filtros_suficientes": filtros_suficientes,
        "mensaje_filtros": (
            MENSAJE_FILTROS_INVALIDOS
            if errores_filtros
            else (
                obtener_mensaje_filtros_insuficientes_cargos(filtros)
                if mostrar_mensaje_filtros
                else ""
            )
        ),
        "limpiar_filtros_querystring": querystring_limpio_cargos(request, page_size),
        "page_obj": page_obj,
        "paginator": paginator,
        "cargos": cargos,
        "total_registros": total_registros,
        "showing_start": page_obj.start_index() if total_registros else 0,
        "showing_end": page_obj.end_index() if total_registros else 0,
        "page_size": page_size,
        "page_size_options": PAGE_SIZE_OPTIONS,
        "query_params_base": query_params.urlencode(),
        "page_range": _obtener_page_range(paginator, page_obj),
        "tabla_cargos_no_migrada": tabla_cargos_no_migrada,
    }
