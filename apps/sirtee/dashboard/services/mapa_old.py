from django.db import connection



class MapaSIRTEE:


    """
    Servicio de información territorial
    para el dashboard operativo SIRTEE.
    """



    # ======================================================
    # ESCUELAS OPERATIVAS
    # ======================================================

    @staticmethod
    def escuelas_operativas(
        region=None,
        departamento=None,
        criticidad=None,
        estado_intervencion=None
    ):


        sql = """

        SELECT


            r.id AS relevamiento_id,


            r.cueanexo,


            v.nom_est,


            v.lat,


            v.long,


            v.region_loc,


            v.departamento,


            v.localidad,



            COUNT(
                DISTINCT h.id
            )
            AS cantidad_hallazgos,



            COUNT(

                DISTINCT

                CASE

                    WHEN c.codigo = 'CRITICA'

                    THEN h.id

                END

            )
            AS hallazgos_criticos,



            STRING_AGG(

                DISTINCT c.nombre,

                ', '

            )
            AS criticidades,



            COUNT(

                DISTINCT

                CASE

                    WHEN ei.codigo NOT IN (

                        'FINALIZADA',

                        'CANCELADA'

                    )

                    THEN i.id

                END

            )
            AS intervenciones_pendientes,



            STRING_AGG(

                DISTINCT ei.nombre,

                ', '

            )
            AS estados_intervencion



        FROM sirtee_relevamientos r



        INNER JOIN

        public.v_capa_unica_ofertas_ant v


        ON

        v.cueanexo =

        CAST(r.cueanexo AS bigint)



        LEFT JOIN

        sirtee_hallazgos h


        ON

        h.relevamiento_id = r.id



        LEFT JOIN

        sirtee_cat_criticidad c


        ON

        c.id = h.criticidad_id



        LEFT JOIN

        sirtee_intervenciones i


        ON

        i.hallazgo_id = h.id



        LEFT JOIN

        sirtee_cat_estado_intervencion ei


        ON

        ei.id = i.estado_id



        WHERE


        v.lat IS NOT NULL


        AND


        v.long IS NOT NULL



        """



        params = []



        # ==================================================
        # FILTROS
        # ==================================================


        if region:


            sql += """

            AND v.region_loc = %s

            """


            params.append(
                region
            )



        if departamento:


            sql += """

            AND v.departamento = %s

            """


            params.append(
                departamento
            )



        if criticidad:


            sql += """

            AND c.codigo = %s

            """


            params.append(
                criticidad
            )



        if estado_intervencion:


            sql += """

            AND ei.codigo = %s

            """


            params.append(
                estado_intervencion
            )



        # ==================================================
        # AGRUPACIÓN
        # ==================================================


        sql += """

        GROUP BY


            r.id,

            r.cueanexo,

            v.nom_est,

            v.lat,

            v.long,

            v.region_loc,

            v.departamento,

            v.localidad



        ORDER BY


            hallazgos_criticos DESC,

            cantidad_hallazgos DESC



        """



        with connection.cursor() as cursor:


            cursor.execute(
                sql,
                params
            )


            columnas = [

                col[0]

                for col in cursor.description

            ]



            resultado = []


            for fila in cursor.fetchall():


                resultado.append(

                    dict(

                        zip(

                            columnas,

                            fila

                        )

                    )

                )



            return resultado



    # ======================================================
    # REGIONES
    # ======================================================


    @staticmethod
    def regiones():


        with connection.cursor() as cursor:


            cursor.execute(

                """

                SELECT DISTINCT

                    region_loc


                FROM

                    public.v_capa_unica_ofertas_ant


                WHERE

                    region_loc IS NOT NULL


                ORDER BY

                    region_loc


                """

            )



            return [

                fila[0]

                for fila in cursor.fetchall()

            ]



    # ======================================================
    # DEPARTAMENTOS
    # ======================================================


    @staticmethod
    def departamentos():


        with connection.cursor() as cursor:


            cursor.execute(

                """

                SELECT DISTINCT

                    departamento


                FROM

                    public.v_capa_unica_ofertas_ant


                WHERE

                    departamento IS NOT NULL


                ORDER BY

                    departamento


                """

            )



            return [

                fila[0]

                for fila in cursor.fetchall()

            ]