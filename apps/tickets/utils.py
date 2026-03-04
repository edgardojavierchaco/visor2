from django.db import connection
from apps.usuarios.models import UsuariosVisualizador


def obtener_region_escuela(cue):

    with connection.cursor() as cursor:

        cursor.execute("""
            SELECT region_loc
            FROM v_capa_unica_ofertas
            WHERE cueanexo = %s
            LIMIT 1
        """,[cue])

        row = cursor.fetchone()

    if row:
        return row[0]

    return None


def obtener_gestor_region(region):

    with connection.cursor() as cursor:

        cursor.execute("""
            SELECT username
            FROM gestores_regionales
            WHERE regional = %s
            LIMIT 1
        """,[region])

        row = cursor.fetchone()

    if not row:
        return None

    username = row[0]

    return UsuariosVisualizador.objects.get(username=username)