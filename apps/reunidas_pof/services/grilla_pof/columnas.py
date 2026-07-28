import re
import unicodedata


def obtener_clave_columna(columna):
    """
    Resuelve una etiqueta visible a la clave logica comun de la grilla POF.

    - Normaliza acentos, mayusculas y puntuacion de labels historicos.
    - Conserva compatibilidad con nombres visibles inconsistentes por nivel.
    - Sirve como base neutral para detalle, preview y filas exportables.
    """
    texto = str(columna or "").strip().lower()
    texto = "".join(
        caracter
        for caracter in unicodedata.normalize("NFD", texto)
        if unicodedata.category(caracter) != "Mn"
    )
    compacto = re.sub(r"[^a-z0-9]+", "", texto)

    if "cuecui" in compacto:
        return "cue_cui"
    if "subcuof" in compacto:
        return "anexo"
    if "subcue" in compacto:
        return "subcue"
    if compacto == "cue":
        return "cue"
    if compacto == "cui":
        return "cui"
    if "cuof" in compacto:
        return "cuof"
    if "ceic" in compacto:
        return "ceic"
    if "totalpuntoscargoshorascatedra" in compacto:
        return "total_general"
    if "totalgeneral" in compacto:
        return "total_general"
    if "totalhorascatedra" in compacto:
        return "total_horas_catedra"
    if "puntoshorascatedra" in compacto:
        return "puntos_horas_catedra"
    if "totalpuntos" in compacto:
        return "total_puntos"
    if compacto == "total":
        return "total"
    if "puntos" in compacto:
        return "puntos"
    if "cantidadcargos" in compacto:
        return "cantidad_cargos"
    if "cantidadhoras" in compacto:
        return "cantidad_horas"
    if "cantidad" in compacto:
        return "cantidad"
    if "unidad" in compacto:
        return "unidad"
    if "estadopof" in compacto:
        return "estado_pof"
    if compacto == "anio":
        return "anio"
    if "proyectoespecial" in compacto:
        return "proyecto_especial"
    if "resolucion" in compacto:
        return "resolucion"
    if "categor" in compacto and "jornada" in compacto:
        return "categoria_jornada"
    if "categor" in compacto:
        return "categoria"
    if "jornada" in compacto:
        return "jornada"
    if "localidad" in compacto and "departamento" in compacto:
        return "ubicacion_completa"
    if "ubicaci" in compacto or "domicilio" in compacto:
        return "ubicacion"
    if "localidad" in compacto:
        return "localidad"
    if "departamento" in compacto:
        return "departamento"
    if "ambito" in compacto or "mbito" in compacto or "zona" in compacto:
        return "ambito"
    if "region" in compacto or "regi" in compacto or compacto in {"reg", "exr"}:
        return "region"
    if "establecimiento" in compacto:
        return "establecimiento"
    if "nombre" in compacto:
        return "nombre"
    if "oferta" in compacto:
        return "oferta"
    if "modalidad" in compacto or "modaidad" in compacto:
        return "modalidad"
    if "tipo" in compacto or "sedeanexo" in compacto:
        return "tipo_anexo"
    if "nanexo" in compacto:
        return "anexo"
    if (
        compacto in {"n", "nro"}
        or (compacto.startswith("n") and len(compacto) <= 4)
        or "estab" in compacto
        or "bp" in compacto
        or ("centrodeeducaci" in compacto and "fisica" in compacto)
    ):
        return "numero_establecimiento"
    if "cargo" in compacto or "denominaci" in compacto:
        return "cargo"

    return columna
