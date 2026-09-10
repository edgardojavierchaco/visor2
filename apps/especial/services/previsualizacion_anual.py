"""Servicios de previsualización anual de Educación Especial.

Estas funciones sólo leen la base y construyen un resumen en memoria.
"""

from django.utils import timezone

from ..models import (
    AlumnoSeccion,
    DocenteSeccion,
    EspecialAlumnoBanco,
    EspecialCiclo,
    EspecialDocenteBanco,
    SeccionEspecial,
)


def origen_anual_previsualizable(ciclo):
    """Acepta el actual abierto o el último cerrado sin sucesor."""
    if ciclo.actual and not ciclo.cerrado:
        return True
    if not ciclo.cerrado or ciclo.actual:
        return False
    return not EspecialCiclo.objects.filter(anio__gt=ciclo.anio).exists()


def prevalidar_generacion_anual(ciclo, cueanexo=""):
    """Cuenta datos proyectables sin crear ni actualizar ningún registro."""
    cueanexo = str(cueanexo or "").strip()
    siguiente_anio = ciclo.anio + 1 if ciclo else None
    resultado = {
        "origen": ciclo,
        "siguiente_anio": siguiente_anio,
        "fecha_simulada": timezone.localdate(),
        "cueanexo": cueanexo,
        "errores": [],
        "advertencias": [],
        "bloqueado": False,
        "secciones": 0,
        "alumnos": 0,
        "docentes": 0,
        "inscripciones": 0,
        "asignaciones": 0,
        "total_registros": 0,
        "por_cueanexo": [],
    }

    if ciclo is None or not origen_anual_previsualizable(ciclo):
        resultado["errores"].append(
            "El ciclo origen no es el actual abierto ni el último ciclo cerrado sin sucesor."
        )
    if not cueanexo:
        resultado["errores"].append("No existe un CUE-Anexo seleccionado.")
    if siguiente_anio is not None and EspecialCiclo.objects.filter(anio=siguiente_anio).exists():
        resultado["errores"].append(
            f"Ya existe el ciclo {siguiente_anio}; no se puede generar un ciclo duplicado."
        )

    if ciclo is None or not cueanexo or not origen_anual_previsualizable(ciclo):
        resultado["bloqueado"] = True
        return resultado

    secciones = SeccionEspecial.objects.filter(
        ciclo=ciclo,
        cueanexo=cueanexo,
        estado=SeccionEspecial.Estado.ACTIVO,
    )
    alumnos = EspecialAlumnoBanco.objects.filter(
        ciclo=ciclo,
        cueanexo=cueanexo,
        estado=EspecialAlumnoBanco.Estado.ACTIVO,
    )
    docentes = EspecialDocenteBanco.objects.filter(
        ciclo=ciclo,
        cueanexo=cueanexo,
        estado=EspecialDocenteBanco.Estado.ACTIVO,
    )
    inscripciones = AlumnoSeccion.objects.filter(
        seccion__in=secciones,
        estado=AlumnoSeccion.Estado.ACTIVO,
    )
    asignaciones = DocenteSeccion.objects.filter(
        seccion__in=secciones,
        estado=DocenteSeccion.Estado.ACTIVO,
    )

    resultado.update(
        secciones=secciones.count(),
        alumnos=alumnos.count(),
        docentes=docentes.count(),
        inscripciones=inscripciones.count(),
        asignaciones=asignaciones.count(),
    )
    resultado["total_registros"] = sum(
        resultado[campo]
        for campo in ("secciones", "alumnos", "docentes", "inscripciones", "asignaciones")
    )
    if not resultado["secciones"]:
        resultado["advertencias"].append(
            f"El ciclo {ciclo.anio} no posee secciones activas para proyectar."
        )
    if not resultado["alumnos"]:
        resultado["advertencias"].append("No hay alumnos activos en banco para proyectar.")
    if not resultado["docentes"]:
        resultado["advertencias"].append("No hay docentes activos en banco para proyectar.")
    if not resultado["inscripciones"]:
        resultado["advertencias"].append("No hay inscripciones activas para proyectar.")
    if not resultado["asignaciones"]:
        resultado["advertencias"].append("No hay asignaciones docentes activas para proyectar.")

    resultado["por_cueanexo"] = [{
        "cueanexo": cueanexo,
        "secciones": resultado["secciones"],
        "alumnos": resultado["alumnos"],
        "docentes": resultado["docentes"],
        "inscripciones": resultado["inscripciones"],
        "asignaciones": resultado["asignaciones"],
    }]
    return resultado
