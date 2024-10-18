import psycopg2
import os 
import dotenv
import plotly.graph_objs as go
import plotly.io as pio
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# Función para conectar a la base de datos
def conectar_bd():
    try:
        connection = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST'),
            user=os.getenv('POSTGRES_USER'),
            password=os.getenv('POSTGRES_PASSWORD'),
            database=os.getenv('POSTGRES_DB')
        )
        return connection
    except psycopg2.Error as e:
        # Manejar el error de conexión
        print(f"Error al conectar a la base de datos: {e}")
        return None


# datos por regional
def filter_data_efec_aban_rep(request):
    cueanexo = request.GET.get('region')
    connection = conectar_bd()

    if not connection:
        return render(request, 'error_conexion.html')

    try:
        cursor = connection.cursor()
        query_efec="""
            SELECT 
                vcuo.region_loc, 
                ts.categoria_modificada, 
                SUM(ts.tasa_efectiva) AS tasa_efectiva                
            FROM indicadores.tasas1_secundaria_ra2024 as ts
            LEFT JOIN public.v_capa_unica_ofertas as vcuo
            ON ts.cueanexo::text = vcuo.cueanexo::text
            WHERE ts.categoria_modificada != 'total' and vcuo.region_loc=%s
            GROUP BY vcuo.region_loc, ts.categoria_modificada
            ORDER BY vcuo.region_loc, ts.categoria_modificada;
        """
        
        query_aban="""
            SELECT 
                vcuo.region_loc, 
                ts.categoria_modificada,                 
                SUM(ts.tasa_abandono) AS tasa_abandono
            FROM indicadores.tasas1_secundaria_ra2024 as ts
            LEFT JOIN public.v_capa_unica_ofertas as vcuo
            ON ts.cueanexo::text = vcuo.cueanexo::text
            WHERE ts.categoria_modificada != 'total' and vcuo.region_loc=%s
            GROUP BY vcuo.region_loc, ts.categoria_modificada
            ORDER BY vcuo.region_loc, ts.categoria_modificada;
        """
        
        query_rep="""
            SELECT 
                vcuo.region_loc, 
                ts.categoria_modificada,                  
                SUM(ts.tasa_rep) AS tasa_repitencia
            FROM indicadores.tasas1_secundaria_ra2024 as ts
            LEFT JOIN public.v_capa_unica_ofertas as vcuo
            ON ts.cueanexo::text = vcuo.cueanexo::text
            WHERE ts.categoria_modificada != 'total' and vcuo.region_loc=%s
            GROUP BY vcuo.region_loc, ts.categoria_modificada
            ORDER BY vcuo.region_loc, ts.categoria_modificada;
        """
        
        cursor.execute(query_efec, (cueanexo,))
        data_efec = cursor.fetchall()
        
        cursor.execute(query_aban, (cueanexo,))
        data_aban = cursor.fetchall()
         
        cursor.execute(query_rep, (cueanexo,))
        data_rep = cursor.fetchall()

        if not data_efec or not data_aban or not data_rep:
            return render(request, 'consulta_vacia.html')

        # Mapeo de categoría de la consulta a los años del gráfico
        mapeo_categorias = {
            '1er Año/Grado': '1ero',
            '2do Año/Grado': '2do',
            '3er Año/Grado': '3ero',
            '4to Año/Grado': '4to',
            '5to Año/Grado': '5to',
            '6to Año/Grado': '6to'
        }

        labels = ['1ero', '2do', '3ero', '4to', '5to', '6to']
        
        def map_tasas_por_año(data, labels, mapeo):
            # Crear un diccionario para inicializar las tasas con 0 por año
            tasas_por_año = {label: 0 for label in labels}
            for row in data:
                categoria = row[1]
                tasa = row[2]
                # Mapear la categoría al año correspondiente usando el diccionario
                if categoria in mapeo:
                    año_mapeado = mapeo[categoria]
                    tasas_por_año[año_mapeado] = float(tasa)  # Asegúrate de que sea un número
            return [tasas_por_año[label] for label in labels]  # Devolver los valores en el orden de las etiquetas
        
        tasa_efectiva = map_tasas_por_año(data_efec, labels, mapeo_categorias)
        tasa_abandono = map_tasas_por_año(data_aban, labels, mapeo_categorias)
        tasa_repitencia = map_tasas_por_año(data_rep, labels, mapeo_categorias)
                
        titulo = f'<b>Tasa Efectiva, Abandono y Repitencia del Nivel Secundario por Año</b> - Regional: {cueanexo}'
        fig = go.Figure()
        fig.add_trace(go.Bar(x=labels, y=tasa_efectiva, name='Efectiva', marker_color='red'))
        fig.add_trace(go.Bar(x=labels, y=tasa_abandono, name='Abandono', marker_color='green'))
        fig.add_trace(go.Bar(x=labels, y=tasa_repitencia, name='Repitencia', marker_color='blue'))
        fig.update_layout(title=titulo, title_x=0.5, xaxis_title='Año 2024', yaxis_title='Tasa', width=800, height=600)

        graph_html = pio.to_html(fig, full_html=False)
        context = {
            'grafico': graph_html,
            'cueanexo': cueanexo,
            'nom_est': data_efec,
        }
        
        return render(request, 'indicadores/efecabanrepsecunreg.html', context)
    finally:
        cursor.close()
        connection.close()


# datos totales Chaco
def filter_data_efec_aban_rep_total(request):
    cueanexo = 'Chaco'
    connection = conectar_bd()

    if not connection:
        return render(request, 'error_conexion.html')

    try:
        cursor = connection.cursor()
        query_efec="""
            SELECT 
                vcuo.region_loc, 
                ts.categoria_modificada, 
                SUM(ts.tasa_efectiva) AS tasa_efectiva                
            FROM indicadores.tasas1_secundaria_ra2024 as ts
            LEFT JOIN public.v_capa_unica_ofertas as vcuo
            ON ts.cueanexo::text = vcuo.cueanexo::text
            WHERE ts.categoria_modificada != 'total'
            GROUP BY vcuo.region_loc, ts.categoria_modificada
            ORDER BY vcuo.region_loc, ts.categoria_modificada;
        """
        
        query_aban="""
            SELECT 
                vcuo.region_loc, 
                ts.categoria_modificada,                 
                SUM(ts.tasa_abandono) AS tasa_abandono
            FROM indicadores.tasas1_secundaria_ra2024 as ts
            LEFT JOIN public.v_capa_unica_ofertas as vcuo
            ON ts.cueanexo::text = vcuo.cueanexo::text
            WHERE ts.categoria_modificada != 'total'
            GROUP BY vcuo.region_loc, ts.categoria_modificada
            ORDER BY vcuo.region_loc, ts.categoria_modificada;
        """
        
        query_rep="""
            SELECT 
                vcuo.region_loc, 
                ts.categoria_modificada,                  
                SUM(ts.tasa_rep) AS tasa_repitencia
            FROM indicadores.tasas1_secundaria_ra2024 as ts
            LEFT JOIN public.v_capa_unica_ofertas as vcuo
            ON ts.cueanexo::text = vcuo.cueanexo::text
            WHERE ts.categoria_modificada != 'total'
            GROUP BY vcuo.region_loc, ts.categoria_modificada
            ORDER BY vcuo.region_loc, ts.categoria_modificada;
        """
        
        cursor.execute(query_efec)
        data_efec = cursor.fetchall()
        
        cursor.execute(query_aban)
        data_aban = cursor.fetchall()
         
        cursor.execute(query_rep)
        data_rep = cursor.fetchall()

        if not data_efec or not data_aban or not data_rep:
            return render(request, 'consulta_vacia.html')

        # Mapeo de categoría de la consulta a los años del gráfico
        mapeo_categorias = {
            '1er Año/Grado': '1ero',
            '2do Año/Grado': '2do',
            '3er Año/Grado': '3ero',
            '4to Año/Grado': '4to',
            '5to Año/Grado': '5to',
            '6to Año/Grado': '6to'
        }

        labels = ['1ero', '2do', '3ero', '4to', '5to', '6to']
        
        def map_tasas_por_año(data, labels, mapeo):
            # Crear un diccionario para inicializar las tasas con 0 por año
            tasas_por_año = {label: 0 for label in labels}
            for row in data:
                categoria = row[1]
                tasa = row[2]
                # Mapear la categoría al año correspondiente usando el diccionario
                if categoria in mapeo:
                    año_mapeado = mapeo[categoria]
                    tasas_por_año[año_mapeado] = float(tasa)  # Asegúrate de que sea un número
            return [tasas_por_año[label] for label in labels]  # Devolver los valores en el orden de las etiquetas
        
        tasa_efectiva = map_tasas_por_año(data_efec, labels, mapeo_categorias)
        tasa_abandono = map_tasas_por_año(data_aban, labels, mapeo_categorias)
        tasa_repitencia = map_tasas_por_año(data_rep, labels, mapeo_categorias)
                
        titulo = f'<b>Tasa Efectiva, Abandono y Repitencia del Nivel Secundario por Año</b> : {cueanexo}'
        fig = go.Figure()
        fig.add_trace(go.Bar(x=labels, y=tasa_efectiva, name='Efectiva', marker_color='red'))
        fig.add_trace(go.Bar(x=labels, y=tasa_abandono, name='Abandono', marker_color='green'))
        fig.add_trace(go.Bar(x=labels, y=tasa_repitencia, name='Repitencia', marker_color='blue'))
        fig.update_layout(title=titulo, title_x=0.5, xaxis_title='Año 2024', yaxis_title='Tasa', width=800, height=600)

        graph_html = pio.to_html(fig, full_html=False)
        context = {
            'grafico': graph_html,
            'cueanexo': cueanexo,
            'nom_est': data_efec,
        }
        
        return render(request, 'indicadores/efecabanrepsecuntotal.html', context)
    finally:
        cursor.close()
        connection.close()

