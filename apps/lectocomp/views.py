import pandas as pd
import plotly.express as px
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import HttpResponse
from django.db import connection

@login_required
def mostrar_grafico(request):
    cueanexo_usuario = request.user.username
    
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
    porcentajes = (conteo_desempeño / conteo_desempeño.sum()) * 100
    porcentajes = porcentajes.round(2)
    promedio_puntaje = round(df['puntaje'].mean(), 2)
    escuela = df['escuela'].iloc[0]

    fig = px.pie(names=conteo_desempeño.index, values=porcentajes, width=800, height=600)
    
    # Añadir anotación para el pie de página
    fig.add_annotation(
        text="En el gráfico se presentan porcentajes de alumnos a los que se les aplicó el Test y",
        xref="paper", yref="paper",
        x=0.5, y=-0.15,
        showarrow=False,
        font=dict(size=12),
        xanchor='center'
    )

    fig.add_annotation(
        text="los porcentajes de alumnos que no fueron calificados o calificados incorrectamente.",
        xref="paper", yref="paper",
        x=0.5, y=-0.2,
        showarrow=False,
        font=dict(size=12),
        xanchor='center'
    )

    # Ajustar márgenes para que las anotaciones se vean correctamente
    fig.update_layout(
        margin=dict(t=40, b=120)  # Ajustar margen inferior para que el texto quede dentro del área del gráfico
    )

    graph_html = fig.to_html(full_html=False)

    return render(request, 'lectura/grafico.html', {
        'grafico': graph_html,
        'promedio_puntaje': promedio_puntaje,
        'total_alumnos': total_alumnos,
        'escuela': escuela,
    })

