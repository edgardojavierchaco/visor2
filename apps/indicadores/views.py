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
        return None

@login_required
def filter_data_evolucion_matricula(request):
    # Obtener el username del usuario logueado
    cueanexo = request.user.username

    # Conectarse a la base de datos
    connection = conectar_bd()
    if not connection:
        return render(request, 'error_conexion.html')

    cursor = connection.cursor()

    query = """
        SELECT cueanexo, nom_est, matricula_2017, matricula_2018, matricula_2019, matricula_2020, matricula_2021, matricula_2022, matricula_2023 
        FROM indicadores.cube_matric_evolucion_primaria
        WHERE cueanexo = %s 
        AND COALESCE(region, sector, ambito, localidad, departamento) IS NULL;
    """

    cursor.execute(query, (cueanexo,))
    data = cursor.fetchall()

    if not data:
        return render(request, 'consulta_vacia.html')

    # Procesar los datos para el gráfico de barras
    labels = ['2017', '2018', '2019', '2020', '2021', '2022', '2023']
    matricula = data[0][2:]

    fig = go.Figure()
    fig.add_trace(go.Bar(x=labels, y=matricula, marker_color='blue'))
    fig.update_layout(title='Evolución de la Matrícula', xaxis_title='Año', yaxis_title='Matrícula')

    # Convertir la figura a un HTML string
    graph_html = pio.to_html(fig, full_html=False)

    context = {
        'grafico': graph_html,
        'cueanexo': cueanexo,
        'nom_est': data[0][1],
    }

    return render(request, 'indicadores/evolucion_matricula.html', context)

@login_required
def filter_data_retencion(request):
    # Obtener el username del usuario logueado
    cueanexo = request.user.username

    # Conectarse a la base de datos
    connection = conectar_bd()
    if not connection:
        return render(request, 'error_conexion.html')

    cursor = connection.cursor()

    query = """
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

    query2 = """
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
    
    cursor.execute(query, (cueanexo,))
    data1 = cursor.fetchall()

    cursor.execute(query2, (cueanexo,))
    data2 = cursor.fetchall()

    if not data1 or not data2:
        return render(request, 'consulta_vacia.html')

    # Procesar los datos para el gráfico de barras
    labels = ['1ero', '2do', '3ero', '4to', '5to', '6to', '7mo']
    tasas1 = data1[0][2:]
    tasas2 = data2[0][2:]

    fig = go.Figure()
    fig.add_trace(go.Bar(x=[x - 0.2 for x in range(1, 8)], y=tasas1, name='2022', marker_color='blue'))
    fig.add_trace(go.Bar(x=[x + 0.2 for x in range(1, 8)], y=tasas2, name='2023', marker_color='orange'))
    fig.update_layout(title='Tasas de Retención por Año', xaxis_title='Año', yaxis_title='Tasa de Retención')

    # Convertir la figura a un HTML string
    graph_html = pio.to_html(fig, full_html=False)

    context = {
        'grafico': graph_html,
        'cueanexo': cueanexo,
        'nom_est': data1[0][1],
    }

    return render(request, 'indicadores/retencion.html', context)
