from django.db import connection

from apps.usuarios.models import Referentes


CATEGORIA_REFERENTE = "refestadistica"


def es_referente_estadistica(usuario):
    """
    Verifica que el usuario tenga el rol refestadistica.
    """
    if not usuario or not usuario.is_authenticated:
        return False

    if not usuario.activo:
        return False

    perfil = getattr(usuario, "perfil", None)

    return bool(
        perfil
        and perfil.rol
        and perfil.rol.categoria_acceso == CATEGORIA_REFERENTE
    )


def obtener_referente(usuario):
    """
    Recupera el referente activo asociado al CUIL.
    """
    if not es_referente_estadistica(usuario):
        return None

    return Referentes.objects.filter(
        cuil=usuario.username,
        estado=True
    ).first()


def obtener_regiones_referente(usuario):
    """
    Devuelve las regionales asignadas.

    Ejemplo:
        '1, 2, 5' -> ['1', '2', '5']
    """
    referente = obtener_referente(usuario)

    if not referente:
        return []

    return list(dict.fromkeys(
        region.strip()
        for region in (referente.region or "").split(",")
        if region.strip()
    ))


def obtener_cueanexos_referente(usuario):
    """
    Recupera únicamente los CUEANEXO
    correspondientes a las regionales autorizadas.
    """
    regiones = obtener_regiones_referente(usuario)

    if not regiones:
        return []

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT DISTINCT
                v.cueanexo
            FROM public.v_capa_unica_ofertas_ant v
            WHERE TRIM(v.region_loc::text) = ANY(%s::text[])
              AND v.cueanexo IS NOT NULL
        """, [regiones])

        return [
            str(fila[0]).strip()
            for fila in cursor.fetchall()
        ]


def obtener_establecimientos_referente(usuario):
    """
    Recupera los establecimientos autorizados
    con sus datos institucionales.
    """
    regiones = obtener_regiones_referente(usuario)

    if not regiones:
        return []

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT DISTINCT
                v.cueanexo,
                v.nom_est,
                v.region_loc,
                v.oferta
            FROM public.v_capa_unica_ofertas_ant v
            WHERE TRIM(v.region_loc::text) = ANY(%s::text[])
              AND v.cueanexo IS NOT NULL
            ORDER BY v.region_loc, v.nom_est
        """, [regiones])

        columnas = [
            columna[0]
            for columna in cursor.description
        ]

        return [
            dict(zip(columnas, fila))
            for fila in cursor.fetchall()
        ]