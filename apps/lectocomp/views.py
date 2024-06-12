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
    
    # Crear el gráfico de torta para los resultados_total_dni
    labels = [resultado[1] for resultado in resultados_total_dni]
    valores = [resultado[2] for resultado in resultados_total_dni]
    grafico_torta_total_dni = go.Figure(data=[go.Pie(labels=labels, values=valores)])
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
        host="relevamientoanual.com.ar"
    ) as conn:
        with conn.cursor() as cursor:
            if mostrar_todo:
                # Si se selecciona "Mostrar Todo", mostrar todos los datos
                query = "SELECT desempenio, puntaje, reg FROM public.teslecturamayo"
                cursor.execute(query)
            else:
                # Filtrar los datos para las regiones seleccionadas
                if regiones_seleccionadas:
                    placeholders = ','.join(['%s'] * len(regiones_seleccionadas))
                    query = f"SELECT desempenio, puntaje, reg FROM public.teslecturamayo WHERE reg IN ({placeholders})"
                    cursor.execute(query, tuple(regiones_seleccionadas))
                else:
                    return render(request, 'lectocomp/graficoreg.html', {
                        'datos_disponibles': False
                    })
            
            # Obtener los datos de la consulta
            datos_usuario = cursor.fetchall()
    
    if not datos_usuario:
        return render(request, 'lectocomp/graficoreg.html', {
            'datos_disponibles': False
        })
    
    # Convertir los datos a un DataFrame de pandas
    df = pd.DataFrame(datos_usuario, columns=['desempenio', 'puntaje', 'reg'])

    # Calcular el total de alumnos evaluados
    total_alumnos = df.shape[0]
    
    # Verificar si las columnas 'desempenio' y 'puntaje' existen
    if 'desempenio' not in df.columns or 'puntaje' not in df.columns:
        return HttpResponse("Error en los datos: columnas 'desempenio' o 'puntaje' no encontradas.")
    
    # Agrupar y contar por categoría de desempeño
    conteo_desempenio = df['desempenio'].value_counts()
    
    # Calcular los porcentajes
    porcentajes = (conteo_desempenio / conteo_desempenio.sum()) * 100
    
    # Calcular el promedio de puntaje
    promedio_puntaje = round(df['puntaje'].mean(), 2)
    
    # Obtener el nombre de la región o mostrar "Chaco"
    regional = 'Chaco' if mostrar_todo else ', '.join(df['reg'].unique())
    
    # Crear el gráfico de torta con Plotly
    fig = go.Figure(data=[go.Pie(labels=porcentajes.index, values=porcentajes)])
    fig.update_layout(
                      showlegend=True)
    
    # Convertir la figura a HTML
    graph_html = fig.to_html(full_html=False, default_height=500, default_width=700)
    
    # Renderizar la plantilla y pasar el gráfico y el promedio de puntaje
    return render(request, 'lectocomp/graficoreg.html', {
        'grafico': graph_html,
        'promedio_puntaje': promedio_puntaje,
        'total_alumnos': total_alumnos,
        'regional': regional,
        'datos_disponibles': True
    })

def cargar_grafico_reg(request):    
    return render(request, 'lectocomp/graficoreg.html', {
        'datos_disponibles': False
    })