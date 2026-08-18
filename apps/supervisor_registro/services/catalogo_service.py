# services/catalogo_service.py
from apps.supervisa2.models import (
    SituacionRevista,
    NivelModalidad,
)

from .permission_service import get_regiones_queryset


class CatalogoService:
    @staticmethod
    def contexto(user=None):
        context = {
            "situaciones": SituacionRevista.objects.all().order_by("nombre"),
            "niveles": NivelModalidad.objects.all().order_by("nombre"),
            "regiones": get_regiones_queryset(user) if user else [],
        }
        return context