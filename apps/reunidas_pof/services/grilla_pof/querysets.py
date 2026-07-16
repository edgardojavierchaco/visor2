from django.db.models import Prefetch

from ...models import CargoPof, SnapshotPadronLocalizacionPof


def obtener_cargos_grilla_reunida(*, reunida):
    snapshots_vigentes = SnapshotPadronLocalizacionPof.objects.filter(
        vigente=True
    ).order_by("-fecha_snapshot")

    return (
        CargoPof.objects
        .filter(localizacion__reunida_id=reunida.id)
        .select_related(
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
        .order_by(
            "localizacion__cueanexo",
            "localizacion__cuof",
            "ceic",
            "id",
        )
    )
