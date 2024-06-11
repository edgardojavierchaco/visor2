from django.http import HttpResponse
import psycopg2
import pandas as pd
import plotly.graph_objs as go
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
import logging

logger = logging.getLogger(__name__)

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
        logger.error(f"Error al conectar a la base de datos: {e}")
        return None

@login_required
def mostrar_grafico(request):
    logger.debug("Inicio de la función mostrar_grafico")
    connection = conectar_bd()
    if connection is None:
        return HttpResponse("Error al conectar a la base de datos")

    cueanexo_usuario = request.user.username

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM public.lectura_oplecturaabril WHERE cueanexo=%s", [cueanexo_usuario])
            columns = [col[0] for col in cursor.description]
            datos_usuario_list = [dict(zip(columns, row)) for row in cursor.fetchall()]

        if not datos_usuario_list:
            return HttpResponse("No hay datos disponibles para esta región")

        df = pd.DataFrame(datos_usuario_list)

        if 'desempeño' not in df.columns or 'puntaje' not in df.columns:
            return HttpResponse("Error en los datos: columnas 'desempeño' o 'puntaje' no encontradas.")

        total_alumnos = df.shape[0]
        conteo_desempeño = df['desempeño'].value_counts()
        porcentajes = conteo_desempeño / conteo_desempeño.sum() * 100
        
        promedio_puntaje = round(df['puntaje'].mean(), 2)
        escuela = df['escuela'].iloc[0]

        # Crear el gráfico utilizando plotly.graph_objs
        trace = go.Pie(labels=conteo_desempeño.index, values=round(porcentajes,2))
        layout = go.Layout(            
            annotations=[
                dict(
                    text="En el gráfico se presentan porcentajes de alumnos a los que se les aplicó el Test y",
                    xref="paper", yref="paper",
                    x=0.5, y=-0.15,
                    showarrow=False,
                    font=dict(size=12),
                    xanchor='center'
                ),
                dict(
                    text="los porcentajes de alumnos que no fueron calificados o calificados incorrectamente.",
                    xref="paper", yref="paper",
                    x=0.5, y=-0.2,
                    showarrow=False,
                    font=dict(size=12),
                    xanchor='center'
                )
            ],
            margin=dict(t=40, b=120)
        )
        fig = go.Figure(data=[trace], layout=layout)

        graph_html = fig.to_html(full_html=False)

        return render(request, 'lectocomp/grafico.html', {
            'grafico': graph_html,
            'promedio_puntaje': promedio_puntaje,
            'total_alumnos': total_alumnos,
            'escuela': escuela,
        })
    except Exception as e:
        logger.error(f"Error en mostrar_grafico: {e}")
        return HttpResponse("Error en mostrar_grafico")
    finally:
        connection.close()
