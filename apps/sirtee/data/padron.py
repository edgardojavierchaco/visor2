from django.db import connection


class PadronEscuelas:
    """
    Capa única de acceso al padrón educativo.

    Fuente:
        public.v_capa_unica_ofertas_ant

    No es un modelo Django.
    Es un repositorio de lectura.
    """

    VIEW = "public.v_capa_unica_ofertas_ant"


    # --------------------------------------
    # EJECUTOR GENERAL
    # --------------------------------------

    @classmethod
    def _fetch(cls, sql, params=None):

        with connection.cursor() as cursor:

            cursor.execute(
                sql,
                params or []
            )

            columns = [
                col[0]
                for col in cursor.description
            ]

            return [
                dict(zip(columns, row))
                for row in cursor.fetchall()
            ]


    # --------------------------------------
    # TODAS LAS ESCUELAS
    # --------------------------------------

    @classmethod
    def all(cls, limit=None):

        sql = f"""
            SELECT
                cueanexo,
                nom_est,
                cui_loc as cui,
                oferta
            FROM {cls.VIEW}
            ORDER BY nom_est
        """

        params = []

        if limit:

            sql += " LIMIT %s"

            params.append(limit)


        return cls._fetch(
            sql,
            params
        )


    # --------------------------------------
    # BUSCAR
    # --------------------------------------

    @classmethod
    def search(cls, texto):

        sql = f"""
            SELECT
                cueanexo,
                nom_est,
                cui_loc as cui,
                oferta
            FROM {cls.VIEW}
            WHERE
                CAST(cueanexo AS TEXT) ILIKE %s
                OR nom_est ILIKE %s
            ORDER BY nom_est
            LIMIT 20
        """

        like = f"%{texto}%"

        return cls._fetch(
            sql,
            [
                like,
                like
            ]
        )


    # --------------------------------------
    # VARIAS ESCUELAS POR CUEANEXO
    # --------------------------------------

    @classmethod
    def get_by_cueanexos(cls, cueanexos):

        if not cueanexos:
            return {}


        sql = f"""
            SELECT
                cueanexo,
                nom_est,
                cui_loc as cui,
                oferta
            FROM {cls.VIEW}
            WHERE cueanexo IN %s
        """


        with connection.cursor() as cursor:

            cursor.execute(
                sql,
                [
                    tuple(cueanexos)
                ]
            )


            columns = [
                col[0]
                for col in cursor.description
            ]


            rows = [
                dict(zip(columns,row))
                for row in cursor.fetchall()
            ]


        return {
            str(row["cueanexo"]): row
            for row in rows
        }


    # --------------------------------------
    # ALIAS CORTO
    # --------------------------------------

    @classmethod
    def get(cls, cueanexo):

        return cls.get_by_cueanexos(
            cueanexo
        )