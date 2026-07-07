import json
import re

from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_POST

from apps.bnhalumnos.models import Alumno
from apps.consultasge.models_padron import CapaUnicaOfertas

from .models import (
    CatalogoTipoEstructuraEspecial,
    CatalogoTipoRangoEtario,
    Especial_AlumnoSeccion,
    SeccionEspecial,
    modalidad_dictado_tipo,
    seccion_tipo,
    turno_tipo,
)


def carga_seccion_especial_view(request):
    """Renderiza el formulario de carga de secciones de Educación Especial.

    Los catálogos se pasan por contexto para que el template arme los <select>
    con {% for item in ... %}. Si agregás un catálogo nuevo al modelo, también
    hay que agregarlo aquí para que aparezca en el formulario.
    """
    contexto = {
        "tipos_estructura_especial": CatalogoTipoEstructuraEspecial.objects.all().order_by("descripcion"),
        "rangos_etarios": CatalogoTipoRangoEtario.objects.all().order_by("cd_tiporangoetario"),
        "modalidades_dictado": modalidad_dictado_tipo.objects.all().order_by("descripcion"),
        "turnos": turno_tipo.objects.all().order_by("descripcion"),
        "tipos_seccion": seccion_tipo.objects.all().order_by("descripcion"),
    }
    return render(request, "especial/carga_seccion_especial.html", contexto)


@require_GET
def buscar_cueanexo(request):
    """Búsqueda AJAX de establecimientos para el combobox de CUE-Anexo.

    OJO: asumí que CapaUnicaOfertas tiene los campos 'cueanexo' (código) y
    'nombre' (nombre del establecimiento). Si en tu modelo real se llaman
    distinto, ajustá los nombres de campo en el filtro y en el diccionario
    de resultados de abajo.
    """
    query = request.GET.get("q", "").strip()
    if len(query) < 3:
        return JsonResponse({"resultados": []})

    establecimientos = CapaUnicaOfertas.objects.filter(
        models_q_cueanexo_or_nombre(query)
    )[:20]

    resultados = [
        {
            "id": est.pk,
            "cueanexo": getattr(est, "cueanexo", ""),
            "nombre": getattr(est, "nombre", ""),
        }
        for est in establecimientos
    ]
    return JsonResponse({"resultados": resultados})


def models_q_cueanexo_or_nombre(query):
    """Construye el filtro OR para buscar por código o por nombre.

    Separado en su propia función para que sea fácil de adaptar si los
    nombres de campo reales de CapaUnicaOfertas son distintos.
    """
    from django.db.models import Q

    return Q(cueanexo__icontains=query) | Q(nombre__icontains=query)


@require_POST
def guardar_carga_seccion(request):
    """Guarda la sección de Educación Especial junto con los alumnos asignados.

    Espera un JSON con esta forma:
    {
        "seccion": {
            "cueanexo": "<id de CapaUnicaOfertas>",
            "tipo_estructura_especial": "<id>",
            "rango_etario": "<id>",
            "modalidad": "<id>",
            "ciclo": "2026",
            "nombre_seccion": "...",
            "cd_tipo_seccion": "<id>",
            "turno": "<id>",
            "capacidad_total": "30",
            "lugar_dictado": "...",
            "descripcion": "..."
        },
        "alumnos": [1, 2, 3]
    }
    """
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"ok": False, "error": "El cuerpo de la solicitud no es JSON válido."}, status=400)

    datos_seccion = payload.get("seccion", {})
    ids_alumnos = payload.get("alumnos", [])

    errores = validar_datos_seccion(datos_seccion)
    if errores:
        return JsonResponse({"ok": False, "errors": errores}, status=400)

    try:
        with transaction.atomic():
            seccion = crear_seccion_especial(datos_seccion)
            asignar_alumnos_a_seccion(seccion, ids_alumnos)
    except Exception as exc:
        return JsonResponse({"ok": False, "error": f"No se pudo guardar la sección: {exc}"}, status=500)

    return JsonResponse({"ok": True, "id_seccion": seccion.pk})


def validar_datos_seccion(datos):
    """Validación mínima en backend; el frontend ya valida lo mismo, pero
    nunca hay que confiar solo en JavaScript."""
    errores = {}
    campos_obligatorios = [
        "cueanexo",
        "tipo_estructura_especial",
        "rango_etario",
        "modalidad",
        "nombre_seccion",
        "cd_tipo_seccion",
        "turno",
        "ciclo",
    ]
    for campo in campos_obligatorios:
        if not str(datos.get(campo, "")).strip():
            errores[campo] = "Este campo es obligatorio."

    try:
        capacidad = int(datos.get("capacidad_total", 0))
        if capacidad < 1:
            errores["capacidad_total"] = "La capacidad debe ser mayor a 0."
    except (TypeError, ValueError):
        errores["capacidad_total"] = "La capacidad debe ser un número entero."

    return errores


def generar_id_seccion(datos, cueanexo_obj):
    """Genera el id de SeccionEspecial concatenando los campos disponibles.

    El docstring original del modelo mencionaba cd_oferta_padron y cd_grado,
    pero esos campos no existen en la versión actual de SeccionEspecial, así
    que se reemplazan por tipo_estructura_especial y rango_etario, que son
    los que efectivamente clasifican la oferta en Educación Especial.
    """
    nombre_limpio = re.sub(r"[^A-Za-z0-9]", "", datos["nombre_seccion"]).upper()
    partes = [
        str(getattr(cueanexo_obj, "cueanexo", cueanexo_obj.pk)),
        str(datos["tipo_estructura_especial"]),
        str(datos["rango_etario"]),
        str(datos["cd_tipo_seccion"]),
        str(datos["turno"]),
        str(datos["ciclo"]),
        nombre_limpio,
    ]
    id_generado = "".join(partes)
    return id_generado[:100]


def crear_seccion_especial(datos):
    cueanexo_obj = get_object_or_404(CapaUnicaOfertas, pk=datos["cueanexo"])
    tipo_estructura = get_object_or_404(CatalogoTipoEstructuraEspecial, pk=datos["tipo_estructura_especial"])
    rango_etario = get_object_or_404(CatalogoTipoRangoEtario, pk=datos["rango_etario"])
    modalidad = get_object_or_404(modalidad_dictado_tipo, pk=datos["modalidad"])
    tipo_seccion = get_object_or_404(seccion_tipo, pk=datos["cd_tipo_seccion"])
    turno = get_object_or_404(turno_tipo, pk=datos["turno"])

    seccion = SeccionEspecial(
        id=generar_id_seccion(datos, cueanexo_obj),
        cueanexo=cueanexo_obj,
        tipo_estructura_especial=tipo_estructura,
        rango_etario=rango_etario,
        modalidad=modalidad,
        cd_tipo_seccion=tipo_seccion,
        turno=turno,
        nombre_seccion=datos["nombre_seccion"].strip(),
        descripcion=datos.get("descripcion", "").strip(),
        capacidad_total=int(datos["capacidad_total"]),
        ciclo=int(datos["ciclo"]),
        lugar_dictado=datos.get("lugar_dictado", "").strip(),
    )
    seccion.save()
    return seccion


def asignar_alumnos_a_seccion(seccion, ids_alumnos):
    for id_alumno in ids_alumnos:
        alumno = get_object_or_404(Alumno, pk=id_alumno)
        Especial_AlumnoSeccion.objects.get_or_create(
            id_alumno=alumno,
            id_seccion=seccion,
        )