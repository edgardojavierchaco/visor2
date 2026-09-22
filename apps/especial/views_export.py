# -*- coding: utf-8 -*-

from django.core.exceptions import PermissionDenied
from django.http import StreamingHttpResponse

from .models import EspecialCiclo
from .permisos import especial_required, get_permisos_especial_request
from .services.exportador_bnh import ExportadorBNH


@especial_required
def exportar_bnh(request):
    """Descarga el TXT BNH del ciclo vigente para administradores."""

    permisos = get_permisos_especial_request(request)
    if not permisos.get("es_admin"):
        raise PermissionDenied("La exportación BNH es exclusiva para administradores.")

    cueanexo = (request.GET.get("cueanexo") or "").strip() or None
    anio_raw = (request.GET.get("anio") or "").strip()
    anio = int(anio_raw) if anio_raw.isdigit() else None
    ciclo = (
        EspecialCiclo.objects.filter(anio=anio).first()
        if anio
        else EspecialCiclo.objects.filter(actual=True, activo=True).first()
    )
    ciclo = ciclo or EspecialCiclo.objects.filter(activo=True).order_by("-anio").first()
    anio_archivo = ciclo.anio if ciclo else anio or "actual"
    nombre_cue = cueanexo or "todos"
    contenido = ExportadorBNH().iterar(cueanexo=cueanexo, anio=anio)

    response = StreamingHttpResponse(
        contenido,
        content_type="text/plain; charset=utf-8",
    )
    response["Content-Disposition"] = (
        f'attachment; filename="especial_bnh_{nombre_cue}_{anio_archivo}.txt"'
    )
    return response
