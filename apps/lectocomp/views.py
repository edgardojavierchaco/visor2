import psycopg2
import plotly.graph_objs as go
from django.db import connection
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
import pandas as pd
from django.http import HttpResponse

def calcular_estadisticas_por_cueanexo(username):
    with connection.cursor() as cursor:
        # Calcular total de DNI por cueanexo y desempeño
        cursor.execute("""
            SELECT cueanexo,
                   desempenio,
                   COUNT(dni) as total_dni
            FROM public.teslecturamayo
            WHERE cueanexo = %s
            GROUP BY cueanexo, desempenio
        """, [username])
        resultados_total_dni = cursor.fetchall()

        # Calcular total de DNI sin discriminación de desempeño
        cursor.execute("""
            SELECT COUNT(dni) as total_dni
            FROM public.teslecturamayo
            WHERE cueanexo = %s
        """, [username])
        total_dni_sin_desempenio = cursor.fetchone()[0]

        # Calcular promedio de puntaje por cueanexo
        cursor.execute("""
            SELECT AVG(puntaje) as promedio_puntaje
            FROM public.teslecturamayo
            WHERE cueanexo = %s
        """, [username])
        resultado_promedio_puntaje = cursor.fetchone()

    return resultados_total_dni, total_dni_sin_desempenio, resultado_promedio_puntaje

@login_required
def tu_vista(request):
    username = request.user.username
    resultados_total_dni, total_dni_sin_desempenio, resultado_promedio_puntaje = calcular_estadisticas_por_cueanexo(username)
    
    # Definir el orden y colores para los labels
    orden_labels = ["Debajo del Nivel Básico", "Básico", "Satisfactorio", "Avanzado", "Calificación Incorrecta", "Sin Calificar"]
    colores = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
    
    # Inicializar diccionario para contar los valores en orden
    conteo_dict = {label: 0 for label in orden_labels}
    
    for resultado in resultados_total_dni:
        conteo_dict[resultado[1]] = resultado[2]
    
    # Crear listas ordenadas
    labels = list(conteo_dict.keys())
    valores = list(conteo_dict.values())
    total_dni = sum(valores)
    etiquetas = [f"{label}: {conteo} ({(conteo / total_dni * 100):.2f}%)" for label, conteo in zip(labels, valores)]
    
    # Crear el gráfico de torta
    grafico_torta_total_dni = go.Figure(data=[go.Pie(labels=etiquetas, values=valores, marker=dict(colors=colores))])
    grafico_torta_total_dni.update_layout(width=750)  # Fijar el ancho del gráfico

    # Verificar si hay un resultado para el promedio de puntaje
    if resultado_promedio_puntaje and resultado_promedio_puntaje[0] is not None:
        promedio_puntaje = float(f"{resultado_promedio_puntaje[0]:.2f}")
    else:
        promedio_puntaje = 0.00

    # Renderizar la plantilla con los resultados y el gráfico
    return render(request, 'lectocomp/grafico.html', {
        'total_dni_sin_desempenio': total_dni_sin_desempenio,
        'promedio_puntaje': promedio_puntaje,
        'grafico_torta_total_dni': grafico_torta_total_dni.to_html(full_html=False),
    })

def mostrar_grafico_reg(request):
    # Obtener los valores seleccionados del checkbox
    regiones_seleccionadas = request.GET.getlist('region')
    
    mostrar_todo = '0' in regiones_seleccionadas  # Verifica si se selecciona "Mostrar Todo"
    
    # Establecer conexión con la base de datos PostgreSQL
    with psycopg2.connect(
        dbname="visualizador",
        user="visualizador",
        password="Estadisticas24",
        host="visoreducativochaco.com.ar"
    ) as conn:
        with conn.cursor() as cursor:
            if mostrar_todo:
                # Si se selecciona "Mostrar Todo", mostrar todos los datos
                query = "SELECT desempenio, puntaje, reg FROM public.teslecturamayo"
                cursor.execute(query)
                datos_usuario = cursor.fetchall()
                
                query1 = "SELECT desempenio3, puntaje, reg FROM public.teslecturamayoeval"
                cursor.execute(query1)
                datos_usuario1 = cursor.fetchall()
            else:
                # Filtrar los datos para las regiones seleccionadas
                if regiones_seleccionadas:
                    placeholders = ','.join(['%s'] * len(regiones_seleccionadas))
                    query = f"SELECT desempenio, puntaje, reg FROM public.teslecturamayo WHERE reg IN ({placeholders})"
                    cursor.execute(query, tuple(regiones_seleccionadas))
                    datos_usuario = cursor.fetchall()
                    
                    query1 = f"SELECT desempenio3, puntaje, reg FROM public.teslecturamayoeval WHERE reg IN ({placeholders})"
                    cursor.execute(query1, tuple(regiones_seleccionadas))
                    datos_usuario1 = cursor.fetchall()
                else:
                    return render(request, 'lectocomp/graficoreg.html', {
                        'datos_disponibles': False
                    })
    
    if not datos_usuario or not datos_usuario1:
        return render(request, 'lectocomp/graficoreg.html', {
            'datos_disponibles': False
        })
    
    # Convertir los datos a DataFrames de pandas
    df = pd.DataFrame(datos_usuario, columns=['desempenio', 'puntaje', 'reg'])
    df1 = pd.DataFrame(datos_usuario1, columns=['desempenio3', 'puntaje', 'reg'])

    # Calcular el total de alumnos evaluados
    total_alumnos = df.shape[0]
    
    # Verificar si las columnas 'desempenio' y 'puntaje' existen
    if 'desempenio' not in df.columns or 'puntaje' not in df.columns:
        return HttpResponse("Error en los datos: columnas 'desempenio' o 'puntaje' no encontradas.")
    
    if 'desempenio3' not in df1.columns or 'puntaje' not in df1.columns:
        return HttpResponse("Error en los datos: columnas 'desempenio3' o 'puntaje' no encontradas.")
    
    # Definir el orden y colores para los labels
    orden_labels = ["Debajo del Nivel Básico", "Básico", "Satisfactorio", "Avanzado", "Calificación Incorrecta", "Sin Calificar"]
    colores = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
    
    # Ajustar los conteos según el orden definido
    conteo_desempenio = df['desempenio'].value_counts().reindex(orden_labels, fill_value=0)
    conteo_desempenio3 = df1['desempenio3'].value_counts().reindex(orden_labels, fill_value=0)
    
    # Calcular los porcentajes
    porcentajes = (conteo_desempenio / conteo_desempenio.sum()) * 100
    porcentajes3 = (conteo_desempenio3 / conteo_desempenio3.sum()) * 100
    
    # Crear etiquetas con cantidad y porcentaje
    etiquetas = [f"{label}: {conteo} ({porcentaje:.2f}%)" for label, conteo, porcentaje in zip(orden_labels, conteo_desempenio, porcentajes)]
    etiquetas3 = [f"{label}: {conteo} ({porcentaje:.2f}%)" for label, conteo, porcentaje in zip(orden_labels, conteo_desempenio3, porcentajes3)]
    
    # Calcular el promedio de puntaje
    promedio_puntaje = round(df['puntaje'].mean(), 2)
    
    # Obtener el nombre de la región o mostrar "Chaco"
    regional = 'Chaco' if mostrar_todo else ', '.join(df['reg'].unique())
    
    # Crear los gráficos de torta con Plotly
    fig = go.Figure(data=[go.Pie(labels=etiquetas, values=conteo_desempenio, marker=dict(colors=colores))])
    fig.update_layout(showlegend=True)
    
    fig3 = go.Figure(data=[go.Pie(labels=etiquetas3, values=conteo_desempenio3, marker=dict(colors=colores))])
    fig3.update_layout(showlegend=True)
    
    # Convertir las figuras a HTML
    graph_html = fig.to_html(full_html=False, default_height=500, default_width=700)
    graph_html3 = fig3.to_html(full_html=False, default_height=500, default_width=700)
    
    # Renderizar la plantilla y pasar ambos gráficos y el promedio de puntaje
    return render(request, 'lectocomp/graficoreg.html', {
        'grafico': graph_html,
        'grafico3': graph_html3,
        'promedio_puntaje': promedio_puntaje,
        'total_alumnos': total_alumnos,
        'regional': regional,
        'datos_disponibles': True
    })

def cargar_grafico_reg(request):    
    return render(request, 'lectocomp/graficoreg.html', {
        'datos_disponibles': False
    })


def mostrar_pdf_recomendaciones(request):
    pdf_url = "https://drive.google.com/file/d/1IxPdm0B40TVxeuzgiw_PXYvkEEBPpRVs/preview"
    return render(request, 'lectocomp/recomendaciones.html',{'pdf_url': pdf_url})

def mostrar_pdf_informefinal(request):
    pdf_url = "https://drive.google.com/file/d/1KIRcY6BfwwR9oyttD3xYqiixC_2akBfr/preview"
    return render(request, 'lectocomp/informefinal.html',{'pdf_url': pdf_url})


#####################################################################
#                 MUESTRA GRAFICO FILTRADO POR LOCALIDAD            #
#####################################################################

def mostrar_grafico_localidad(request):
    localidades=[]       
    
    # Obtine las localidades únicas
    with connection.cursor() as cursor:
        cursor.execute("SELECT DISTINCT localidad FROM public.v_teslecturamayoeval WHERE localidad !='None'")
        localidades = [row[0] for row in cursor.fetchall()]
        print('Localidades cargadas:', localidades)
    
     # Si es una solicitud estándar, renderiza la plantilla
    context = {
        'localidades': localidades,        
    }
    print('Contexto:', context)
    return render(request, 'lectocomp/graficolocalidades.html', context)


def mostrar_grafico_loc(request):
    # Obtiene las localidades únicas para cargar en el select
    with connection.cursor() as cursor:
        cursor.execute("SELECT DISTINCT localidad FROM public.v_teslecturamayoeval WHERE localidad !='None'")
        localidades = [row[0] for row in cursor.fetchall()]
    
    # Obtiene los valores seleccionados en el select    
    localidades_seleccionadas = request.GET.get('localidad')   
    
    print('localidad_seleccionada:',localidades_seleccionadas)    
    
    # Establece conexión con la base de datos PostgreSQL
    with psycopg2.connect(
        dbname="visualizador",
        user="visualizador",
        password="Estadisticas24",
        host="visoreducativochaco.com.ar"
    ) as conn:
        with conn.cursor() as cursor:            
                # Filtrar los datos para las regiones seleccionadas
                if localidades_seleccionadas:                    
                    query = f"SELECT desempenio, puntaje, localidad FROM public.v_teslecturamayoeval WHERE localidad = '{localidades_seleccionadas}'"
                    cursor.execute(query, localidades_seleccionadas)
                    datos_usuario = cursor.fetchall()
                    print('datos de usuario:', datos_usuario)
                    query1 = f"SELECT desempenio3, puntaje, localidad FROM public.v_teslecturamayoeval WHERE localidad = '{localidades_seleccionadas}'"
                    cursor.execute(query1, localidades_seleccionadas)
                    datos_usuario1 = cursor.fetchall()
                else:
                    return render(request, 'lectocomp/graficolocalidades.html', {
                        'datos_disponibles': False
                    })
    
    if not datos_usuario or not datos_usuario1:
        return render(request, 'lectocomp/graficolocalidades.html', {
            'datos_disponibles': False
        })
    
    # Convertir los datos a DataFrames de pandas
    df = pd.DataFrame(datos_usuario, columns=['desempenio', 'puntaje', 'localidad'])
    df1 = pd.DataFrame(datos_usuario1, columns=['desempenio3', 'puntaje', 'localidad'])

    # Calcular el total de alumnos evaluados
    total_alumnos = df.shape[0]
    
    # Verificar si las columnas 'desempenio' y 'puntaje' existen
    if 'desempenio' not in df.columns or 'puntaje' not in df.columns:
        return HttpResponse("Error en los datos: columnas 'desempenio' o 'puntaje' no encontradas.")
    
    if 'desempenio3' not in df1.columns or 'puntaje' not in df1.columns:
        return HttpResponse("Error en los datos: columnas 'desempenio3' o 'puntaje' no encontradas.")
    
    # Definir el orden y colores para los labels
    orden_labels = ["Debajo del Nivel Básico", "Básico", "Satisfactorio", "Avanzado", "Calificación Incorrecta", "Sin Calificar"]
    colores = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
    
    # Ajustar los conteos según el orden definido
    conteo_desempenio = df['desempenio'].value_counts().reindex(orden_labels, fill_value=0)
    conteo_desempenio3 = df1['desempenio3'].value_counts().reindex(orden_labels, fill_value=0)
    
    # Calcular los porcentajes
    porcentajes = (conteo_desempenio / conteo_desempenio.sum()) * 100
    porcentajes3 = (conteo_desempenio3 / conteo_desempenio3.sum()) * 100
    
    # Crear etiquetas con cantidad y porcentaje
    etiquetas = [f"{label}: {conteo} ({porcentaje:.2f}%)" for label, conteo, porcentaje in zip(orden_labels, conteo_desempenio, porcentajes)]
    etiquetas3 = [f"{label}: {conteo} ({porcentaje:.2f}%)" for label, conteo, porcentaje in zip(orden_labels, conteo_desempenio3, porcentajes3)]
    
    # Calcular el promedio de puntaje
    promedio_puntaje = round(df['puntaje'].mean(), 2)
    
    # Obtener el nombre de la región o mostrar "Chaco"
    localidad = localidades_seleccionadas
    
    # Crear los gráficos de torta con Plotly
    fig = go.Figure(data=[go.Pie(labels=etiquetas, values=conteo_desempenio, marker=dict(colors=colores))])
    fig.update_layout(showlegend=True)
    
    fig3 = go.Figure(data=[go.Pie(labels=etiquetas3, values=conteo_desempenio3, marker=dict(colors=colores))])
    fig3.update_layout(showlegend=True)
    
    # Convertir las figuras a HTML
    graph_html = fig.to_html(full_html=False, default_height=500, default_width=700)
    graph_html3 = fig3.to_html(full_html=False, default_height=500, default_width=700)
    
    # Renderizar la plantilla y pasar ambos gráficos y el promedio de puntaje
    return render(request, 'lectocomp/graficolocalidades.html', {
        'grafico': graph_html,
        'grafico3': graph_html3,
        'promedio_puntaje': promedio_puntaje,
        'total_alumnos': total_alumnos,
        'localidades': localidades,
        'localidad': localidades_seleccionadas,
        'datos_disponibles': True
    })

def cargar_grafico_loc(request):    
    return render(request, 'lectocomp/graficolocalidades.html', {
        'datos_disponibles': False
    })