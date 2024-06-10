import psycopg2
import matplotlib.pyplot as plt
import io
import base64
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

    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Definir una paleta de colores para cada año
    colors = ['blue', 'green', 'orange', 'red', 'purple', 'brown', 'gray']
    
    ax.bar(labels, matricula, color=colors)
    ax.set_title('Evolución de la Matrícula')
    ax.set_xlabel('Año')
    ax.set_ylabel('Matrícula')

    # Guardar la figura en un buffer de bytes
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    image_png = buffer.getvalue()
    buffer.close()

    # Codificar la imagen en base64
    image_base64 = base64.b64encode(image_png).decode('utf-8')

    context = {
        'grafico': image_base64,
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

    fig, ax = plt.subplots(figsize=(16, 10))

    ax.bar([x - 0.2 for x in range(1, 8)], tasas1, width=0.4, label='2022')
    ax.bar([x + 0.2 for x in range(1, 8)], tasas2, width=0.4, label='2023')
    ax.set_title('Tasas de Retención por Año', fontsize=24)
    ax.set_xlabel('Año',fontsize=20)
    ax.set_ylabel('Tasa de Retención',fontsize=20)
    ax.set_xticks(range(1, 8))
    ax.set_xticklabels(labels, fontsize=20)
    ax.legend(fontsize=20)

    # Guardar la figura en un buffer de bytes
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    image_png = buffer.getvalue()
    buffer.close()

    # Codificar la imagen en base64
    image_base64 = base64.b64encode(image_png).decode('utf-8')

    context = {
        'grafico': image_base64,
        'cueanexo': cueanexo,
        'nom_est': data1[0][1],
    }

    return render(request, 'indicadores/retencion.html', context)
