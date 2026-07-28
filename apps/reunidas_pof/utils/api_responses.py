from django.http import JsonResponse


def normalizar_errores(errores):
    if not errores:
        return {}

    if hasattr(errores, "message_dict"):
        errores = errores.message_dict
    elif hasattr(errores, "messages"):
        errores = errores.messages

    if isinstance(errores, str):
        return {"__all__": [errores]}

    if isinstance(errores, (list, tuple)):
        return {"__all__": [str(error) for error in errores]}

    if isinstance(errores, dict):
        normalizados = {}
        for campo, valor in errores.items():
            clave = str(campo)
            if isinstance(valor, dict):
                normalizados[clave] = normalizar_errores(valor)
            elif isinstance(valor, (list, tuple)):
                normalizados[clave] = [
                    str(item) for item in valor if item is not None
                ]
            elif valor is None:
                normalizados[clave] = []
            else:
                normalizados[clave] = [str(valor)]
        return normalizados

    return {"__all__": [str(errores)]}


def api_ok(mensaje="", data=None, status=200):
    return JsonResponse(
        {
            "ok": True,
            "tipo": "ok",
            "mensaje": mensaje,
            "data": data or {},
        },
        status=status,
    )


def _api_error(tipo, mensaje, errores=None, status=400):
    return JsonResponse(
        {
            "ok": False,
            "tipo": tipo,
            "mensaje": mensaje,
            "errores": normalizar_errores(errores),
        },
        status=status,
    )


def api_error_validacion(mensaje, errores=None, status=400):
    return _api_error("validacion", mensaje, errores, status)


def api_error_permiso(
    mensaje="Esta acci\u00f3n no est\u00e1 disponible para tu usuario.",
    status=403,
):
    return _api_error("permiso", mensaje, {}, status)


def api_error_sesion(
    mensaje="La sesi\u00f3n expir\u00f3 o la solicitud no es v\u00e1lida. Recarg\u00e1 la p\u00e1gina.",
    status=403,
):
    return _api_error("sesion", mensaje, {}, status)


def api_error_no_encontrado(
    mensaje="No se encontr\u00f3 el registro solicitado.",
    errores=None,
    status=404,
):
    return _api_error("no_encontrado", mensaje, errores, status)


def api_error_sin_cambios(
    mensaje="No hay cambios para guardar.",
    status=400,
):
    return _api_error("sin_cambios", mensaje, {}, status)


def api_error_interno(
    mensaje="Ocurri\u00f3 un error interno. Informe al administrador.",
    status=500,
):
    return _api_error("interno", mensaje, {}, status)
