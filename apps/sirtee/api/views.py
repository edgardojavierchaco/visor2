from django.http import JsonResponse
from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from django.views.decorators.http import require_GET

from apps.sirtee.data.padron import PadronEscuelas
from apps.sirtee.models.relevamientos import Relevamiento
from apps.sirtee.models.hallazgos import Hallazgo
from apps.sirtee.models.intervenciones import Intervencion

from apps.sirtee.api.serializers import (
    RelevamientoSerializer,
    HallazgoSerializer,
    IntervencionSerializer
)

from apps.sirtee.api.filters import (
    RelevamientoFilter,
    HallazgoFilter,
    IntervencionFilter
)


# --------------------------------------
# RELEVAMIENTO API
# --------------------------------------

class RelevamientoViewSet(viewsets.ModelViewSet):
    queryset = Relevamiento.objects.all().select_related("escuela")
    serializer_class = RelevamientoSerializer

    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_class = RelevamientoFilter

    search_fields = [
        "escuela__nom_est",
        "escuela__cueanexo",
        "observaciones"
    ]


# --------------------------------------
# HALLAZGO API
# --------------------------------------

class HallazgoViewSet(viewsets.ModelViewSet):
    queryset = Hallazgo.objects.all().select_related(
        "relevamiento",
        "relevamiento__escuela"
    )
    serializer_class = HallazgoSerializer

    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_class = HallazgoFilter

    search_fields = [
        "titulo",
        "descripcion",
        "relevamiento__escuela__nom_est"
    ]


# --------------------------------------
# INTERVENCIÓN API
# --------------------------------------

class IntervencionViewSet(viewsets.ModelViewSet):
    queryset = Intervencion.objects.all().select_related(
        "hallazgo",
        "hallazgo__relevamiento",
        "hallazgo__relevamiento__escuela"
    )
    serializer_class = IntervencionSerializer

    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_class = IntervencionFilter

    search_fields = [
        "titulo",
        "hallazgo__titulo",
        "hallazgo__relevamiento__escuela__nom_est"
    ]
    
@require_GET
def escuela(request, cueanexo):

    escuela = PadronEscuelas.get_by_cueanexos(cueanexo)

    if escuela is None:
        return JsonResponse({}, status=404)

    return JsonResponse(escuela)