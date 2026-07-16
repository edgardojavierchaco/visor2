from django.db.models import Case, Count, IntegerField, Prefetch, Q, Value, When

from ..models import CargoPof, LocalizacionPof, ProyectosEspecialesPof, SnapshotPadronLocalizacionPof
from .niveles_service import limpiar_texto


MENSAJE_SIN_COINCIDENCIAS = (
    "No hay datos previos para este CUOF en Proyectos Especiales del mismo año."
)


def _snapshot_vigente(localizacion):
    snapshots = getattr(localizacion, "snapshots_vigentes", [])
    return snapshots[0] if snapshots else None


def _texto(valor):
    return str(valor or "").strip()


def _serializar_localizacion_manual(localizacion, proyecto_actual_id):
    """
    Serializa coincidencias históricas de CUOF para sugerir el modo de carga.

    - Conserva todos los identificadores informativos ya expuestos por la búsqueda.
    - Marca si la coincidencia tiene CUEANEXO y por lo tanto requiere padrón.
    - Sugiere `PADRON` o `MANUAL_CONTROLADO` sin ocultar resultados previos.
    """
    snapshot = _snapshot_vigente(localizacion)
    proyecto = localizacion.proyecto_especial
    cueanexo = _texto(localizacion.cueanexo)
    tiene_cueanexo = bool(cueanexo)

    return {
        "localizacion_id": localizacion.id,
        "proyecto_especial_id": proyecto.id,
        "proyecto_nombre": proyecto.nombre,
        "proyecto_anio": proyecto.anio,
        "proyecto_resolucion": _texto(proyecto.resolucion),
        "misma_cabecera": localizacion.proyecto_especial_id == proyecto_actual_id,
        "cuof": _texto(localizacion.cuof),
        "cuof_loc": _texto(localizacion.cuof),
        "tiene_cueanexo": tiene_cueanexo,
        "requiere_padron": tiene_cueanexo,
        "modo_sugerido": "PADRON" if tiene_cueanexo else "MANUAL_CONTROLADO",
        "cueanexo": cueanexo,
        "padron_cueanexo": cueanexo,
        "cue_anexo": cueanexo,
        "cue": localizacion.cue_base,
        "anexo": localizacion.anexo_localizacion,
        "cui": _texto(localizacion.cui),
        "cui_loc": _texto(localizacion.cui),
        "nombre_establecimiento": _texto(getattr(snapshot, "nombre_establecimiento", "")),
        "nom_est": _texto(getattr(snapshot, "nombre_establecimiento", "")),
        "numero_establecimiento": _texto(getattr(snapshot, "numero_establecimiento", "")),
        "nro_est": _texto(getattr(snapshot, "numero_establecimiento", "")),
        "region": _texto(getattr(snapshot, "region", "")),
        "region_loc": _texto(getattr(snapshot, "region", "")),
        "localidad": _texto(getattr(snapshot, "localidad", "")),
        "departamento": _texto(getattr(snapshot, "departamento", "")),
        "oferta": _texto(getattr(snapshot, "oferta", "")),
        "oferta_real": _texto(getattr(snapshot, "oferta", "")),
        "acronimo": _texto(getattr(snapshot, "acronimo", "")),
        "ambito": _texto(getattr(snapshot, "ambito", "")),
        "categoria": _texto(getattr(snapshot, "categoria", "")),
        "jornada": _texto(getattr(snapshot, "jornada", "")),
        "estado_localizacion_padron": _texto(getattr(snapshot, "estado_localizacion_padron", "")),
        "estado_loc": _texto(getattr(snapshot, "estado_localizacion_padron", "")),
        "estado_oferta_padron": _texto(getattr(snapshot, "estado_oferta_padron", "")),
        "est_oferta": _texto(getattr(snapshot, "estado_oferta_padron", "")),
        "estado_establecimiento_padron": _texto(getattr(snapshot, "estado_establecimiento_padron", "")),
        "estado_est": _texto(getattr(snapshot, "estado_establecimiento_padron", "")),
        "origen_datos": _texto(getattr(snapshot, "origen_datos", "")),
        "estado_padron": _texto(getattr(snapshot, "estado_padron", "")),
        "total_cargos_afectados": localizacion.total_cargos_afectados,
    }


def buscar_cuof_manual_proyecto_especial(proyecto_especial_id, cuof):
    proyecto_id = limpiar_texto(proyecto_especial_id, 20)
    cuof_normalizado = limpiar_texto(cuof, 100)

    if not proyecto_id.isdigit():
        return {
            "ok": False,
            "mensaje": "Debe seleccionar un Proyecto Especial POF válido.",
            "errores": {"proyecto_especial_id": ["El Proyecto Especial seleccionado no es válido."]},
        }

    if not cuof_normalizado:
        return {
            "ok": False,
            "mensaje": "Ingresá un CUOF para buscar datos previos.",
            "errores": {"cuof": ["Ingresá un CUOF para buscar datos previos."]},
        }

    try:
        proyecto_actual = ProyectosEspecialesPof.objects.get(pk=proyecto_id)
    except ProyectosEspecialesPof.DoesNotExist:
        return {
            "ok": False,
            "mensaje": "No existe el Proyecto Especial POF seleccionado.",
            "errores": {"proyecto_especial_id": ["No existe el Proyecto Especial POF seleccionado."]},
        }

    snapshots_vigentes = SnapshotPadronLocalizacionPof.objects.filter(
        vigente=True,
    ).order_by("-fecha_snapshot")

    localizaciones = (
        LocalizacionPof.objects
        .select_related("proyecto_especial")
        .prefetch_related(
            Prefetch(
                "snapshots_padron",
                queryset=snapshots_vigentes,
                to_attr="snapshots_vigentes",
            )
        )
        .filter(
            proyecto_especial__isnull=False,
            proyecto_especial__anio=proyecto_actual.anio,
            cuof__iexact=cuof_normalizado,
        )
        .annotate(
            prioridad_cabecera=Case(
                When(proyecto_especial_id=proyecto_actual.id, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            ),
            total_cargos_afectados=Count(
                "cargos",
                filter=Q(cargos__estado_pof=CargoPof.EstadoPof.AFECTADO),
                distinct=True,
            ),
        )
        .order_by("prioridad_cabecera", "-actualizado_en", "id")
    )

    coincidencias = [
        _serializar_localizacion_manual(localizacion, proyecto_actual.id)
        for localizacion in localizaciones
    ]

    if not coincidencias:
        return {
            "ok": True,
            "encontrado": False,
            "mensaje": MENSAJE_SIN_COINCIDENCIAS,
            "coincidencias": [],
        }

    return {
        "ok": True,
        "encontrado": True,
        "coincidencias": coincidencias,
    }
