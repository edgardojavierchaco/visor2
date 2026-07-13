from django.db import connection


class MapaSIRTEE:
    """
    Servicio territorial del Dashboard SIRTEE.

    Cada registro representa UNA ESCUELA.
    Los valores de hallazgos e intervenciones se obtienen
    acumulando TODOS los relevamientos de dicha escuela.
    """

    VIEW = "public.v_capa_unica_ofertas_ant"

    # =====================================================
    # ESCUELAS OPERATIVAS
    # =====================================================

    @staticmethod
    def escuelas_operativas(
        region=None,
        departamento=None,
        criticidad=None,
        estado_intervencion=None,
    ):

        sql = f"""
        SELECT

            r.cueanexo,

            v.nom_est,
            v.cui_loc,
            v.oferta,

            v.lat,
            v.long,

            v.region_loc,
            v.departamento,
            v.localidad,

            COUNT(DISTINCT r.id)
                AS cantidad_relevamientos,

            COUNT(DISTINCT h.id)
                AS cantidad_hallazgos,

            COUNT(
                DISTINCT
                CASE
                    WHEN c.codigo='CRITICA'
                    THEN h.id
                END
            )
                AS hallazgos_criticos,

            COUNT(
                DISTINCT
                CASE
                    WHEN ei.codigo NOT IN
                    (
                        'FINALIZADA',
                        'CANCELADA'
                    )
                    THEN i.id
                END
            )
                AS intervenciones_pendientes,

            STRING_AGG(
                DISTINCT c.nombre,
                ', '
            )
                AS criticidades,

            STRING_AGG(
                DISTINCT ei.nombre,
                ', '
            )
                AS estados_intervencion

        FROM sirtee_relevamientos r

        INNER JOIN {MapaSIRTEE.VIEW} v
            ON v.cueanexo = CAST(r.cueanexo AS bigint)

        LEFT JOIN sirtee_hallazgos h
            ON h.relevamiento_id = r.id

        LEFT JOIN sirtee_cat_criticidad c
            ON c.id = h.criticidad_id

        LEFT JOIN sirtee_intervenciones i
            ON i.hallazgo_id = h.id

        LEFT JOIN sirtee_cat_estado_intervencion ei
            ON ei.id = i.estado_id

        WHERE

            v.lat IS NOT NULL

        AND

            v.long IS NOT NULL
        """

        params = []

        # -----------------------------------------
        # FILTROS
        # -----------------------------------------

        if region:

            sql += """
            AND UPPER(v.region_loc)=UPPER(%s)
            """

            params.append(region)

        if departamento:

            sql += """
            AND UPPER(v.departamento)=UPPER(%s)
            """

            params.append(departamento)

        if criticidad:

            sql += """
            AND c.codigo=%s
            """

            params.append(criticidad)

        if estado_intervencion:

            sql += """
            AND ei.codigo=%s
            """

            params.append(estado_intervencion)

        # -----------------------------------------
        # AGRUPACIÓN
        # -----------------------------------------

        sql += """

        GROUP BY

            r.cueanexo,

            v.nom_est,
            v.cui_loc,
            v.oferta,

            v.lat,
            v.long,

            v.region_loc,
            v.departamento,
            v.localidad

        ORDER BY

            hallazgos_criticos DESC,

            cantidad_hallazgos DESC,

            cantidad_relevamientos DESC,

            v.nom_est

        """

        with connection.cursor() as cursor:

            cursor.execute(sql, params)

            columnas = [
                col[0]
                for col in cursor.description
            ]

            resultado = []

            for fila in cursor.fetchall():

                registro = dict(
                    zip(
                        columnas,
                        fila
                    )
                )

                registro["cantidad_relevamientos"] = (
                    registro["cantidad_relevamientos"] or 0
                )

                registro["cantidad_hallazgos"] = (
                    registro["cantidad_hallazgos"] or 0
                )

                registro["hallazgos_criticos"] = (
                    registro["hallazgos_criticos"] or 0
                )

                registro["intervenciones_pendientes"] = (
                    registro["intervenciones_pendientes"] or 0
                )

                registro["criticidades"] = (
                    registro["criticidades"] or "-"
                )

                registro["estados_intervencion"] = (
                    registro["estados_intervencion"] or "-"
                )

                resultado.append(registro)

            return resultado

    # =====================================================
    # REGIONES
    # =====================================================

    @staticmethod
    def regiones():

        with connection.cursor() as cursor:

            cursor.execute(
                f"""
                SELECT DISTINCT
                    region_loc
                FROM {MapaSIRTEE.VIEW}
                WHERE region_loc IS NOT NULL
                ORDER BY region_loc
                """
            )

            return [
                fila[0]
                for fila in cursor.fetchall()
            ]

    # =====================================================
    # DEPARTAMENTOS
    # =====================================================

    @staticmethod
    def departamentos():

        with connection.cursor() as cursor:

            cursor.execute(
                f"""
                SELECT DISTINCT
                    departamento
                FROM {MapaSIRTEE.VIEW}
                WHERE departamento IS NOT NULL
                ORDER BY departamento
                """
            )

            return [
                fila[0]
                for fila in cursor.fetchall()
            ]