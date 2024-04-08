import psycopg2
import pandas as pd
from django.shortcuts import render
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View

# Clase para administrar la conexión a la base de datos como un contexto
class DatabaseConnection:
    def __init__(self, dbname):
        self.connection = None
        self.dbname = dbname

    def __enter__(self):
        # Establecer la conexión con la base de datos
        self.connection = psycopg2.connect(
            dbname=self.dbname,
            user='visualizador',
            password='Estadisticas24',
            host='sigechaco.com.ar',
            port='5432'
        )
        return self.connection

    def __exit__(self, exc_type, exc_value, traceback):
        # Cerrar la conexión al salir del contexto
        if self.connection:
            self.connection.close()

def obtener_cueanexo_y_id_establecimiento_por_usuario(usuario):
    # Usar la conexión dentro de un contexto para la base de datos "Padron"
    with DatabaseConnection('Padron') as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT cueanexo, id_establecimiento,oferta FROM public.padron_ofertas WHERE cueanexo = %s and est_oferta='Activo'", [usuario])
        resultados = cursor.fetchall()
        print("resultados0:",resultados)
        cursor.close()
    return resultados

def obtener_cueanexos_por_id_establecimiento(id_establecimiento):    
    try:
        # Usar la conexión dentro de un contexto para la base de datos "Padron"
        with DatabaseConnection('Padron') as connection:
            cursor = connection.cursor()        
            cursor.execute("SELECT cueanexo FROM public.padron_ofertas WHERE id_establecimiento = %s and est_oferta='Activo'", [id_establecimiento])
            resultados = cursor.fetchall()
            cursor.close()
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
        elif oferta_usuario == 'Común - Primaria de 7 años ':
            consulta_funcion = "funcion.visor_matric_comun_primaria('ra_carga2023')"
        elif oferta_usuario == 'Común - Secundaria Completa req. 7 años ':
            consulta_funcion = "funcion.visor_matric_comun_secundaria('ra_carga2023')"        

        # Usar la conexión dentro de un contexto para la base de datos "Visualizador"
        with DatabaseConnection('visualizador') as connection:
            cursor = connection.cursor()

            # Ejecutar la consulta SQL para obtener los grados por cueanexo
            cursor.execute(f"SELECT DISTINCT grado FROM {consulta_funcion} WHERE cueanexo = %s", [cueanexo])

            # Obtener los resultados
            ciclos = cursor.fetchall()

            cursor.close()

        return [ciclo[0] for ciclo in ciclos]  # Extraer los ciclos de la lista de tuplas

    except psycopg2.Error as e:
        print("Error al obtener los ciclos:", e)
        return []

def obtener_secciones_por_cueanexo_y_ciclo(cueanexo, ciclo_etapa):
    try:
        # Obtener la oferta del usuario
        resultados_oferta = obtener_cueanexo_y_id_establecimiento_por_usuario(cueanexo)
        oferta_usuario = resultados_oferta[0][2] if resultados_oferta else None
        print("oferta usuario:",oferta_usuario)  
              
        # Determinar la función a ejecutar según la oferta del usuario
        if oferta_usuario == 'Adultos - Formación Profesional':
            consulta_funcion = "funcion.visor_matric_adulto_fp('ra_carga2023')"
        elif oferta_usuario == 'Adultos - Primaria ':
            consulta_funcion = "funcion.visor_matric_adulto_primaria('ra_carga2023')"
        elif oferta_usuario == 'Adultos - Secundaria Completa':
            consulta_funcion = "funcion.visor_matric_adulto_secundaria('ra_carga2023')"
        elif oferta_usuario == 'Común - Jardín de Infantes' or oferta_usuario == 'Común - Jardín maternal':
            consulta_funcion = "funcion.visor_matric_comun_inicial('ra_carga2023')"
        elif oferta_usuario == 'Común - Primaria de 7 años ':
            consulta_funcion = "funcion.visor_matric_comun_primaria('ra_carga2023')"
        elif oferta_usuario == 'Común - Secundaria Completa req. 7 años ':
            consulta_funcion = "funcion.visor_matric_comun_secundaria('ra_carga2023')" 
            
        # Usar la conexión dentro de un contexto para la base de datos "Visualizador"
        with DatabaseConnection('visualizador') as connection:
            cursor = connection.cursor()

            # Ejecutar la consulta SQL para obtener las secciones por cueanexo y grado
            cursor.execute(f"SELECT DISTINCT nom_secc FROM {consulta_funcion} WHERE cueanexo = %s AND grado = %s", [cueanexo, ciclo_etapa])

            # Obtener los resultados
            secciones = cursor.fetchall()

            cursor.close()

        return [seccion[0] for seccion in secciones]  # Extraer las secciones de la lista de tuplas

    except psycopg2.Error as e:
        print("Error al obtener las secciones:", e)
        return []

def obtener_resultados_filtrados(nivel,cueanexo, ciclo_etapa,nom_seccion):
    try:
        # Obtener la oferta del usuario
        resultados_oferta = obtener_cueanexo_y_id_establecimiento_por_usuario(cueanexo)
        oferta_usuario = resultados_oferta[0][2] if resultados_oferta else None
        print("Parámetros recibidos1:", nivel, cueanexo,ciclo_etapa,nom_seccion)
        
        # Usar la conexión dentro de un contexto para la base de datos "ra_carga2023"
        with DatabaseConnection('ra_carga2023') as connection:
            cursor = connection.cursor()

            # Ejecutar la consulta SQL para obtener los resultados filtrados
            #print("Nivel:", nivel)  # Imprimir el valor de nivel para depuración
            #consulta_sql = "SELECT * FROM public.obtener_matriculas2(%s, %s, %s, %s)"
            #print("Consulta SQL:", consulta_sql % (nivel, cueanexo, ciclo_etapa, nom_seccion))  # Imprimir la consulta SQL para depuración
            #cursor.execute(consulta_sql, (nivel, cueanexo, ciclo_etapa, nom_seccion))
            
            # Determinar la función a ejecutar según la oferta del usuario
            if oferta_usuario == 'Adultos - Formación Profesional' or oferta_usuario == 'Adultos - Primaria ':            
                cursor.execute("""SELECT * FROM public.obtener_matriculas3(%s, %s, %s, %s)
                                AS (cueanexo character varying, "Año" character varying, nom_secc character varying, total_edad_13_a_18 integer, total_edad_19_a_29 integer, total_edad_30_a_55_y_mas integer);"""
                                , (nivel, cueanexo, ciclo_etapa, nom_seccion))
            elif oferta_usuario == 'Adultos - Secundaria Completa':
                cursor.execute("""SELECT * FROM public.obtener_matriculas3(%s, %s, %s, %s)
                                AS (cueanexo character varying, Ciclo character varying, nom_secc character varying, total_edad_14_a_18 integer, total_edad_19_a_29 integer, total_edad_30_a_55_y_mas integer);"""
                                , (nivel, cueanexo, ciclo_etapa, nom_seccion))
            elif oferta_usuario == 'Común - Jardín de Infantes' or oferta_usuario == 'Común - Jardín maternal':
                cursor.execute("""SELECT * FROM public.obtener_matriculas3(%s, %s, %s, %s)
                                AS (cueanexo character varying, Sala character varying, nom_secc character varying, menos_1_año integer, un_año integer, dos_años integer, tres_año integer, cuatro_años integer, cinco_años integer, seis_años integer);"""
                                , (nivel, cueanexo, ciclo_etapa, nom_seccion))
            elif oferta_usuario == 'Común - Primaria de 7 años ':
                cursor.execute("""SELECT * FROM public.obtener_matriculas3(%s, %s, %s, %s)
                                AS (cueanexo character varying, Grado character varying, nom_secc character varying, edad_5 integer, edad_6 integer, edad_7 integer, edad_8 integer, edad_9 integer, edad_10 integer, edad_11 integer, edad_12 integer, total_edad_13_a_18_y_más integer);"""
                                , (nivel, cueanexo, ciclo_etapa, nom_seccion))
            elif oferta_usuario == 'Común - Secundaria Completa req. 7 años ':
                cursor.execute("""SELECT * FROM public.obtener_matriculas3(%s, %s, %s, %s)
                                AS (cueanexo character varying, "Año" character varying, nom_secc character varying, edad_12 integer, edad_13 integer, edad_14 integer, edad_15 integer, edad_16 integer, edad_17 integer, edad_18 integer, edad_19 integer, total_edad_20_a_25_y_mas integer);"""
                                , (nivel, cueanexo, ciclo_etapa, nom_seccion))

            # Obtener los nombres de las columnas
            column_names = [desc[0] for desc in cursor.description] # type: ignore
            
            # Obtener los resultados
            totales = cursor.fetchall()
            print(totales)

            cursor.close()

        return column_names, totales

    except psycopg2.Error as e:
        print("Error al obtener los resultados filtrados:", e)
        return [], []


class TuVista(LoginRequiredMixin,View):
    def get(self, request):
        try:
            usuario = request.user.username
            resultados = obtener_cueanexo_y_id_establecimiento_por_usuario(usuario)
            id_establecimiento_usuario = resultados[0][1] if resultados else None
            print("ID del establecimiento del usuario:", id_establecimiento_usuario)

            if id_establecimiento_usuario:
                cueanexos_filtrados = obtener_cueanexos_por_id_establecimiento(id_establecimiento_usuario)
                cueanexos_filtrados = [resultado[0] for resultado in cueanexos_filtrados]
                print("Cueanexos filtrados:", cueanexos_filtrados)
            else:
                cueanexos_filtrados = []
            
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
            column_name_upper=[]
            if cueanexo_seleccionado:
                ciclos = obtener_ciclo_por_cueanexo(cueanexo_seleccionado)
                print("Ciclos filtrados:", ciclos)

                if ciclo_etapa_seleccionado:
                    secciones = obtener_secciones_por_cueanexo_y_ciclo(cueanexo_seleccionado, ciclo_etapa_seleccionado)
                    print("Secciones filtradas:", secciones)      
                    
                    if nom_seccion_seleccionado:
                        column_name,totales = obtener_resultados_filtrados(nivel,cueanexo_seleccionado, ciclo_etapa_seleccionado, nom_seccion_seleccionado)
                        column_name = [column.replace('_', ' ').replace('total', '') for column in column_name]
                        column_name_upper=[name.upper() for name in column_name]
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
            column_name_upper=[]
            
        df_totales = pd.DataFrame(totales, columns=column_name_upper)
        df_column_names = pd.DataFrame([column_name_upper], columns=column_name_upper)

        tabla_totales = df_totales.to_html(index=False)
        tabla_column_names = df_column_names.to_html(index=False)
        
        return render(request, 'confidencial/matricula.html', {'cueanexos_filtrados': cueanexos_filtrados, 'ciclos': ciclos, 'secciones': secciones, 'totales': tabla_totales, 'column_names': tabla_column_names})
