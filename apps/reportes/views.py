import psycopg2
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

# Función para conectar a la base de datos
def conectar_bd(request):
    try:
        connection = psycopg2.connect(
            host='relevamientoanual.com.ar',
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

#####################################################################
#                       PARA REPORTE DE CARGOS                      #
#####################################################################

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
                        'dbname=Padron user=visualizador password=Estadisticas24 host=relevamientoanual.com.ar port=5432',
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

        # verificar si la consulta arroja datos
        datos_encontrados=len(rows)>0

        # Convertir los resultados de la consulta a formato JSON
        data = []
        for row in rows:
            data.append({
                'cargos': row[0],
                'total': int(row[1]),
                'titular': int(row[2]),
                'interinos': int(row[3]),
                'sin_cubrir': int(row[4])
            })

        # Cerrar la conexión a la base de datos
        connection.close()
        print(data)

        if not datos_encontrados:
            return render(request, 'consulta_vacia.html')
        
        # Devolver los datos como contexto a la plantilla 'cargos.html'
        return render(request, 'publico/repocargos.html', {'data': data, 'nvista': nvista,'nrelevamiento':nrelevamiento})


#####################################################################
#                PARA REPORTE DE DOCENTES EN ACTIVIDAD               #
#####################################################################

# Vista asíncrona para procesar los datos del formulario de filtrado de docentes
@csrf_exempt
def filter_data_docentes(request):
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
            'visor_docente_actividad_adulto_fp',
            'visor_docente_actividad_adulto_primaria',
            'visor_docente_actividad_adulto_secundaria',
            'visor_docente_actividad_comun_inicial',
            'visor_docente_actividad_comun_primaria',
            'visor_docente_actividad_comun_secundaria',
            'visor_docente_actividad_comun_servicios_complementarios',
            'visor_docente_actividad_comun_snu',
            'visor_docente_actividad_educacion_especial',
        ]

        # Obtener el valor seleccionado para tvista
        tvista = request.POST.get('Vista')

        print(relevamiento, tvista, sector)
        # Validar que tvista esté en la lista de opciones válidas
        if tvista not in opciones_validas:
            return render(request, 'error.html', {'mensaje': 'Opción de vista no válida'})

        # Asignar un valor descriptivo a la opción de tvista seleccionada
        opciones_descriptivas = {
            'visor_docente_actividad_adulto_fp': 'Adulto Formación Profesional',
            'visor_docente_actividad_adulto_primaria': 'Adulto Primaria',
            'visor_docente_actividad_adulto_secundaria': 'Adulto Secundaria',
            'visor_docente_actividad_comun_inicial': 'Común Inicial',
            'visor_docente_actividad_comun_primaria': 'Común Primaria',
            'visor_docente_actividad_comun_secundaria': 'Común Secundaria',
            'visor_docente_actividad_comun_servicios_complementarios': 'Común Servicios Complementarios',
            'visor_docente_actividad_comun_snu': 'Común SNU',
            'visor_docente_actividad_educacion_especial': 'Educación Especial',
        }
        nvista = opciones_descriptivas.get(tvista, 'Educación Especial')

        # Asignar un valor descriptivo a la opción de relevamiento seleccionado
        opciones_relevamiento={
            'ra_carga2020':'Relevamiento 2020',
            'ra_carga2021':'Relevamiento 2021',
            'ra_carga2022':'Relevamiento 2022',
            'ra_carga2023':'Relevamiento 2023',
        }
        nrelevamiento=opciones_relevamiento.get(relevamiento,'Relevamiento 2022')

        try:
            # Conectarse a la base de datos
            connection = conectar_bd(relevamiento)
            if not connection:
                return render(request, 'error_conexion.html')

            resultados = connection.cursor()

            query = f"""
                SELECT
                    docentes,
                    SUM(CAST(total AS INT)) AS total,
                    SUM(CAST(varones AS INT)) AS varones                
                FROM funcion.{tvista}('{relevamiento}')   
                LEFT JOIN (
                    SELECT * FROM dblink (
                        'dbname=Padron user=visualizador password=Estadisticas24 host=relevamientoanual.com.ar port=5432',
                        'SELECT distinct cueanexo, nom_est, nro_est, anio_creac_establec, fecha_creac_establec, region, udt, cui, cua, cuof, sector, ambito, ref_loc, calle, numero, localidad, departamento, cod_postal, categoria, estado_est, estado_loc, telefono_cod_area, telefono_nro, per_funcionamiento, email_loc FROM padron'
                    ) AS padron (
                        cueanexo varchar, nom_est varchar, nro_est varchar, anio_creac_establec varchar,
                        fecha_creac_establec varchar, region varchar, udt varchar, cui varchar, cua varchar, cuof varchar, sector varchar, ambito varchar, ref_loc varchar,
                        calle varchar, numero varchar, localidad varchar, departamento varchar, cod_postal varchar, categoria varchar, estado_est varchar, estado_loc varchar,
                        telefono_cod_area varchar, telefono_nro varchar, per_funcionamiento varchar, email_loc varchar
                    )
                ) AS p using (cueanexo)         
                WHERE 1=1 AND docentes = 'Total docentes en actividad'         
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
                query += " AND p.localidad = %s"
                parameters.append(localidad)

            query += " GROUP BY docentes HAVING SUM(CAST(total AS INT)) <> 0"

            resultados.execute(query, parameters)
            rows1 = resultados.fetchall()

            datos_encontrados1=len(rows1)>0

            # Convertir los resultados de la consulta a formato JSON
            data1 = []
            for row in rows1:
                data1.append({
                    'docentes': row[0],
                    'total': int(row[1]),
                    'varones': int(row[2])
                })

            # Cerrar la conexión a la base de datos
            connection.close()
            print(data1)

            if not datos_encontrados1:
                return render(request, 'consulta_vacia.html')
        
            # Devolver los datos como contexto a la plantilla 'docentes.html'
            return render(request, 'publico/repodocentes.html', {'data1': data1, 'nvista': nvista, 'nrelevamiento':nrelevamiento})
        except psycopg2.Error as e:
            # Manejar el error de conexión
            return render(request, 'error_conexion.html')


#####################################################################
#                       PARA REPORTE DE HORAS                       #
#####################################################################

# Vista asíncrona para procesar los datos del formulario de filtrado de horas
@csrf_exempt
def filter_data_horas(request):
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
            'visor_horas_adulto_fp',        
            'visor_horas_adulto_primaria',
            'visor_horas_adulto_secundaria',            
            'visor_horas_comun_inicial',
            'visor_horas_comun_primaria',
            'visor_horas_comun_secundaria',
            'visor_horas_comun_servicios_complementarios',
            'visor_horas_comun_snu',
            'visor_horas_especial_temprana',
        ]

        # Obtener el valor seleccionado para tvista
        tvista = request.POST.get('Vista')

        print(relevamiento, tvista, sector, localidad)
        # Validar que tvista esté en la lista de opciones válidas
        if tvista not in opciones_validas:
            return render(request, 'error.html', {'mensaje': 'Opción de vista no válida'})

        # Asignar un valor descriptivo a la opción de tvista seleccionada
        opciones_descriptivas = {
            'visor_horas_adulto_fp': 'Adulto Formación Profesional',
            'visor_horas_adulto_primaria': 'Adulto Primaria',
            'visor_horas_adulto_secundaria': 'Adulto Secundaria',            
            'visor_horas_comun_inicial': 'Común Inicial',
            'visor_horas_comun_primaria': 'Común Primaria',
            'visor_horas_comun_secundaria': 'Común Secundaria',
            'visor_horas_comun_servicios_complementarios': 'Común Servicios Complementarios',
            'visor_horas_comun_snu': 'Común SNU',
            'visor_horas_especial_temprana': 'Educación Especial',
        }
        nvista = opciones_descriptivas.get(tvista, 'Educación Especial')

        # Asignar un valor descriptivo a la opción de relevamiento seleccionado
        opciones_relevamiento={
            'ra_carga2019':'Relevamiento 2019',
            'ra_carga2020':'Relevamiento 2020',
            'ra_carga2021':'Relevamiento 2021',
            'ra_carga2022':'Relevamiento 2022',
            'ra_carga2023':'Relevamiento 2023',
        }
        nrelevamiento=opciones_relevamiento.get(relevamiento,'Relevamiento 2022')

        try:
            # Conectarse a la base de datos
            connection = conectar_bd(relevamiento)
            if not connection:
                return render(request, 'error_conexion.html',{'mensaje': 'Error de conexión a la base de datos'})

            resultados1 = connection.cursor()

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
                        'dbname=Padron user=visualizador password=Estadisticas24 host=relevamientoanual.com.ar port=5432',
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
                query += " AND p.localidad = %s"
                parameters.append(localidad)

            query += " GROUP BY cargos HAVING SUM(CAST(total AS INT)) <> 0"

            resultados1.execute(query, parameters)
            rows2 = resultados1.fetchall()

            datos_encontrados2=len(rows2)>0

            if not datos_encontrados2:
                return render(request, 'consulta_vacia.html')
            else:

                # Convertir los resultados de la consulta a formato JSON
                data2 = []
                for row in rows2:
                    data2.append({
                        'horas': row[0],
                        'total': int(row[1]),
                        'titular': int(row[2]),
                        'interinos': int(row[3]),
                        'sin_cubrir': int(row[4])
                    })

                # Cerrar la conexión a la base de datos
                connection.close()
                print(data2)               
            
                # Devolver los datos como contexto a la plantilla 'docentes.html'
                return render(request, 'publico/repohoras.html', {'data2': data2, 'nvista': nvista, 'nrelevamiento':nrelevamiento})
        except psycopg2.Error as e:
            # Manejar el error de conexión
            return render(request, 'error_conexion.html',{'mensaje': 'Error en la consulta: ' + str(e)})

