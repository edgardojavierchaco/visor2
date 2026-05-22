from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import redirect

from .models_integracion import (
    CefPadronOferta,
    PADRON_DB_ALIAS,
    normalizar_cueanexo,
    normalizar_cuil,
)
from .permisos import set_cef_cueanexo_activo


BIBLIOTECA_SESSION_KEY = "cueanexo_activo"
ACRONIMOS_BIBLIOTECA = {"BI", "BI ANEXO"}
ACRONIMO_CEF = "CEF"


def _normalizar_acronimo(valor):
    """
    Normaliza el acrónimo del servicio para rutear.
    """
    return " ".join(str(valor or "").strip().upper().split())


def _get_servicio_padron_usuario_o_403(user, cueanexo):
    """
    Busca el servicio por CUE-Anexo y valida que pertenezca al usuario logueado.

    Esta validación es intencionalmente previa al ruteo por acrónimo:
    - BI / BI ANEXO debe poder entrar al router.
    - CEF debe poder entrar al router.
    - servicios ajenos no deben poder seleccionarse.
    """
    cueanexo_normalizado = normalizar_cueanexo(cueanexo)

    if not cueanexo_normalizado:
        raise PermissionDenied("CUE-Anexo inválido.")

    servicio = (
        CefPadronOferta.objects.using(PADRON_DB_ALIAS)
        .filter(cueanexo=cueanexo_normalizado)
        .first()
    )

    if servicio is None:
        raise PermissionDenied("No se encontró el servicio seleccionado.")

    cuil_usuario = normalizar_cuil(getattr(user, "username", ""))
    cuil_responsable = normalizar_cuil(servicio.resploc_cuitcuil)

    if not cuil_usuario or cuil_usuario != cuil_responsable:
        raise PermissionDenied("No tenés permisos para seleccionar ese servicio.")

    return servicio


@login_required
def seleccionar_servicio_por_acronimo(request, cueanexo):
    """
    Router real por acrónimo.

    Reglas:
    - BI / BI ANEXO -> Biblioteca.
    - CEF -> CEF alumnos.
    - Otro acrónimo -> mensaje controlado.

    Importante:
    - Biblioteca usa request.session["cueanexo_activo"].
    - CEF usa request.session["cef_cueanexo_activo"].
    """
    servicio = _get_servicio_padron_usuario_o_403(request.user, cueanexo)
    cueanexo_normalizado = normalizar_cueanexo(servicio.cueanexo)
    acronimo = _normalizar_acronimo(servicio.acronimo)

    if acronimo in ACRONIMOS_BIBLIOTECA:
        request.session[BIBLIOTECA_SESSION_KEY] = cueanexo_normalizado
        request.session.modified = True
        return redirect("bibliotecas:continuar_carga")

    if acronimo == ACRONIMO_CEF:
        set_cef_cueanexo_activo(request, cueanexo_normalizado)
        return redirect("cef:alumnos")

    return HttpResponse(
        (
            "El servicio seleccionado no tiene un destino configurado para este "
            f"módulo. Acrónimo detectado: {acronimo or 'Sin dato'}."
        ),
        status=400,
        content_type="text/plain; charset=utf-8",
    )
