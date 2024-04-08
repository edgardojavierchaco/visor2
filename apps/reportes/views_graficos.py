import psycopg2
import pandas as pd
import matplotlib.pyplot as plt
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import os

# Función para conectar a la base de datos
def conectar_bd(request):
    try:
        connection = psycopg2.connect(
            host='sigechaco.com.ar',
            user='visualizador',
            password='Estadisticas24',
            database='visualizador',
        )
        return connection
    except psycopg2.Error as e:
        # Manejar el error de conexión
        return None

# Vista para mostrar el formulario de filtrado de cargos
def filtrado_cargos(request):
    return render(request, 'reportes/filter_cargos.html')

# Vista para mostrar el formulario de filtrado de docentes
def filtrado_docentes(request):
    return render(request, 'reportes/filter_docentes.html')

# Vista para mostrar el formulario de filtrado de horas
def filtrado_horas(request):
    return render(request, 'reportes/filter_horas.html')
# Vista para procesar los datos del formulario de filtrado de cargos


@csrf_exempt
def filter_data_cargos(request):
    if request.method == 'POST':        
        cueanexo = request.POST.get('Cueanexo')
        ambito = request.POST.get('Ambito')
        sector = request.POST.get('Sector')
        region = request.POST.get('Region')
        departamento = request.POST.get('Departamento')
        localidad = request.POST.get('Localidad')
        relevamiento = request.POST.get('Relevamiento')

        # Validar que tvista esté en la lista de opciones válidas
        opciones_validas = [
            'visor_cargo_adulto_primaria',
            'visor_cargo_adulto_secundaria',
            'visor_cargo_comun_artistica',
            'visor_cargo_comun_inicial',
            'visor_cargo_comun_primaria',
            'visor_cargo_comun_secundaria',
            'visor_cargo_comun_servicios_complementarios',
            'visor_cargo_comun_snu',
            'visor_cargo_especial_tln',
            'visor_cargos_adulto_fp'
        ]

        # Obtener el valor seleccionado para tvista
        tvista = request.POST.get('Vista')
        print(relevamiento, tvista, sector)

        # Validar que tvista esté en la lista de opciones válidas
        if tvista not in opciones_validas:
            return render(request, 'error.html', {'mensaje': 'Opción de vista no válida'})

        # Asignar un valor descriptivo a la opción de tvista seleccionada
        opciones_descriptivas = {
            'visor_cargo_adulto_primaria': 'Adulto Primaria',
            'visor_cargo_adulto_secundaria': 'Adulto Secundaria',
            'visor_cargo_comun_artistica': 'Común Artística',
            'visor_cargo_comun_inicial': 'Común Inicial',
            'visor_cargo_comun_primaria': 'Común Primaria',
            'visor_cargo_comun_secundaria': 'Común Secundaria',
            'visor_cargo_comun_servicios_complementarios': 'Común Servicios Complementarios',
            'visor_cargo_comun_snu': 'Común SNU',
            'visor_cargo_especial_tln': 'Especial TLN',
            'visor_cargos_adulto_fp': 'Adultos Formación Profesional',
        }
        nvista = opciones_descriptivas.get(tvista, 'Adultos Formación Profesional')

        # Asignar un valor descriptivo a la opción de relevamiento seleccionado
        opciones_relevamiento={
            'ra_carga2019':'Relevamiento 2019',
            'ra_carga2020':'Relevamiento 2020',
            'ra_carga2021':'Relevamiento 2021',
            'ra_carga2022':'Relevamiento 2022',
            'ra_carga2023':'Relevamiento 2023',
        }
        nrelevamiento=opciones_relevamiento.get(relevamiento,'Relevamiento 2022')
        
         # Conectarse a la base de datos
        connection = conectar_bd(request)
        if not connection:
            return render(request, 'error_conexion.html')

        cursor = connection.cursor()

        # Código para ejecutar la consulta SQL y obtener los datos
        query = f"""
            SELECT
                cargos,
                SUM(CAST(total AS INT)) AS total,
                SUM(CAST(titular AS INT)) AS titular,
                SUM(CAST(interinos AS INT)) AS interinos,
                SUM(CAST(sin_cubrir AS INT)) AS sin_cubrir                
            FROM funcion.{tvista}('{relevamiento}')
            LEFT JOIN (
                    SELECT * FROM dblink (
                        'dbname=Padron user=visualizador password=Estadisticas24 host=sigechaco.com.ar port=5432',
                        'SELECT distinct cueanexo, nom_est, nro_est, anio_creac_establec, fecha_creac_establec, region, udt, cui, cua, cuof, sector, ambito, ref_loc, calle, numero, localidad, departamento, cod_postal, categoria, estado_est, estado_loc, telefono_cod_area, telefono_nro, per_funcionamiento, email_loc FROM padron'
                    ) AS padron (
                        cueanexo varchar, nom_est varchar, nro_est varchar, anio_creac_establec varchar,
                        fecha_creac_establec varchar, region varchar, udt varchar, cui varchar, cua varchar, cuof varchar, sector varchar, ambito varchar, ref_loc varchar,
                        calle varchar, numero varchar, localidad varchar, departamento varchar, cod_postal varchar, categoria varchar, estado_est varchar, estado_loc varchar,
                        telefono_cod_area varchar, telefono_nro varchar, per_funcionamiento varchar, email_loc varchar
                    )
                ) AS p using (cueanexo)             
            WHERE 1=1           
        """

        parameters = []
        if cueanexo:
            query += "AND p.cueanexo = %s"
            parameters.append(cueanexo)
        if ambito:
            query += " AND p.ambito = %s"
            parameters.append(ambito)
        if sector:
            query += " AND p.sector = %s"
            parameters.append(sector)
        if region:
            query += " AND p.region = %s"
            parameters.append(region)
        if departamento:
            query += " AND p.departamento = %s"
            parameters.append(departamento)
        if localidad:
            query += "AND p.localidad = %s"
            parameters.append(localidad)

        query += " GROUP BY cargos HAVING SUM(CAST(total AS INT)) <> 0"

        cursor.execute(query, parameters)
        rows = cursor.fetchall()

        # Convertir los resultados de la consulta a un DataFrame de Pandas
        df = pd.DataFrame(rows, columns=['cargos', 'total', 'titular', 'interinos', 'sin_cubrir'])
        df=df[['cargos','titular','interinos','sin_cubrir']]
        df.set_index('cargos', inplace=True)

        # Cerrar la conexión a la base de datos
        connection.close()

        if df.empty:
            return render(request, 'consulta_vacia.html')

        # Crear el gráfico utilizando Matplotlib
        plt.figure(figsize=(10, 6))
        df.plot(kind='bar', stacked=True)
        plt.title('Gráfico de cargos')
        plt.xlabel('Cargos')
        plt.ylabel('Cantidad')

        # Guardar el gráfico como una imagen
        img_path = '/media/grafico_cargos.png'  # Ruta donde se guardará la imagen
        plt.savefig(img_path)
        plt.close()

        # Devolver la ruta de la imagen como contexto a la plantilla
        return render(request, 'reportes/cargos_graf.html', {'img_path': img_path})