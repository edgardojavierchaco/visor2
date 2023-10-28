import psycopg2
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

# Función para conectar a la base de datos
def conectar_bd(request):
    try:
        connection = psycopg2.connect(
            host='relevamientoanual.com.ar',
            user='visualizador',
            password='Estadisticas23',
            database='visualizador',       )
        return connection
    except psycopg2.Error as e:
        # Manejar el error de conexión
        return None

# Vista para mostrar el formulario de filtrado de matricula aborigen
def filtrado_aborigen(request):
    return render(request, 'reportes/filter_aborigen.html')

# Vista para mostrar el formulario de filtrado de matricula común y especial
def filtrado_comesp(request):
    return render(request, 'reportes/filter_comesp.html')

# Vista para mostrar el formulario de filtrado de matricula SNU
def filtrado_snu(request):
    return render(request, 'reportes/filter_snu.html')

#####################################################################
#               PARA REPORTE DE MATRICULA AGORIGEN                  #
#####################################################################

# Vista para procesar los datos del formulario de filtrado de matricula aborigen
@csrf_exempt
def filter_data_aborigen(request):
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
            'visor_matric_aborigen_adulto_primaria',
            'visor_matric_aborigen_adulto_secundaria',
            'visor_matric_aborigen_comun_inicial',
            'visor_matric_aborigen_comun_primaria',
            'visor_matric_aborigen_comun_secundaria',
            'visor_matric_aborigen_comun_snu',
            'visor_matric_aborigen_educacion_especial'            
        ]

        # Obtener el valor seleccionado para tvista
        tvistaaborigen = request.POST.get('Vista')
        print(relevamiento, tvistaaborigen, sector)

        # Validar que tvista esté en la lista de opciones válidas
        if tvistaaborigen not in opciones_validas:
            return render(request, 'error.html', {'mensaje': 'Opción de vista no válida'})

        # Asignar un valor descriptivo a la opción de tvista seleccionada
        opciones_descriptivas = {
            'visor_matric_aborigen_adulto_primaria': 'Aborigen Adulto Primaria',
            'visor_matric_aborigen_adulto_secundaria': 'Aborigen Adulto Secundaria',
            'visor_matric_aborigen_comun_inicial': 'Aborigen Común Inicial',
            'visor_matric_aborigen_comun_primaria': 'Aborigen Común Primaria',
            'visor_matric_aborigen_comun_secundaria': 'Aborigen Común Secundaria',
            'visor_matric_aborigen_comun_snu': 'Aborigen Común SNU',
            'visor_matric_aborigen_educacion_especial': 'Aborigen Educación Especial',            
        }
        nvistaaborigen = opciones_descriptivas.get(tvistaaborigen, 'Aborigen Educación Especial')

        # Asignar un valor descriptivo a la opción de relevamiento seleccionado
        opciones_relevamiento={      
            'ra_carga2022':'Relevamiento 2022',            
        }
        nrelevamiento=opciones_relevamiento.get(relevamiento,'Relevamiento 2022')

        # Conectarse a la base de datos
        connection = conectar_bd(request)
        if not connection:
            return render(request, 'error_conexion.html')

        cursor = connection.cursor()

        query = f"""
            SELECT                
                SUM(CAST(total AS INT)) AS total,
                SUM(CAST(tot_var AS INT)) AS tot_var                               
            FROM funcion.{tvistaaborigen}('{relevamiento}')  
            LEFT JOIN (
                    SELECT * FROM dblink (
                        'dbname=Padron user=visualizador password=Estadisticas23 host=relevamientoanual.com.ar port=5432',
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
        

        cursor.execute(query, parameters)
        rows = cursor.fetchall()

        # verificar si hay datos en rows 
        datos_encontrados = len(rows)>0

        # Convertir los resultados de la consulta a formato JSON
        dataaborigen = []
        for row in rows:
            dataaborigen.append({
                
                'total': int(row[0]),
                'tot_var': int(row[1])
            })

        # Cerrar la conexión a la base de datos
        connection.close()
        print(dataaborigen)

        # Si no hay datos para la consulta
        if not datos_encontrados:
            return render(request, 'consulta_vacia.html')
        
        # Devolver los datos como contexto a la plantilla 'cargos.html'
        return render(request, 'reportes/aborigenes.html', {'dataaborigen': dataaborigen, 'nvistaaborigen': nvistaaborigen, 'nrelevamiento':nrelevamiento})
    
#####################################################################
#           PARA REPORTE DE MATRICULA COMÚN Y ESPECIAL              #
#####################################################################

# Vista para procesar los datos del formulario de filtrado de matricula común y especial
@csrf_exempt
def filter_data_comesp(request):
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
            'visor_matric_adulto_fp',
            'visor_matric_adulto_primaria',
            'visor_matric_adulto_secundaria',
            'visor_matric_comun_inicial',
            'visor_matric_comun_primaria',
            'visor_matric_comun_secundaria',            
            'visor_matric_especial_ed_temprana',
            'visor_matric_especial_inicial',
            'visor_matric_especial_primaria',           
        ]

        # Obtener el valor seleccionado para tvista
        tvistacomesp = request.POST.get('Vista')
        print(relevamiento, tvistacomesp, sector)

        # Validar que tvista esté en la lista de opciones válidas
        if tvistacomesp not in opciones_validas:
            return render(request, 'error.html', {'mensaje': 'Opción de vista no válida'})

        # Asignar un valor descriptivo a la opción de tvista seleccionada
        opciones_descriptivas = {
            'visor_matric_adulto_fp': 'Adulto Formación Profesional',
            'visor_matric_adulto_primaria': 'Adulto Primaria',
            'visor_matric_adulto_secundaria': 'Adulto Secundaria',
            'visor_matric_comun_inicial': 'Común Inicial',
            'visor_matric_comun_primaria': 'Común Primaria',
            'visor_matric_comun_secundaria': 'Común Secundaria',
            'visor_matric_especial_ed_temprana': 'Especial Temprana',
            'visor_matric_especial_inicial': 'Especial Inicial',
            'visor_matric_especial_primaria': 'Especial Primaria',
        }
        nvistacomesp = opciones_descriptivas.get(tvistacomesp, 'Especial Primaria')

        # Asignar un valor descriptivo a la opción de relevamiento seleccionado
        opciones_relevamiento={
            'ra_carga2011':'Relevamiento 2011',
            'ra_carga2012':'Relevamiento 2012',
            'ra_carga2013':'Relevamiento 2013',
            'ra_carga2014':'Relevamiento 2014',
            'ra_carga2015':'Relevamiento 2015',
            'ra_carga2016':'Relevamiento 2016',
            'ra_carga2017':'Relevamiento 2017',
            'ra_carga2018':'Relevamiento 2018',
            'ra_carga2019':'Relevamiento 2019',
            'ra_carga2020':'Relevamiento 2020',
            'ra_carga2021':'Relevamiento 2021',
            'ra_carga2022':'Relevamiento 2022',
            'ra_carga2023':'Relevamiento 2023',
        }
        nrelevamiento=opciones_relevamiento.get(relevamiento,'Relevamiento 2022')

        # Conectarse a la base de datos
        connection = conectar_bd(relevamiento)
        if not connection:
            return render(request, 'error_conexion.html')

        cursor = connection.cursor()

        query1 = f"""
            SELECT DISTINCT
                turno,
                grado,
                SUM(CAST(total AS INT)) AS total,
                SUM(CAST(total_var AS INT)) AS tot_var                               
            FROM funcion.{tvistacomesp}('{relevamiento}')  
            LEFT JOIN (
                    SELECT * FROM dblink (
                        'dbname=Padron user=visualizador password=Estadisticas23 host=relevamientoanual.com.ar port=5432',
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
            query1 += "AND cueanexo = %s"
            parameters.append(cueanexo)
        if ambito:
            query1 += " AND ambito = %s"
            parameters.append(ambito)
        if sector:
            query1 += " AND sector = %s"
            parameters.append(sector)
        if region:
            query1 += " AND region = %s"
            parameters.append(region)
        if departamento:
            query1 += " AND departamento = %s"
            parameters.append(departamento)
        if localidad:
            query1 += "AND localidad = %s"
            parameters.append(localidad)

        query1 += " GROUP BY grado, turno HAVING SUM(CAST(total AS INT)) <> 0"

        cursor.execute(query1, parameters)
        rows = cursor.fetchall()

        # verifica si hay datos para la consulta
        datos_encontrados=len(rows)>0

        # Convertir los resultados de la consulta a formato JSON
        datacomesp = []
        for row in rows:
            datacomesp.append({
                'turno': row[0],
                'grado': row[1],
                'total': int(row[2]),
                'tot_var': int(row[3])
            })

        # Cerrar la conexión a la base de datos
        connection.close()
        print(datacomesp)
        print(nvistacomesp)

        if not datos_encontrados:
            return render(request, 'consulta_vacia.html')
        
        # Devolver los datos como contexto a la plantilla 'cargos.html'
        return render(request, 'reportes/comunespecial.html', {'datacomesp': datacomesp, 'nvistacomesp': nvistacomesp, 'nrelevamiento':nrelevamiento})

#####################################################################
#                     PARA REPORTE DE MATRICULA SNU                 #
#####################################################################

# Vista para procesar los datos del formulario de filtrado de matricula común y especial
@csrf_exempt
def filter_data_snu(request):
    if request.method == 'POST':
        cueanexo = request.POST.get('Cueanexo')
        ambito = request.POST.get('Ambito')
        sector = request.POST.get('Sector')
        region = request.POST.get('Region')
        departamento = request.POST.get('Departamento')
        localidad = request.POST.get('Localidad')
        relevamiento = request.POST.get('Relevamiento')

        # Validar que tvista esté en la lista de opciones válidas
        opciones_validas_snu = [            
            'visor_matric_comun_snu'            
        ]

        # Obtener el valor seleccionado para tvista
        tvistasnu = request.POST.get('Vista')
        print(relevamiento, tvistasnu, sector)

        # Validar que tvista esté en la lista de opciones válidas
        if tvistasnu not in opciones_validas_snu:
            return render(request, 'error.html', {'mensaje': 'Opción de vista no válida'})

        # Asignar un valor descriptivo a la opción de tvista seleccionada
        opciones_descriptivas_snu = {            
            'visor_matric_comun_snu': 'Común SNU',
        }
        nvistasnu = opciones_descriptivas_snu.get(tvistasnu, 'Común SNU')

        # Asignar un valor descriptivo a la opción de relevamiento seleccionado
        opciones_relevamiento={            
            'ra_carga2020':'Relevamiento 2020',
            'ra_carga2021':'Relevamiento 2021',
            'ra_carga2022':'Relevamiento 2022',
        }
        nrelevamiento=opciones_relevamiento.get(relevamiento,'Relevamiento 2022')

        # Conectarse a la base de datos
        connection = conectar_bd(request) 
        if not connection:
            return render(request, 'error_conexion.html')

        cursor = connection.cursor()

        query2 = f"""
            SELECT
                plan_est_titulo,
                SUM(CAST(total AS INT)) AS total,
                SUM(CAST(total_ingresante AS INT)) AS ingresantes,
                SUM(CAST(total_pasantia_practicas AS INT)) AS pasantia,
                SUM(CAST(total_residencia AS INT)) AS residencia
            FROM funcion.{tvistasnu}('{relevamiento}')         
            LEFT JOIN (
                    SELECT * FROM dblink (
                        'dbname=Padron user=visualizador password=Estadisticas23 host=relevamientoanual.com.ar port=5432',
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
            query2 += "AND p.cueanexo = %s"
            parameters.append(cueanexo)
        if ambito:
            query2 += " AND p.ambito = %s"
            parameters.append(ambito)
        if sector:
            query2 += " AND p.sector = %s"
            parameters.append(sector)
        if region:
            query2 += " AND p.region = %s"
            parameters.append(region)
        if departamento:
            query2 += " AND p.departamento = %s"
            parameters.append(departamento)
        if localidad:
            query2 += "AND p.localidad = %s"
            parameters.append(localidad)

        query2 += " GROUP BY plan_est_titulo HAVING SUM(CAST(total AS INT)) <> 0"

        cursor.execute(query2, parameters)
        rows = cursor.fetchall()

        # verificar si hay datos para la consulta
        datos_encontrados=len(rows)>0

        # Convertir los resultados de la consulta a formato JSON
        datasnu = []
        for row in rows:
            datasnu.append({
                'titulo': row[0],
                'total': row[1],
                'ingresantes': int(row[2]),
                'pasantia': int(row[3]),
                'residencia': int(row[4])
            })

        # Cerrar la conexión a la base de datos
        connection.close()
        print(datasnu)
        print(nvistasnu)

        if not datos_encontrados:
            return render(request, 'consulta_vacia.html')
        
        # Devolver los datos como contexto a la plantilla 'cargos.html'
        return render(request, 'reportes/snu.html', {'datasnu': datasnu, 'nvistasnu': nvistasnu, 'nrelevamiento':nrelevamiento})   
     