import psycopg2
import os
import dotenv
import plotly.graph_objs as go
from django.db import connection
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
import pandas as pd
from django.http import HttpResponse, JsonResponse


def calcular_estadisticas_por_cueanexo(username):
    """
    Calcula estadísticas sobre los alumnos por cueanexo.

    Args:
        username (str): El nombre de usuario para filtrar los datos.

    Returns:
        tuple: Una tupla que contiene:
            - resultados_total_dni: Lista de estadísticas por cueanexo y desempeño.
            - total_dni_sin_desempenio: Total de DNI sin discriminar por desempeño.
            - resultado_promedio_velocidad: Promedio de velocidad.
            - resultado_promedio_precision: Promedio de precisión.
            - resultado_promedio_prosodia: Promedio de prosodia.
            - resultado_promedio_comprension: Promedio de comprensión.
            - total_dni_presentes: Total de DNI de alumnos presentes.
    """
    
    with connection.cursor() as cursor:
        # Calcular total de DNI por cueanexo y desempeño
        cursor.execute("""
            SELECT cueanexo,
                    cal_vel, 
                    cal_pres, 
                    cal_pros, 
                    cal_comp,
                    COUNT(dni_alumno) as total_dni
            FROM cenpe."Evaluacion_Lectora"
            WHERE cueanexo = %s and asistencia = 'true'
            GROUP BY cueanexo, cal_vel, cal_pres, cal_pros, cal_comp
        """, [username])
        resultados_total_dni = cursor.fetchall()

        # Calcular total de DNI sin discriminación de desempeño
        cursor.execute("""
            SELECT COUNT(dni_alumno) as total_dni
            FROM cenpe."Evaluacion_Lectora"
            WHERE cueanexo = %s
        """, [username])
        total_dni_sin_desempenio = cursor.fetchone()[0]
        
        # Calcular total de alumnos presentes
        cursor.execute("""
            SELECT 
                    COUNT(dni_alumno) as total_dni
            FROM cenpe."Evaluacion_Lectora"
            WHERE cueanexo = %s and asistencia = 'true'            
        """, [username])
        total_dni_presentes = cursor.fetchone()[0]

        # Calcular promedio de velocidad por cueanexo
        cursor.execute("""
            SELECT AVG(velocidad) as promedio_velocidad
            FROM cenpe."Evaluacion_Lectora"
            WHERE cueanexo = %s and asistencia='true'
        """, [username])
        resultado_promedio_velocidad = cursor.fetchone()
        
        # Calcular promedio de precisión por cueanexo
        cursor.execute("""
            SELECT AVG(precision) as promedio_precision
            FROM cenpe."Evaluacion_Lectora"
            WHERE cueanexo = %s and asistencia='true'
        """, [username])
        resultado_promedio_precision = cursor.fetchone()
        
        # Calcular promedio de prosodia por cueanexo
        cursor.execute("""
            SELECT AVG(prosodia) as promedio_prosodia
            FROM cenpe."Evaluacion_Lectora"
            WHERE cueanexo = %s and asistencia='true'
        """, [username])
        resultado_promedio_prosodia = cursor.fetchone()
        
        # Calcular promedio de comprension por cueanexo
        cursor.execute("""
            SELECT AVG(comprension) as promedio_comprension
            FROM cenpe."Evaluacion_Lectora"
            WHERE cueanexo = %s and asistencia='true'
        """, [username])
        resultado_promedio_comprension = cursor.fetchone()

    return resultados_total_dni, total_dni_sin_desempenio, resultado_promedio_velocidad, resultado_promedio_precision, resultado_promedio_prosodia, resultado_promedio_comprension, total_dni_presentes


@login_required
def tu_vistaloc(request):
    """
    Vista que muestra las estadísticas de evaluación lectora.

    Args:
        request (HttpRequest): La solicitud HTTP.

    Returns:
        HttpResponse: Renderiza la plantilla con gráficos y estadísticas.
    """
    
    
    username = request.user.username
    resultados_total_dni, total_dni_sin_desempenio, resultado_promedio_velocidad, resultado_promedio_precision, resultado_promedio_prosodia, resultado_promedio_comprension, total_dni_presentes = calcular_estadisticas_por_cueanexo(username)
    print(total_dni_presentes)
    # Definir el orden y colores para los labels
    orden_labels = ["Debajo del Básico", "Básico", "Satisfactorio", "Avanzado"]
    colores = ['#d62728','#ffcc00', '#90ee90','#2ca02c']
    
    # Crear un gráfico para cada una de las categorías: velocidad, precisión, prosodia, comprensión
    graficos = {}
    atributos = ['cal_vel', 'cal_pres', 'cal_pros', 'cal_comp']
    nombres_atributos = ['Velocidad lectora', 'Precisión lectora', 'Prosodia', 'Comprensión lectora']
    
    for i, atributo in enumerate(atributos):
        conteo_dict = {label: 0 for label in orden_labels}
        for resultado in resultados_total_dni:
            conteo_dict[resultado[i+1]] += resultado[5]
        
        labels = list(conteo_dict.keys())
        valores = list(conteo_dict.values())
        total_dni = sum(valores)
        etiquetas = [f"{label}: {conteo} ({(conteo / total_dni_presentes * 100):.2f}%)" for label, conteo in zip(labels, valores)]
        
        grafico = go.Figure(data=[go.Pie(labels=etiquetas, values=valores, marker=dict(colors=colores))])
        grafico.update_layout(
            title={
                'text': f'Gráfico de {nombres_atributos[i]}',
                'y': 0.9,  # Ajusta la posición vertical del título (0.5 es el centro)
                'x': 0.5,  # Ajusta la posición horizontal del título (0.5 es el centro)
                'xanchor': 'center',  # Ancla el texto en el centro horizontal
                'yanchor': 'bottom'  # Ancla el texto en la parte superior vertical
            },
            title_font=dict(
                size=20,  # Tamaño de la fuente
                color='black',  # Color del texto
                family='Arial',  # Tipo de letra
                weight='bold',  # Texto en negrita
            ),
            width=750  # Ancho del gráfico
        )

        
        graficos[nombres_atributos[i].lower()] = grafico.to_html(full_html=False)

    # Verificar si hay un resultado para los promedios
    promedio_velocidad = float(f"{resultado_promedio_velocidad[0]:.2f}") if resultado_promedio_velocidad[0] is not None else 0.00
    promedio_precision = float(f"{resultado_promedio_precision[0]:.2f}") if resultado_promedio_precision[0] is not None else 0.00
    promedio_prosodia = float(f"{resultado_promedio_prosodia[0]:.2f}") if resultado_promedio_prosodia[0] is not None else 0.00
    promedio_comprension = float(f"{resultado_promedio_comprension[0]:.2f}") if resultado_promedio_comprension[0] is not None else 0.00

    # Renderizar la plantilla con los gráficos y los promedios
    return render(request, 'oplectura/grafico.html', {
        'total_dni_sin_desempenio': total_dni_sin_desempenio,
        'total_dni_presentes': total_dni_presentes,
        'promedio_velocidad': promedio_velocidad,
        'promedio_precision': promedio_precision,
        'promedio_prosodia': promedio_prosodia,
        'promedio_comprension': promedio_comprension,
        'grafico_velocidad': graficos['velocidad lectora'],
        'grafico_precision': graficos['precisión lectora'],
        'grafico_prosodia': graficos['prosodia'],
        'grafico_comprension': graficos['comprensión lectora'],
    })

@login_required
def mostrar_grafico_loc(request):
    """
    Muestra el gráfico de evaluación según las regiones, ámbitos y sectores seleccionados.

    Args:
        request (HttpRequest): La solicitud HTTP.

    Returns:
        HttpResponse: Renderiza la plantilla con los gráficos filtrados.
    """
    
    # Obtener los valores seleccionados del checkbox
    localidad_seleccionadas = request.GET.get('localidad')
    ambitos_seleccionados = request.GET.get('ambito')
    sectores_seleccionados = request.GET.get('sector')
    print("localidad seleccionada:", localidad_seleccionadas)
    
    mostrar_todo = localidad_seleccionadas == '0'  # Verifica si se selecciona "Mostrar Todo"
    
    # Establecer conexión con la base de datos PostgreSQL
    with psycopg2.connect(
        host=os.getenv('POSTGRES_HOST'),
        user=os.getenv('POSTGRES_USER'),
        password=os.getenv('POSTGRES_PASSWORD'),
        database=os.getenv('POSTGRES_DB')
    ) as conn:
        with conn.cursor() as cursor:
            if mostrar_todo:                
                # Si se selecciona "Mostrar Todo", mostrar todos los datos
                query = '''
                    SELECT velocidad, precision, prosodia, comprension, cal_vel, cal_pres, cal_pros, cal_comp, region, asistencia, ambito, sector
                    FROM cenpe.vistaevaluacion_unica_por_dni_y_tramo
                '''
                cursor.execute(query)
                datos_usuario = cursor.fetchall()              
                print('general:', datos_usuario)
            else:
                # Filtrar los datos para las regiones seleccionadas
                query = '''
                    SELECT velocidad, precision, prosodia, comprension, cal_vel, cal_pres, cal_pros, cal_comp, region, asistencia, ambito, sector 
                    FROM cenpe.vistaevaluacion_unica_por_dni_y_tramo WHERE 1=1
                '''
                parameters = []
                
                if localidad_seleccionadas:
                    query += " AND localidad = %s"
                    parameters.append(localidad_seleccionadas)
                if ambitos_seleccionados:
                    query += " AND ambito = %s"
                    parameters.append(ambitos_seleccionados)
                if sectores_seleccionados:
                    query += " AND sector = %s"
                    parameters.append(sectores_seleccionados)
                    
                cursor.execute(query, parameters)
                datos_usuario = cursor.fetchall()
                print('datos:', datos_usuario)
    
    if not datos_usuario:
        return render(request, 'oplectura/graficoxloc.html', {
            'datos_disponibles': False
        })
    
    # Convertir los datos a DataFrames de pandas con las columnas correctas
    columns = ['velocidad', 'precision', 'prosodia', 'comprension', 'cal_vel', 'cal_pres', 'cal_pros', 'cal_comp', 'localidad', 'asistencia', 'ambito', 'sector']
    df = pd.DataFrame(datos_usuario, columns=columns)
    
    # Filtrar los DataFrames para incluir solo a los alumnos presentes (asistencia = True)
    df_presentes = df[df['asistencia'] == 't']
    df_total = df
    
    # Separar DataFrames para cada aspecto con solo los presentes
    df_vel = df_presentes[['velocidad', 'cal_vel', 'localidad']]
    df_pres = df_presentes[['precision', 'cal_pres', 'localidad']]
    df_pros = df_presentes[['prosodia', 'cal_pros', 'localidad']]
    df_comp = df_presentes[['comprension', 'cal_comp', 'localidad']]
    
    # Calcular el total de alumnos presentes (que ya están filtrados)
    total_dni_presentes = df_presentes.shape[0]
    total_alumnos = df_total.shape[0]
    
    # Verificar las columnas antes de operar
    if 'velocidad' not in df_vel.columns or 'cal_vel' not in df_vel.columns:
        return HttpResponse("Error en los datos: columnas 'velocidad' o 'cal_vel' no encontradas.")
    
    if 'precision' not in df_pres.columns or 'cal_pres' not in df_pres.columns:
        return HttpResponse("Error en los datos: columnas 'precisión' o 'cal_pres' no encontradas.")
    
    if 'prosodia' not in df_pros.columns or 'cal_pros' not in df_pros.columns:
        return HttpResponse("Error en los datos: columnas 'prosodia' o 'cal_pros' no encontradas.")
    
    if 'comprension' not in df_comp.columns or 'cal_comp' not in df_comp.columns:
        return HttpResponse("Error en los datos: columnas 'comprensión' o 'cal_comp' no encontradas.")
    
    # Definir el orden y colores para los labels
    orden_labels = ["Debajo del Básico", "Básico", "Satisfactorio", "Avanzado"]
    colores = ['#d62728','#ffcc00', '#90ee90','#2ca02c']
    
    # Ajustar los conteos según el orden definido, considerando solo los presentes
    conteo_vel = df_vel['cal_vel'].value_counts().reindex(orden_labels, fill_value=0)
    conteo_pres = df_pres['cal_pres'].value_counts().reindex(orden_labels, fill_value=0)
    conteo_pros = df_pros['cal_pros'].value_counts().reindex(orden_labels, fill_value=0)
    conteo_comp = df_comp['cal_comp'].value_counts().reindex(orden_labels, fill_value=0)
    
    # Calcular los porcentajes sobre el total de alumnos presentes
    porcentajes_vel = (conteo_vel / total_dni_presentes) * 100
    porcentajes_pres = (conteo_pres / total_dni_presentes) * 100
    porcentajes_pros = (conteo_pros / total_dni_presentes) * 100
    porcentajes_comp = (conteo_comp / total_dni_presentes) * 100
    
    # Crear etiquetas con cantidad y porcentaje
    etiquetas_vel = [f"{label}: {conteo} ({porcentaje:.2f}%)" for label, conteo, porcentaje in zip(orden_labels, conteo_vel, porcentajes_vel)]
    etiquetas_pres = [f"{label}: {conteo} ({porcentaje:.2f}%)" for label, conteo, porcentaje in zip(orden_labels, conteo_pres, porcentajes_pres)]
    etiquetas_pros = [f"{label}: {conteo} ({porcentaje:.2f}%)" for label, conteo, porcentaje in zip(orden_labels, conteo_pros, porcentajes_pros)]
    etiquetas_comp = [f"{label}: {conteo} ({porcentaje:.2f}%)" for label, conteo, porcentaje in zip(orden_labels, conteo_comp, porcentajes_comp)]
    
    # Calcular el promedio de puntaje
    promedio_puntaje_vel = int(round(df_vel['velocidad'].mean()))
    promedio_puntaje_pres = int(round(df_pres['precision'].mean()))
    promedio_puntaje_pros = int(round(df_pros['prosodia'].mean()))
    promedio_puntaje_comp = int(round(df_comp['comprension'].mean()))
    
    # Obtener el nombre de la región o mostrar "Chaco"
    localidad = 'Chaco' if mostrar_todo else ', '.join(df_vel['localidad'].unique())
    
    # Crear los gráficos de torta con Plotly de Velocidad
    fig = go.Figure(data=[go.Pie(labels=etiquetas_vel, values=conteo_vel, marker=dict(colors=colores))])
    fig.update_layout(showlegend=True)
    
    # Crear los gráficos de torta con Plotly de Precisión
    fig2 = go.Figure(data=[go.Pie(labels=etiquetas_pres, values=conteo_pres, marker=dict(colors=colores))])
    fig2.update_layout(showlegend=True)
    
    # Crear los gráficos de torta con Plotly de Prosodia
    fig3 = go.Figure(data=[go.Pie(labels=etiquetas_pros, values=conteo_pros, marker=dict(colors=colores))])
    fig3.update_layout(showlegend=True)
    
    # Crear los gráficos de torta con Plotly de Comprensión
    fig4 = go.Figure(data=[go.Pie(labels=etiquetas_comp, values=conteo_comp, marker=dict(colors=colores))])
    fig4.update_layout(showlegend=True)
    
    # Convertir las figuras a HTML
    graph_html = fig.to_html(full_html=False, default_height=500, default_width=700)
    graph_html2 = fig2.to_html(full_html=False, default_height=500, default_width=700)
    graph_html3 = fig3.to_html(full_html=False, default_height=500, default_width=700)
    graph_html4 = fig4.to_html(full_html=False, default_height=500, default_width=700)
    
    # Renderizar la plantilla y pasar los gráficos, promedios y total de presentes
    return render(request, 'oplectura/graficoxloc.html', {
        'grafico': graph_html,
        'grafico2': graph_html2,
        'grafico3': graph_html3,
        'grafico4': graph_html4, 
        'promedio_puntaje_velocidad': promedio_puntaje_vel,
        'promedio_puntaje_precision': promedio_puntaje_pres,
        'promedio_puntaje_prosodia': promedio_puntaje_pros,
        'promedio_puntaje_comprension': promedio_puntaje_comp,
        'total_alumnos': total_alumnos,
        'total_dni_presentes': total_dni_presentes,  # Incluye el total de presentes
        'localidad': localidad_seleccionadas,
        'datos_disponibles': True
    })


@login_required
def cargar_grafico_loc(request):    
    return render(request, 'oplectura/graficoxloc.html', {
        'datos_disponibles': False
    })


def mostrar_grafico_localidad(request):
    """
    Obtiene y muestra un listado de localidades con datos disponibles para la evaluación.
    Renderiza una vista que permite seleccionar localidades para filtrar datos de evaluación.

    Args:
        request (HttpRequest): La solicitud HTTP recibida.

    Returns:
        HttpResponse: Respuesta renderizada con la plantilla 'lectocomp/graficolocalidades.html', 
                      que incluye la lista de localidades.
    """
    localidades=[]       
    
    # Obtine las localidades únicas
    with connection.cursor() as cursor:
        cursor.execute("SELECT DISTINCT localidad FROM cenpe.vistaevaluacion_unica_por_dni_y_tramo WHERE localidad !='None'")
        localidades = [row[0] for row in cursor.fetchall()]
        print('Localidades cargadas:', localidades)
    
     # Si es una solicitud estándar, renderiza la plantilla
    context = {
        'localidades': localidades,        
    }
    print('Contexto:', context)
    return render(request, 'oplectura/graficoxloc.html', context)
