import psycopg2
import plotly.graph_objs as go
import plotly.io as pio
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# Función para conectar a la base de datos
def conectar_bd():
    try:
        connection = psycopg2.connect(
            host='relevamientoanual.com.ar',
            user='visualizador',
            password='Estadisticas24',
            database='visualizador',
        )
        return connection
    except psycopg2.Error as e:
        # Manejar el error de conexión
        print(f"Error al conectar a la base de datos: {e}")
        return None

@login_required
def filter_data_evolucion_matricula(request):
    cueanexo = request.user.username
    connection = conectar_bd()

    if not connection:
        return render(request, 'error_conexion.html')

    try:
        cursor = connection.cursor()
        query = """
            SELECT cueanexo, nom_est, matricula_2017, matricula_2018, matricula_2019, matricula_2020, matricula_2021, matricula_2022, matricula_2023 
            FROM indicadores.cube_matric_evolucion_primaria
            WHERE cueanexo = %s 
            AND COALESCE(region, sector, ambito, localidad, departamento) IS NULL;
        """
        cursor.execute(query, (cueanexo,))
        data = cursor.fetchone()

        if not data:
            return render(request, 'consulta_vacia.html')

        labels = ['2017', '2018', '2019', '2020', '2021', '2022', '2023']
        matricula = data[2:]

        colors = ['blue', 'green', 'orange', 'red', 'purple', 'brown', 'gray']
        fig = go.Figure()
        for i, año in enumerate(labels):
            fig.add_trace(go.Bar(x=[año], y=[matricula[i]], marker_color=colors[i], name=f'{año}: {matricula[i]}'))

        titulo = f'<b>Evolución de la Matrícula</b> - Cueanexo: {cueanexo}'
        fig.update_layout(title=titulo, title_x=0.5, xaxis_title='Año', yaxis_title='Matrícula')

        graph_html = fig.to_html(full_html=False)
        context = {
            'grafico': graph_html,
            'cueanexo': cueanexo,
            'nom_est': data[1],
        }

        return render(request, 'indicadores/evolucion_matricula.html', context)
    finally:
        cursor.close()
        connection.close()

@login_required
def filter_data_retencion(request):
    cueanexo = request.user.username
    connection = conectar_bd()

    if not connection:
        return render(request, 'error_conexion.html')

    try:
        cursor = connection.cursor()
        query_2022 = """
            SELECT cueanexo, nom_est, 
                ROUND(tasa_retencion_primero, 2) AS tasa_retencion_primero, 
                ROUND(tasa_retencion_segundo, 2) AS tasa_retencion_segundo, 
                ROUND(tasa_retencion_tercero, 2) AS tasa_retencion_tercero, 
                ROUND(tasa_retencion_cuarto, 2) AS tasa_retencion_cuarto, 
                ROUND(tasa_retencion_quinto, 2) AS tasa_retencion_quinto, 
                ROUND(tasa_retencion_sexto, 2) AS tasa_retencion_sexto, 
                ROUND(tasa_retencion_septimo, 2) AS tasa_retencion_septimo
            FROM indicadores.cube_retencion_primaria_ra2022
            WHERE cueanexo=%s
            AND COALESCE(sector, ambito, departamento, region) IS NULL;
        """

        query_2023 = """
            SELECT cueanexo, nom_est, 
                ROUND(tasa_retencion_primero, 2) AS tasa_retencion_primero, 
                ROUND(tasa_retencion_segundo, 2) AS tasa_retencion_segundo, 
                ROUND(tasa_retencion_tercero, 2) AS tasa_retencion_tercero, 
                ROUND(tasa_retencion_cuarto, 2) AS tasa_retencion_cuarto, 
                ROUND(tasa_retencion_quinto, 2) AS tasa_retencion_quinto, 
                ROUND(tasa_retencion_sexto, 2) AS tasa_retencion_sexto, 
                ROUND(tasa_retencion_septimo, 2) AS tasa_retencion_septimo
            FROM indicadores.cube_retencion_primaria_ra2023
            WHERE cueanexo=%s
            AND COALESCE(sector, ambito, departamento, region) IS NULL;
        """

        cursor.execute(query_2022, (cueanexo,))
        data_2022 = cursor.fetchone()

        cursor.execute(query_2023, (cueanexo,))
        data_2023 = cursor.fetchone()

        if not data_2022 or not data_2023:
            return render(request, 'consulta_vacia.html')

        labels = ['1ero', '2do', '3ero', '4to', '5to', '6to', '7mo']
        tasas_2022 = data_2022[2:]
        tasas_2023 = data_2023[2:]

        titulo = f'<b>Tasas de Retención por Año y Grado</b> - Cueanexo: {cueanexo}'
        fig = go.Figure()
        fig.add_trace(go.Bar(x=labels, y=tasas_2022, name='2022', marker_color='red'))
        fig.add_trace(go.Bar(x=labels, y=tasas_2023, name='2023', marker_color='green'))
        fig.update_layout(title=titulo, title_x=0.5, xaxis_title='Año', yaxis_title='Tasa de Retención', width=800, height=600)

        graph_html = pio.to_html(fig, full_html=False)
        context = {
            'grafico': graph_html,
            'cueanexo': cueanexo,
            'nom_est': data_2022[1],
        }

        return render(request, 'indicadores/retencion.html', context)
    finally:
        cursor.close()
        connection.close()


@login_required
def filter_data_efec_aban_rep(request):
    cueanexo = request.user.username
    connection = conectar_bd()

    if not connection:
        return render(request, 'error_conexion.html')

    try:
        cursor = connection.cursor()
        query_efec="""
            SELECT 
                cueanexo,
                ROUND("1er_tasa_efectiva", 2) AS "1er_tasa_efectiva", 
                ROUND("2do_tasa_efectiva", 2) AS "2do_tasa_efectiva",
                ROUND("3er_tasa_efectiva", 2) AS "3er_tasa_efectiva",
                ROUND("4to_tasa_efectiva", 2) AS "4to_tasa_efectiva",
                ROUND("5to_tasa_efectiva", 2) AS "5to_tasa_efectiva",
                ROUND("6to_tasa_efectiva", 2) AS "6to_tasa_efectiva",
                ROUND("7mo_tasa_efectiva", 2) AS "7mo_tasa_efectiva"
            FROM 
                indicadores.t_efec_primaria_ra2023
            WHERE 
                cueanexo=%s;
        """
        
        query_aban="""
            SELECT 
                cueanexo,
                ROUND("1er_tasa_abandono", 2) AS "1er_tasa_abandono", 
                ROUND("2do_tasa_abandono", 2) AS "2do_tasa_abandono",
                ROUND("3er_tasa_abandono", 2) AS "3er_tasa_abandono",
                ROUND("4to_tasa_abandono", 2) AS "4to_tasa_abandono",
                ROUND("5to_tasa_abandono", 2) AS "5to_tasa_abandono",
                ROUND("6to_tasa_abandono", 2) AS "6to_tasa_abandono",
                ROUND("7mo_tasa_abandono", 2) AS "7mo_tasa_abandono"
            FROM 
                indicadores.t_aban_primaria_ra2023
            WHERE 
                cueanexo=%s;
        """
        
        query_rep="""
            SELECT 
                cueanexo,
                ROUND("1er_tasa_repitente", 2) AS "1er_tasa_repitente", 
                ROUND("2do_tasa_repitente", 2) AS "2do_tasa_repitente",
                ROUND("3er_tasa_repitente", 2) AS "3er_tasa_repitente",
                ROUND("4to_tasa_repitente", 2) AS "4to_tasa_repitente",
                ROUND("5to_tasa_repitente", 2) AS "5to_tasa_repitente",
                ROUND("6to_tasa_repitente", 2) AS "6to_tasa_repitente",
                ROUND("7mo_tasa_repitente", 2) AS "7mo_tasa_repitente"
            FROM 
                indicadores.t_rep_primaria_ra2023
            WHERE 
                cueanexo=%s;
        """
        
        cursor.execute(query_efec, (cueanexo,))
        data_efec = cursor.fetchone()

        cursor.execute(query_aban, (cueanexo,))
        data_aban = cursor.fetchone()
        
        cursor.execute(query_rep, (cueanexo,))
        data_rep = cursor.fetchone()

        if not data_efec or not data_aban or not data_rep:
            return render(request, 'consulta_vacia.html')

        labels = ['1ero', '2do', '3ero', '4to', '5to', '6to', '7mo']
        tasa_efectiva = data_efec[1:]
        tasa_abandono = data_aban[1:]
        tasa_repitencia = data_aban[1:]
                
        titulo = f'<b>Tasa Efectiva, Abanono y Repitencia por Año y Grado</b> - Cueanexo: {cueanexo}'
        fig = go.Figure()
        fig.add_trace(go.Bar(x=labels, y=tasa_efectiva, name='Efectiva', marker_color='red'))
        fig.add_trace(go.Bar(x=labels, y=tasa_abandono, name='Abandono', marker_color='green'))
        fig.add_trace(go.Bar(x=labels, y=tasa_repitencia, name='Repitencia', marker_color='blue'))
        fig.update_layout(title=titulo, title_x=0.5, xaxis_title='Año 2023', yaxis_title='Tasa', width=800, height=600)

        graph_html = pio.to_html(fig, full_html=False)
        context = {
            'grafico': graph_html,
            'cueanexo': cueanexo,
            'nom_est': data_efec[1],
        }

        return render(request, 'indicadores/efecabanrep.html', context)
    finally:
        cursor.close()
        connection.close()


@login_required
def filter_data_sobreedad(request):
    cueanexo = request.user.username
    connection = conectar_bd()

    if not connection:
        return render(request, 'error_conexion.html')

    try:
        cursor = connection.cursor()
        query_sobre="""
            select cueanexo, escuela, grado, total, edad, sobre_edad from indicadores.sobreedadprimaria2023
                where cueanexo=%s;
        """      
                
        cursor.execute(query_sobre, (cueanexo,))
        data_sobre = cursor.fetchall()        

        if not data_sobre:
            return render(request, 'consulta_vacia.html')

        return render(request, 'indicadores/sobreedad.html',{'data_sobre': data_sobre} )
    finally:
        cursor.close()
        connection.close()