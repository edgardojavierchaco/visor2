import os
import psycopg2
from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required
def filtrar_tablas_view_directores(request):
    """
    Vista principal de datos institucionales del usuario autenticado.
    Trae datos de la DB principal y planes desde otra DB.
    """
    cuil = request.user.username  # Username = CUIL

    # --- Función reutilizable para consultas ---
    def fetch_dicts(conn, query, params=None):
        with conn.cursor() as cursor:
            cursor.execute(query, params or [])
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    planes = {}  # Inicializar para evitar UnboundLocalError

    # --- Conexión DB principal ---
    try:
        conn_main = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST'),
            user=os.getenv('POSTGRES_USER'),
            password=os.getenv('POSTGRES_PASSWORD'),
            database=os.getenv('DB_NAME1')
        )
    except psycopg2.Error as e:
        return render(request, 'directores/institucional.html', {'error': f'Error DB principal: {e}'})

    try:
        # Cueanexos del usuario
        cueanexos_q = """
            SELECT DISTINCT cueanexo
            FROM padron_ofertas
            WHERE REGEXP_REPLACE(resploc_cuitcuil, '[^0-9]', '', 'g') = %s
        """
        cueanexos_rows = fetch_dicts(conn_main, cueanexos_q, [cuil])
        cueanexos = [row['cueanexo'] for row in cueanexos_rows]

        if not cueanexos:
            return render(request, 'directores/institucional.html', {
                'institucional': [], 'cueanexos_data': [], 'anexos': [],
                'tiene_bibliotecas': False, 'comun_primaria': False,
                'comun_secundaria': False, 'privado': False
            })

        # --- Datos institucionales ---
        institucional_q = """
            SELECT *
            FROM padron_ofertas
            WHERE REGEXP_REPLACE(resploc_cuitcuil, '[^0-9]', '', 'g') = %s
        """
        institucional = fetch_dicts(conn_main, institucional_q, [cuil])

        # --- Anexos ---
        placeholders = ','.join(['%s'] * len(cueanexos))
        anexos_q = f"""
            SELECT DISTINCT po.cueanexo, po.anexo, po.calle, po.numero, po.estado_loc
            FROM padron_ofertas po
            WHERE po.cueanexo IN ({placeholders}) AND po.estado_loc = %s
        """
        anexos = fetch_dicts(conn_main, anexos_q, cueanexos + ['Activo'])

        # --- Ofertas ---
        ofertas_q = """
            SELECT *
            FROM padron_ofertas
            WHERE REGEXP_REPLACE(resploc_cuitcuil, '[^0-9]', '', 'g') = %s
              AND est_oferta = %s
        """
        ofertas = fetch_dicts(conn_main, ofertas_q, [cuil, 'Activo'])

        # Clasificaciones rápidas
        for o in ofertas:
            o['es_biblioteca'] = o.get('acronimo_oferta', '').startswith('BI')
            o['es_privado'] = o.get('sector') == 'Privado'

        tiene_bibliotecas = any(o['es_biblioteca'] for o in ofertas)
        comun_primaria = any(o.get('oferta') == 'Común - Primaria de 7 años ' for o in ofertas)
        comun_secundaria = any(o.get('oferta') == 'Común - Secundaria Completa req. 7 años ' for o in ofertas)
        privado = any(o['es_privado'] for o in ofertas)

        # --- PLANES DE ESTUDIO (DB separada) ---
        try:
            conn_planes = psycopg2.connect(
                host=os.getenv('POSTGRES_HOST'),
                user=os.getenv('POSTGRES_USER'),
                password=os.getenv('POSTGRES_PASSWORD'),
                database=os.getenv('POSTGRES_DB')
            )
        except psycopg2.Error as e:
            print("Error al conectar a DB planes:", e)
        else:
            try:
                cueanexos_str = ','.join(f"'{c}'" for c in cueanexos)
                planes_q = f"""
                    SELECT cueanexo, valor AS plan_estudio
                    FROM public.planes_estudios
                    WHERE REGEXP_REPLACE(cueanexo, '[^0-9]', '', 'g') IN ({cueanexos_str})
                    ORDER BY valor
                """
                with conn_planes.cursor() as cur:
                    cur.execute(planes_q)
                    rows = cur.fetchall()

                # Convertir a diccionario {cueanexo: [plan1, plan2, ...]}
                for cue_val, plan_val in rows:
                    planes.setdefault(cue_val, []).append(plan_val)

            except Exception as e:
                print("Error al obtener planes:", e)
            finally:
                conn_planes.close()

        # --- Combinar ofertas y planes por cueanexo para el template ---
        ofertas_por_cueanexo = {}
        for cue in cueanexos:
            ofertas_por_cueanexo[cue] = [o for o in ofertas if o.get('cueanexo') == cue]

        cueanexos_data = []
        for cue in cueanexos:
            cueanexos_data.append({
                'cueanexo': cue,
                'ofertas': ofertas_por_cueanexo.get(cue, []),
                'planes': planes.get(cue, [])
            })

    except psycopg2.Error as e:
        conn_main.close()
        return render(request, 'directores/institucional.html', {'error': f'Error consulta: {e}'})

    conn_main.close()

    context = {
        'institucional': institucional,
        'cueanexos_data': cueanexos_data,
        'anexos': anexos,
        'tiene_bibliotecas': tiene_bibliotecas,
        'comun_primaria': comun_primaria,
        'comun_secundaria': comun_secundaria,
        'privado': privado
    }

    return render(request, 'directores/institucional.html', context)


@login_required
def filter_matricula_views_directores(request):
    """
    Vista principal de matrícula UEGP para un CUEANEXO específico.
    Permite filtrar por grado si se pasa 'grado' en GET.
    """
    # Toma el cueanexo de GET si existe, sino usa el username
    cueanexo = request.GET.get('cueanexo')
    grado = request.GET.get('grado', None)

    # Asegurarse de que sea string
    cueanexo = str(cueanexo)
    
    try:
        connection = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST'),
            user=os.getenv('POSTGRES_USER'),
            password=os.getenv('POSTGRES_PASSWORD'),
            database=os.getenv('POSTGRES_DB')
        )
        cursor = connection.cursor()
    except psycopg2.Error as e:
        return render(request, 'error.html', {'mensaje': f'Error al conectar a la DB: {e}'})

    resultados_detalle = []

    try:
        # Obtener ofertas activas para el cueanexo (tratar cueanexo como texto)
        cursor.execute(
            "SELECT DISTINCT oferta FROM padron_ofertas WHERE est_oferta='Activo' AND cueanexo=%s",
            (cueanexo,)
        )
        ofertas = [r[0] for r in cursor.fetchall()]

        if not ofertas:
            return render(request, 'directores/matriculauegp.html', {
                'resultados_detalle': [],
                'cueanexo': cueanexo,
                'mensaje': 'No hay ofertas activas para este CUEANEXO.'
            })

        for ofert in ofertas:
            data = {'oferta': ofert, 'encabezados': [], 'valores': []}

            # Mapear a la función correspondiente según oferta
            if ofert == 'Adultos - Primaria ':
                query = """SELECT cueanexo, turno, tipo_secc AS tipo, nom_secc as seccion, grado AS Ciclo, total,
                           edad_menos_13 AS "Edad menor 13",
                           SUM(edad_13 + edad_14 + edad_15 + edad_16 + edad_17 + edad_18) AS "Edad 13-18",
                           sum(edad_19+edad_20_a_24+edad_25_a_29) as "Edad 19-29",
                           sum(edad_30_a_34+edad_35+edad_39) as "Edad 30-39",
                           sum(edad_40_a_44+edad_45+edad_49) as "Edad 40-49",
                           sum(edad_50_a_54+edad_55_mas) as "Edad 50 o más"
                    FROM funcion.visor_matric_adulto_primaria('ra_carga2025')
                    WHERE cueanexo::text=%s
                    GROUP BY cueanexo, turno, tipo_secc, nom_secc, grado, total, edad_menos_13
                    ORDER BY cueanexo, grado;"""
            elif ofert == 'Adultos - Secundaria Completa':
                query = """SELECT cueanexo, turno, grado as Año, tipo_div AS tipo, nom_secc as seccion, total,
                           sum(edad_14+edad_15+edad_16+edad_17) AS "Edad 14-17",
                           sum(edad_18+edad_19+edad_20+edad_21+edad_22+edad_23+edad_24+edad_25_a_29) as "Edad 18-29",
                           sum(edad_30_a_34+edad_35+edad_39) as "Edad 30-39",
                           sum(edad_40_a_44+edad_45_a_49) as "Edad 40-49",
                           sum(edad_50_a_54+edad_50_y_mas) as "Edad 50 o más"
                    FROM funcion.visor_matric_adulto_secundaria('ra_carga2025')
                    WHERE cueanexo::text=%s
                    GROUP BY cueanexo, turno, tipo_div, nom_secc, grado, total
                    ORDER BY cueanexo, grado;"""
            elif ofert in ['Común - Jardín de infantes ', 'Común - Jardín maternal ']:
                query = """SELECT cueanexo, turno, grado as sala, tipo_secc AS tipo, nom_secc as seccion, total,
                           menos_1_año as "Menos 1 año", un_año as "1 año", dos_años as "2 años", tres_años as "3 años",
                           cuatro_años as "4 años", cinco_años as "5 años", seis_años as "6 años", total_disc as "Discapacitados"
                    FROM funcion.visor_matric_comun_inicial('ra_carga2025')
                    WHERE cueanexo::text=%s
                    GROUP BY cueanexo, turno, grado, tipo_secc, nom_secc, total, menos_1_año, un_año, dos_años, tres_años, cuatro_años, cinco_años, seis_años, total_disc
                    ORDER BY cueanexo, grado;"""
            elif ofert == 'Común - Primaria de 7 años ':
                query = """SELECT cueanexo, turno, grado, tipo_secc AS tipo, nom_secc as seccion, total,
                           edad_5 as "5 años", edad_6 as "6 años", edad_7 as "7 años", edad_8 as "8 años",
                           edad_9 as "9 años", edad_10 as "10 años", edad_11 as "11 años", edad_12 as "12 años",
                           sum(edad_13+edad_14+edad_15+edad_16+edad_17+edad_18_y_mas) as "13 o más años",
                           tot_discapacidad as "Discapacitados"
                    FROM funcion.visor_matric_comun_primaria('ra_carga2025')
                    WHERE cueanexo::text=%s
                    GROUP BY cueanexo, turno, grado, tipo_secc, nom_secc, total, edad_5, edad_6, edad_7, edad_8, edad_9, edad_10, edad_11, edad_12, tot_discapacidad
                    ORDER BY cueanexo, grado;"""
            else:
                query = """SELECT cueanexo, turno, grado as año, tipo_div AS tipo, nom_secc as seccion, total,
                           edad_12 as "12 años", edad_13 as "13 años", edad_14 as "14 años", edad_15 as "15 años",
                           edad_16 as "16 años", edad_17 as "17 años", edad_18 as "18 años", edad_19 as "19 años",
                           sum(edad_20_24+edad_25_y_mas) as "20 a más",
                           total_disc as "Discapacitados"
                    FROM funcion.visor_matric_comun_secundaria('ra_carga2025')
                    WHERE cueanexo::text=%s
                    GROUP BY cueanexo, turno, grado, tipo_div, nom_secc, total, edad_12, edad_13, edad_14, edad_15, edad_16, edad_17, edad_18, edad_19, total_disc
                    ORDER BY cueanexo, grado;"""

            cursor.execute(query, (cueanexo,))
            data['encabezados'] = [desc[0] for desc in cursor.description]
            data['valores'] = cursor.fetchall()

            if grado:
                data['valores'] = [f for f in data['valores'] if str(f[2]) == str(grado)]

            resultados_detalle.append(data)

    except psycopg2.Error as e:
        connection.close()
        return render(request, 'error.html', {'mensaje': f'Error en la consulta: {e}'})

    connection.close()

    # Debug: imprimir cueanexo recibido
    print("CUEANEXO usado:", cueanexo)

    return render(request, 'directores/matriculauegp.html', {
        'resultados_detalle': resultados_detalle,
        'cueanexo': cueanexo
    })


@login_required
def ajax_filtrar_matricula(request):
    import os, psycopg2
    from django.http import JsonResponse
    from django.template.loader import render_to_string

    cueanexo = request.GET.get('cueanexo') or str(request.user.username)
    grado = request.GET.get('grado', None)
    turno = request.GET.get('turno', None)
    seccion = request.GET.get('seccion', None)
    cueanexo = str(cueanexo)

    resultados_detalle = []

    try:
        connection = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST'),
            user=os.getenv('POSTGRES_USER'),
            password=os.getenv('POSTGRES_PASSWORD'),
            database=os.getenv('POSTGRES_DB')
        )
        cursor = connection.cursor()
    except psycopg2.Error as e:
        return JsonResponse({'html': f'<p>Error al conectar a la DB: {e}</p>'})

    try:
        # Obtener ofertas activas
        cursor.execute(
            "SELECT DISTINCT oferta FROM padron_ofertas WHERE est_oferta='Activo' AND cueanexo::text=%s",
            (cueanexo,)
        )
        ofertas = [r[0] for r in cursor.fetchall()]

        if not ofertas:
            return JsonResponse({'html': '<p>No hay ofertas activas para este CUEANEXO.</p>'})

        for ofert in ofertas:
            data = {'oferta': ofert, 'encabezados': [], 'valores': []}

            # ------------------ QUERY SEGÚN OFERTA ------------------
            if ofert == 'Adultos - Primaria ':
                query = """
                    SELECT cueanexo, turno, tipo_secc AS tipo, nom_secc as seccion, grado AS Ciclo, total,
                           edad_menos_13 AS "Edad menor 13",
                           SUM(edad_13 + edad_14 + edad_15 + edad_16 + edad_17 + edad_18) AS "Edad 13-18",
                           SUM(edad_19 + edad_20_a_24 + edad_25_a_29) AS "Edad 19-29",
                           SUM(edad_30_a_34 + edad_35 + edad_39) AS "Edad 30-39",
                           SUM(edad_40_a_44 + edad_45 + edad_49) AS "Edad 40-49",
                           SUM(edad_50_a_54 + edad_55_mas) AS "Edad 50 o más"
                    FROM funcion.visor_matric_adulto_primaria('ra_carga2025')
                    WHERE cueanexo::text=%s
                    GROUP BY cueanexo, turno, tipo_secc, nom_secc, grado, total, edad_menos_13
                    ORDER BY grado;
                """
                idx_grado = 4
                idx_turno = 1
                idx_seccion = 3

            elif ofert == 'Adultos - Secundaria Completa':
                query = """
                    SELECT cueanexo, turno, grado as Año, tipo_div AS tipo, nom_secc as seccion, total,
                           SUM(edad_14 + edad_15 + edad_16 + edad_17) AS "Edad 14-17",
                           SUM(edad_18 + edad_19 + edad_20 + edad_21 + edad_22 + edad_23 + edad_24 + edad_25_a_29) AS "Edad 18-29",
                           SUM(edad_30_a_34 + edad_35 + edad_39) AS "Edad 30-39",
                           SUM(edad_40_a_44 + edad_45 + edad_49) AS "Edad 40-49",
                           SUM(edad_50_a_54 + edad_50_y_mas) AS "Edad 50 o más"
                    FROM funcion.visor_matric_adulto_secundaria('ra_carga2025')
                    WHERE cueanexo::text=%s
                    GROUP BY cueanexo, turno, tipo_div, nom_secc, grado, total
                    ORDER BY grado;
                """
                idx_grado = 2
                idx_turno = 1
                idx_seccion = 4

            elif ofert in ['Común - Jardín de infantes ', 'Común - Jardín maternal ']:
                query = """
                    SELECT cueanexo, turno, grado as sala, tipo_secc AS tipo, nom_secc as seccion, total,
                           menos_1_año AS "Menos 1 año", un_año AS "1 año", dos_años AS "2 años", tres_años AS "3 años",
                           cuatro_años AS "4 años", cinco_años AS "5 años", seis_años AS "6 años", total_disc AS "Discapacitados"
                    FROM funcion.visor_matric_comun_inicial('ra_carga2025')
                    WHERE cueanexo::text=%s
                    GROUP BY cueanexo, turno, grado, tipo_secc, nom_secc, total, menos_1_año, un_año, dos_años, tres_años, cuatro_años, cinco_años, seis_años, total_disc
                    ORDER BY grado;
                """
                idx_grado = 2
                idx_turno = 1
                idx_seccion = 4

            elif ofert == 'Común - Primaria de 7 años ':
                query = """
                    SELECT cueanexo, turno, grado, tipo_secc AS tipo, nom_secc AS seccion, total,
                           edad_5 AS "5 años", edad_6 AS "6 años", edad_7 AS "7 años", edad_8 AS "8 años",
                           edad_9 AS "9 años", edad_10 AS "10 años", edad_11 AS "11 años", edad_12 AS "12 años",
                           SUM(edad_13 + edad_14 + edad_15 + edad_16 + edad_17 + edad_18_y_mas) AS "13 o más años",
                           tot_discapacidad AS "Discapacitados"
                    FROM funcion.visor_matric_comun_primaria('ra_carga2025')
                    WHERE cueanexo::text=%s
                    GROUP BY cueanexo, turno, grado, tipo_secc, nom_secc, total, edad_5, edad_6, edad_7, edad_8, edad_9, edad_10, edad_11, edad_12, tot_discapacidad
                    ORDER BY grado;
                """
                idx_grado = 2
                idx_turno = 1
                idx_seccion = 4

            else:  # Secundaria Común
                query = """
                    SELECT cueanexo, turno, grado AS año, tipo_div AS tipo, nom_secc AS seccion, total,
                           edad_12 AS "12 años", edad_13 AS "13 años", edad_14 AS "14 años", edad_15 AS "15 años",
                           edad_16 AS "16 años", edad_17 AS "17 años", edad_18 AS "18 años", edad_19 AS "19 años",
                           SUM(edad_20_24 + edad_25_y_mas) AS "20 a más",
                           total_disc AS "Discapacitados"
                    FROM funcion.visor_matric_comun_secundaria('ra_carga2025')
                    WHERE cueanexo::text=%s
                    GROUP BY cueanexo, turno, grado, tipo_div, nom_secc, total, edad_12, edad_13, edad_14, edad_15, edad_16, edad_17, edad_18, edad_19, total_disc
                    ORDER BY grado;
                """
                idx_grado = 2
                idx_turno = 1
                idx_seccion = 4

            # ------------------ EJECUTAR ------------------
            cursor.execute(query, (cueanexo,))
            data['encabezados'] = [desc[0] for desc in cursor.description]
            data['valores'] = cursor.fetchall()

            # Filtrar por selección
            if grado:
                data['valores'] = [f for f in data['valores'] if str(f[idx_grado]).strip() == str(grado).strip()]
            if turno:
                data['valores'] = [f for f in data['valores'] if str(f[idx_turno]).strip() == str(turno).strip()]
            if seccion:
                data['valores'] = [f for f in data['valores'] if str(f[idx_seccion]).strip() == str(seccion).strip()]

            resultados_detalle.append(data)

        # Listas únicas para selectores
        grados_disponibles = sorted({str(f[idx_grado]) for r in resultados_detalle for f in r['valores'] if f[idx_grado]})
        turnos_disponibles = sorted({str(f[idx_turno]) for r in resultados_detalle for f in r['valores'] if f[idx_turno]})
        secciones_disponibles = sorted({str(f[idx_seccion]) for r in resultados_detalle for f in r['valores'] if f[idx_seccion]})

    except psycopg2.Error as e:
        connection.close()
        return JsonResponse({'html': f'<p>Error en la consulta: {e}</p>'})

    connection.close()

    html = render_to_string('directores/matricula_cards.html', {
        'resultados_detalle': resultados_detalle,
        'cueanexo': cueanexo
    })

    return JsonResponse({
        'html': html,
        'grados': list(grados_disponibles),
        'turnos': list(turnos_disponibles),
        'secciones': list(secciones_disponibles)
    })