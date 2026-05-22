import re

from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from .models_integracion import get_datos_establecimiento_cef
from .permisos import (
    cef_director_required,
    get_cefs_cargables_usuario,
    get_cueanexos_cargables_usuario,
    resolver_cef_cueanexo_activo,
    set_cef_cueanexo_activo,
    validar_cueanexo_director_o_403,
)


LONGITUD_CUIL = 11
COEFICIENTES_CUIL = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]


def normalizar_cuil_alumno(valor):
    return re.sub(r"[^\d]", "", str(valor or ""))


def validar_cuil(valor):
    if not valor:
        return

    cuil = normalizar_cuil_alumno(valor)
    if len(cuil) != LONGITUD_CUIL:
        raise ValidationError("CUIL debe tener 11 digitos")

    if len(set(cuil)) == 1:
        raise ValidationError("CUIL invalido")

    suma = sum(int(cuil[i]) * COEFICIENTES_CUIL[i] for i in range(10))
    resto = suma % 11
    digito = 11 - resto
    if digito == 11:
        digito = 0
    elif digito == 10:
        digito = 9

    if digito != int(cuil[-1]):
        raise ValidationError("CUIL invalido: digito verificador incorrecto")


def validar_cuil_alumno(valor):
    cuil = normalizar_cuil_alumno(valor)
    errores = []

    if not cuil:
        errores.append("El CUIL es obligatorio.")
    elif len(cuil) != LONGITUD_CUIL:
        errores.append("CUIL debe tener 11 digitos.")
    elif not cuil.isdigit():
        errores.append("CUIL debe contener solo numeros.")
    elif len(set(cuil)) == 1:
        errores.append("CUIL invalido.")

    if not errores:
        try:
            validar_cuil(cuil)
        except ValidationError as exc:
            errores.extend(getattr(exc, "messages", None) or [str(exc)])

    if errores:
        return {
            "valido": False,
            "cuil": cuil,
            "mensaje": "CUIL invalido.",
            "errores": errores,
        }

    return {
        "valido": True,
        "cuil": cuil,
        "mensaje": "CUIL valido.",
        "errores": [],
    }


@cef_director_required
def alumnos_inicio(request):
    cueanexo_activo = resolver_cef_cueanexo_activo(request)
    cefs_cargables = get_cefs_cargables_usuario(request.user)
    cueanexos_cargables = get_cueanexos_cargables_usuario(request.user)

    datos_establecimiento = None
    if cueanexo_activo:
        datos_establecimiento = get_datos_establecimiento_cef(cueanexo_activo)

    context = {
        "title": "Alumnos CEF",
        "active_menu": "alumnos",
        "cef_cueanexo_activo": cueanexo_activo,
        "cefs_cargables": cefs_cargables,
        "cueanexos_cargables": cueanexos_cargables,
        "datos_establecimiento": datos_establecimiento,
    }

    return render(request, "cef/alumnos_cef.html", context)


@cef_director_required
def api_validar_cuil_alumno(request):
    cuil = request.POST.get("cuil") or request.GET.get("cuil") or ""
    resultado = validar_cuil_alumno(cuil)
    return JsonResponse(resultado)


@cef_director_required
@require_POST
def api_seleccionar_cef_carga(request):
    cueanexo = request.POST.get("cueanexo", "")
    cueanexo_validado = validar_cueanexo_director_o_403(
        request.user,
        cueanexo,
    )

    set_cef_cueanexo_activo(request, cueanexo_validado)

    return JsonResponse(
        {
            "ok": True,
            "cueanexo_activo": cueanexo_validado,
            "mensaje": "CEF activo actualizado.",
        }
    )
