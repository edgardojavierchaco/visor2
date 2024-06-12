import plotly.graph_objs as go
from django.db import connection
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

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
