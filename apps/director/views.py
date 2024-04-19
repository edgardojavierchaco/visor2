import psycopg2
import pandas as pd
from django.shortcuts import render
from django.conf import settings

from apps.director.models import PadronOfertas


def obtener_cueanexo_y_id_establecimiento_por_usuario(usuario):
    # Establecer la conexión con la base de datos externa
    connection = psycopg2.connect(
        dbname='Padron',
        user='visualizador',
        password='Estadisticas24',
        host='sigechaco.com.ar',
        port='5432'
    )

    # Crear un cursor para ejecutar consultas
    cursor = connection.cursor()

    # Ejecutar la consulta SQL
    cursor.execute("SELECT cueanexo, id_establecimiento,oferta FROM public.padron_ofertas WHERE cueanexo = %s", [usuario])

    # Obtener los resultados
    resultados = cursor.fetchall()
    print(resultados)
    # Cerrar el cursor y la conexión
    cursor.close()
    connection.close()

    return resultados

def obtener_cueanexos_por_id_establecimiento(id_establecimiento):
    try:
        # Establecer la conexión con la base de datos externa
        connection = psycopg2.connect(
            dbname='Padron',
            user='visualizador',
            password='Estadisticas24',
            host='sigechaco.com.ar',
            port='5432'
        )

        # Crear un cursor para ejecutar consultas
        cursor = connection.cursor()        
        
        # Ejecutar la consulta SQL para obtener los cueanexo por id_establecimiento
        cursor.execute("SELECT cueanexo FROM public.padron_ofertas WHERE id_establecimiento = %s and est_oferta='Activo'", [id_establecimiento])

        # Obtener los resultados
        resultados = cursor.fetchall()
        
        # Cerrar el cursor y la conexión
        cursor.close()
        connection.close()

        return resultados

    except psycopg2.Error as e:
        print("Error al obtener los resultados:", e)
        return []

def obtener_ciclo_por_cueanexo(cueanexo):
    try:
        # Obtener la oferta del usuario
        resultados_oferta = obtener_cueanexo_y_id_establecimiento_por_usuario(cueanexo)
        oferta_usuario = resultados_oferta[0][2] if resultados_oferta else None
        
        # Determinar la función a ejecutar según la oferta del usuario
        if oferta_usuario == 'Adultos - Formación Profesional':
            consulta_funcion = "funcion.visor_matric_adulto_fp('ra_carga2023')"
        elif oferta_usuario == 'Adultos - Primaria ':
            consulta_funcion = "funcion.visor_matric_adulto_primaria('ra_carga2023')"
        elif oferta_usuario == 'Adultos - Secundaria Completa':
            consulta_funcion = "funcion.visor_matric_adulto_secundaria('ra_carga2023')"
        elif oferta_usuario == 'Común - Jardín de Infantes' or oferta_usuario == 'Común - Jardín maternal':
            consulta_funcion = "funcion.visor_matric_comun_inicial('ra_carga2023')"
        elif oferta_usuario == 'Común - Primaria de 7 años':
            consulta_funcion = "funcion.visor_matric_comun_primaria('ra_carga2023')"
        elif oferta_usuario == 'Común - Secundaria Completa req. 7 años':
            consulta_funcion = "funcion.visor_matric_comun_secundaria('ra_carga2023')"        
                  
        # Establecer la conexión con la base de datos externa
        connection = psycopg2.connect(
            dbname='visualizador',
            user='visualizador',
            password='Estadisticas24',
            host='sigechaco.com.ar',
            port='5432'
        )

        # Crear un cursor para ejecutar consultas
        cursor = connection.cursor()

        
        # Ejecutar la consulta SQL para obtener los grados por cueanexo
        cursor.execute(f"SELECT DISTINCT grado FROM {consulta_funcion} WHERE cueanexo = %s", [cueanexo])

        # Obtener los resultados
        ciclos = cursor.fetchall()
        
        # Cerrar el cursor y la conexión
        cursor.close()
        connection.close()

        return [ciclo[0] for ciclo in ciclos]  # Extraer los ciclos de la lista de tuplas

    except psycopg2.Error as e:
        print("Error al obtener los ciclos:", e)
        return []

def obtener_secciones_por_cueanexo_y_ciclo(cueanexo, ciclo_etapa):
    try:
        # Obtener la oferta del usuario
        resultados_oferta = obtener_cueanexo_y_id_establecimiento_por_usuario(cueanexo)
        oferta_usuario = resultados_oferta[0][2] if resultados_oferta else None
        
        # Determinar la función a ejecutar según la oferta del usuario
        if oferta_usuario == 'Adultos - Formación Profesional':
            consulta_funcion = "funcion.visor_matric_adulto_fp('ra_carga2023')"
        elif oferta_usuario == 'Adultos - Primaria ':
            consulta_funcion = "funcion.visor_matric_adulto_primaria('ra_carga2023')"
        elif oferta_usuario == 'Adultos - Secundaria Completa':
            consulta_funcion = "funcion.visor_matric_adulto_secundaria('ra_carga2023')"
        elif oferta_usuario == 'Común - Jardín de Infantes' or oferta_usuario == 'Común - Jardín maternal':
            consulta_funcion = "funcion.visor_matric_comun_inicial('ra_carga2023')"
        elif oferta_usuario == 'Común - Primaria de 7 años':
            consulta_funcion = "funcion.visor_matric_comun_primaria('ra_carga2023')"
        elif oferta_usuario == 'Común - Secundaria Completa req. 7 años':
            consulta_funcion = "funcion.visor_matric_comun_secundaria('ra_carga2023')" 
            
        # Establecer la conexión con la base de datos externa
        connection = psycopg2.connect(
            dbname='visualizador',
            user='visualizador',
            password='Estadisticas24',
            host='sigechaco.com.ar',
            port='5432'
        )

        # Crear un cursor para ejecutar consultas
        cursor = connection.cursor()

        # Ejecutar la consulta SQL para obtener las secciones por cueanexo y grado
        cursor.execute(f"SELECT DISTINCT nom_secc FROM {consulta_funcion} WHERE cueanexo = %s AND grado = %s", [cueanexo, ciclo_etapa])

        # Obtener los resultados
        secciones = cursor.fetchall()
        print("secciones:",secciones)
        # Cerrar el cursor y la conexión
        cursor.close()
        connection.close()

        return [seccion[0] for seccion in secciones]  # Extraer las secciones de la lista de tuplas

    except psycopg2.Error as e:
        print("Error al obtener las secciones:", e)
        return []

def obtener_resultados_filtrados(nivel,cueanexo, ciclo_etapa,nom_seccion):
    try:
        print("Parámetros recibidos1:", nivel, cueanexo,ciclo_etapa,nom_seccion)
        # Establecer la conexión con la base de datos externa
        connection = psycopg2.connect(
            dbname='visualizador',
            user='visualizador',
            password='Estadisticas24',
            host='sigechaco.com.ar',
            port='5432'
        )

        # Crear un cursor para ejecutar consultas
        cursor = connection.cursor()

        # Ejecutar la consulta SQL para obtener los resultados filtrados
        print("Nivel:", nivel)  # Imprimir el valor de nivel para depuración
        consulta_sql = "SELECT * FROM funcion.visor_matric_adulto_primaria('ra_carga2023') WHERE cueanexo=%s and grado=%s and nom_secc=%s"
        print("Consulta SQL:", consulta_sql % (cueanexo, ciclo_etapa, nom_seccion))  # Imprimir la consulta SQL para depuración
        cursor.execute(consulta_sql, (cueanexo, ciclo_etapa, nom_seccion))
        
        # Ejecutar la consulta SQL para obtener los resultados filtrados
        #cursor.execute("SELECT * FROM funcion.visor_matric_adulto_primaria('ra_carga2023') WHERE cueanexo=%s and grado=%s and nom_secc=%s")

        # Obtener los nombres de las columnas
        column_names = [desc[0] for desc in cursor.description]
        
        # Obtener los resultados
        totales = cursor.fetchall()
        print(totales)
        # Cerrar el cursor y la conexión
        cursor.close()
        connection.close()

        return column_names,totales

    except psycopg2.Error as e:
        print("Error al obtener los resultados filtrados:", e)
        return [],[]

def tu_vista(request):
    objetos_filtrados = PadronOfertas.objects.filter(cueanexo=request.user.username).values_list('id_establecimiento', flat=True)
    
    print('Objetos filtrados:', objetos_filtrados)
    
    listado_cueanexos=PadronOfertas.objects.filter(id_localizacion__in=objetos_filtrados).values_list('cueanexo', flat=True)
    print(listado_cueanexos)
    try:
        # Obtener el id_establecimiento del usuario
        usuario = request.user.username
        resultados = obtener_cueanexo_y_id_establecimiento_por_usuario(usuario)
        id_establecimiento_usuario = resultados[0][1] if resultados else None
        print("ID del establecimiento del usuario:", id_establecimiento_usuario)

        if id_establecimiento_usuario:
            # Realizar la nueva consulta filtrando por id_establecimiento
            cueanexos_filtrados = obtener_cueanexos_por_id_establecimiento(id_establecimiento_usuario)
            # Extraer solo el primer elemento de cada tupla en la lista de cueanexos filtrados
            cueanexos_filtrados = [resultado[0] for resultado in cueanexos_filtrados]
            print("Cueanexos filtrados:", cueanexos_filtrados)
        else:
            cueanexos_filtrados = []
        
        # Obtener el cueanexo y ciclo_etapa seleccionados en la lista desplegable
        cueanexo_seleccionado = request.GET.get('cueanexo', None)
        ciclo_etapa_seleccionado = request.GET.get('ciclo_etapa', None)
        filtrar_ciclo = request.GET.get('filtrar_ciclo', None)
        nom_seccion_seleccionado = request.GET.get('nom_seccion', None)
        filtrar_seccion = request.GET.get('filtrar_seccion', None)
        print("Parámetros recibidos2:", cueanexo_seleccionado, ciclo_etapa_seleccionado, nom_seccion_seleccionado)  # Agregar esta línea para depurar

        ciclos = []
        secciones = []
        totales = []
        nivel=resultados[0][2] if resultados else None
        column_name=[]
        if cueanexo_seleccionado:
            # Obtener los ciclos asociados al cueanexo seleccionado
            ciclos = obtener_ciclo_por_cueanexo(cueanexo_seleccionado)
            print("Ciclos filtrados:", ciclos)

            if ciclo_etapa_seleccionado:
                secciones = obtener_secciones_por_cueanexo_y_ciclo(cueanexo_seleccionado, ciclo_etapa_seleccionado)
                print("Secciones filtradas:", secciones)      
                
                if nom_seccion_seleccionado:
                    column_name,totales = obtener_resultados_filtrados(nivel,cueanexo_seleccionado, ciclo_etapa_seleccionado, nom_seccion_seleccionado)
                    # Eliminar la palabra "Totales" y los guiones bajos de los nombres de las columnas
                    column_name = [column.replace('_', ' ').replace('total', '') for column in column_name]
                    print("Nombres de las columnas:", column_name)  # Agregar esta línea para depurar
                    print("Totales obtenidos:", totales)  # Agregar esta línea para depurar
                    print("parametros3",nivel,cueanexo_seleccionado,ciclo_etapa_seleccionado,nom_seccion_seleccionado)
                    print("Totales obtenidos:", column_name, totales)  # Agregar esta línea para depurar
                                 
    except Exception as e:
        print("Error en la vista:", e)
        cueanexos_filtrados = []
        ciclos = []
        secciones = []
        totales = []
        column_name=[]
    # Convertir los resultados y los nombres de las columnas a un DataFrame de Pandas
    df_totales = pd.DataFrame(totales, columns=column_name)
    df_column_names = pd.DataFrame([column_name], columns=column_name)

    # Convertir los DataFrames a formato HTML
    tabla_totales = df_totales.to_html(index=False)
    tabla_column_names = df_column_names.to_html(index=False)
    print('pandas',tabla_totales)
    return render(request, 'directores/matricula.html', {'cueanexos_filtrados': cueanexos_filtrados, 'ciclos': ciclos, 'secciones': secciones, 'totales': tabla_totales, 'column_names': tabla_column_names})
