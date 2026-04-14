import psycopg2
import os
import dotenv
import json
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

# Vista para obtener la jerarquía geográfica (región -> departamento -> localidad)
def get_jerarquia_geografica(request):
    """
    Devuelve la jerarquía geográfica en formato JSON.
    Incluye mapeos de región -> departamento -> localidad y mapeos inversos.
    """
    # Cargar datos desde archivo JSON (podrías también generarlos dinámicamente desde la BD)
    jerarquia_data = {
        "region_depto_localidad": {
            "REGION 1": {"GENERAL GUEMES": ["MISIÓN NUEVA POMPEYA"]},
            "SUBSEDE 1 A": {"GENERAL GUEMES": ["FUERTE ESPERANZA", "COMANDANCIA FRIAS"]},
            "SUBSEDE 1 B": {"GENERAL GUEMES": ["EL SAUZALITO"]},
            "REGION 2": {"GENERAL GUEMES": ["JUAN JOSE CASTELLI", "EL ESPINILLO", "MIRAFLORES", "VILLA RIO BERMEJITO"]},
            "SUBSEDE 2": {"MAIPU": ["TRES ISLETAS"]},
            "REGION 3": {
                "INDEPENDENCIA": ["NAPENAY", "AVIA TERAI"],
                "ALMIRANTE BROWN": ["CONCEPCION DEL BERMEJO", "RIO MUERTO", "LOS FRENTONES", "PAMPA DEL INFIER."]
            },
            "SUBSEDE 3": {"ALMIRANTE BROWN": ["TACO POZO"]},
            "REGION 4-A": {"COMANDANTE FERNANDEZ": ["PRESIDENCIA ROQUE SAENZ PEÑA"]},
            "REGION 4-B": {
                "QUITILIPI": ["QUITILIPI"],
                "25 DE MAYO": ["MACHAGAI"],
                "PCIA,DE LA PLAZA": ["PCIA.DE LA PLAZA"],
                "PCIA,DE LA PLAZA": ["PCIA.DE LA PLAZA"]
            },
            "REGION 5": {"LIBERTADOR GENERAL SAN MARTIN": ["GRAL. JOSE DE SAN MARTIN", "LA EDUVIGIS", "SELVA RIO DE ORO", "PAMPA ALMIRON"]},
            "SUBSEDE 5": {"LIBERTADOR GENERAL SAN MARTIN": ["PAMPA DEL INDIO", "LAGUNA LIMPIA", "CIERVO PETISO", "PRESIDENCIA ROCA"]},
            "REGION 6": {"BERMEJO": ["LA LEONESA", "PUERTO EVA PERON", "PUERTO BERMEJO", "LAS PALMAS", "GENERAL VEDIA", "ISLA DEL CERRITO"]},
            "REGION 7": {
                "GENERAL DONOVAN": ["LA ESCONDIDA", "LA VERDE", "LAPACHITO", "MAKALLE"],
                "SARGENTO CABRAL": ["COLONIA ELISA", "CAPITAN SOLARI", "COLONIAS UNIDAS", "LAS GARCITAS"],
                "LIBERTAD": ["LAGUNA BLANCA"]
            },
            "REGION 8-A": {
                "9 DE JULIO": ["LAS BREÑAS"],
                "GRAL BELGRANO": ["CORZUELA"],
                "INDEPENDENCIA": ["CAMPO LARGO"],
                "CHACABUCO": ["CHARATA"]
            },
            "REGION 8-B": {
                "12 DE OCTUBRE": ["GENERAL PINEDO", "GENERAL CAPDEVILA", "GANCEDO"],
                "2 DE ABRIL": ["HERMOSO CAMPO"]
            },
            "REGION 9": {
                "MAYOR LUIS J.FONTANA": ["VILLA ANGELA", "CORONEL DU GRATY", "ENRIQUE URIEN"],
                "FRAY JUSTO SANTA M. DE ORO": ["CHOROTIS", "SANTA SYLVINA"],
                "SAN LORENZO": ["SAMUHU", "VILLA BERTHET"],
                "O HIGGINS": ["SAN BERNARDO", "LA CLOTILDE", "LA TIGRA"]
            },
            "REGION 10-A": {"SAN FERNANDO": ["RESISTENCIA"]},
            "REGION 10-B": {"SAN FERNANDO": ["COLONIA BARANDA", "RESISTENCIA"]},
            "REGION 10-C": {
                "SAN FERNANDO": ["BARRANQUERAS", "PUERTO VILELAS", "FONTANA", "BASAIL"],
                "1§ DE MAYO": ["COLONIA BENITEZ", "MARGARITA BELEN"],
                "LIBERTAD": ["COLONIA POPULAR", "PUERTO TIROL"],
                "TAPENAGA": ["COTE LAI", "CHARADAI"]
            }
        }
    }
    
    return JsonResponse(jerarquia_data)

# Función para conectar a la base de datos
def conectar_bd(request):
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
        return None

# Vista para mostrar el formulario de filtrado de cargos
def filtrado_cargos(request):
    # Ahora carga el dashboard en vez de la ventanita modal
    return render(request, 'reportes/dashboard_reportes_cargos.html')

# Vista para mostrar el formulario de filtrado de docentes
def filtrado_docentes(request):
    # Ahora carga el dashboard en vez de la ventanita modal
    return render(request, 'reportes/dashboard_reportes_docentes.html')

# Vista para mostrar el formulario de filtrado de docentes pasiva
def filtrado_docentes_pasiva(request):
    # Ahora carga el dashboard en vez de la ventanita modal
    return render(request, 'reportes/dashboard_reportes_docentes_pasiva.html')

# Vista para mostrar el formulario de filtrado de horas
def filtrado_horas(request):
    # Ahora carga el dashboard en vez de la ventanita modal
    return render(request, 'reportes/dashboard_reportes_horas.html')

#####################################################################
#                       PARA REPORTE DE CARGOS                      #
#####################################################################

# Vista para procesar los datos del formulario de filtrado de cargos
@csrf_exempt
def filter_data_cargos(request):
    """
    Vista para procesar los datos del formulario de filtrado de cargos.

    Args:
        request: El objeto de solicitud de Django.

    Returns:
        HttpResponse: Renderiza la plantilla con los resultados del filtrado 
                      o una plantilla de error si no se encuentra información.
    """
    
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
            'ra_carga2024':'Relevamiento 2024',
            'ra_carga2025':'Relevamiento 2025',
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
                        'dbname=Padron user=visualizador password=Estadisticas24 host=visoreducativochaco.com.ar port=5432',
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
        return render(request, 'reportes/cargos.html', {'data': data, 'nvista': nvista,'nrelevamiento':nrelevamiento})


#####################################################################
#                PARA REPORTE DE DOCENTES EN ACTIVIDAD               #
#####################################################################

# Vista asíncrona para procesar los datos del formulario de filtrado de docentes
@csrf_exempt
def filter_data_docentes(request):
    """
    Vista asíncrona para procesar los datos del formulario de filtrado de docentes.

    Args:
        request: El objeto de solicitud de Django.

    Returns:
        HttpResponse: Renderiza la plantilla con los resultados del filtrado 
                      o una plantilla de error si no se encuentra información.
    """
    
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
            'ra_carga2024':'Relevamiento 2024',
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
                        'dbname=Padron user=visualizador password=Estadisticas24 host=visoreducativochaco.com.ar port=5432',
                        'SELECT distinct (cueanexo), nom_est, nro_est, anio_creac_establec, fecha_creac_establec, region, udt, cui, cua, cuof, sector, ambito, ref_loc, calle, numero, localidad, departamento, cod_postal, categoria, estado_est, estado_loc, telefono_cod_area, telefono_nro, per_funcionamiento, email_loc FROM padron'
                    ) AS padron (
                        cueanexo varchar, nom_est varchar, nro_est varchar, anio_creac_establec varchar,
                        fecha_creac_establec varchar, region varchar, udt varchar, cui varchar, cua varchar, cuof varchar, sector varchar, ambito varchar, ref_loc varchar,
                        calle varchar, numero varchar, localidad varchar, departamento varchar, cod_postal varchar, categoria varchar, estado_est varchar, estado_loc varchar,
                        telefono_cod_area varchar, telefono_nro varchar, per_funcionamiento varchar, email_loc varchar
                    )
                ) AS p using (cueanexo)         
                WHERE 1=1 AND docentes !='Total docentes en actividad' AND docentes!='Docentes en tareas pasivas'        
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
            return render(request, 'reportes/docentes.html', {'data1': data1, 'nvista': nvista, 'nrelevamiento':nrelevamiento})
        except psycopg2.Error as e:
            # Manejar el error de conexión
            return render(request, 'error_conexion.html')


#####################################################################
#                       PARA REPORTE DE HORAS                       #
#####################################################################

# Vista asíncrona para procesar los datos del formulario de filtrado de horas
@csrf_exempt
def filter_data_horas(request):
    """
    Procesa los datos del formulario de filtrado de horas.

    Args:
        request: Objeto HttpRequest.

    Returns:
        Renderiza la plantilla 'reportes/horas.html' con los datos filtrados
        o una plantilla de error si hay problemas con la conexión o la consulta.
    """
    
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
            'visor_horas_comun_artistica',
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
            'visor_horas_comun_artistica': 'Común Artística',
            'visor_horas_comun_artistica': 'Común Artística',
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
            'ra_carga2024':'Relevamiento 2024',
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
                        'dbname=Padron user=visualizador password=Estadisticas24 host=visoreducativochaco.com.ar port=5432',
                        'SELECT distinct cueanexo, nom_est, nro_est,  region, sector, ambito, localidad, departamento FROM padron'
                    ) AS padron (
                        cueanexo varchar, nom_est varchar, nro_est varchar, 
                         region varchar, sector varchar, ambito varchar, 
                        localidad varchar, departamento varchar                       
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
                return render(request, 'reportes/horas.html', {'data2': data2, 'nvista': nvista, 'nrelevamiento':nrelevamiento})
        except psycopg2.Error as e:
            # Manejar el error de conexión
            return render(request, 'error_conexion.html',{'mensaje': 'Error en la consulta: ' + str(e)})



#####################################################################
#           PARA REPORTE DE DOCENTES EN TAREAS PASIVAS              #
#####################################################################

# Vista asíncrona para procesar los datos del formulario de filtrado de docentes
@csrf_exempt
def filter_data_docentes_pasiva(request):
    """
    Vista asíncrona para procesar los datos del formulario de filtrado de docentes.

    Args:
        request: El objeto de solicitud de Django.

    Returns:
        HttpResponse: Renderiza la plantilla con los resultados del filtrado 
                      o una plantilla de error si no se encuentra información.
    """
    
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
            'ra_carga2024':'Relevamiento 2024',
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
                        'dbname=Padron user=visualizador password=Estadisticas24 host=visoreducativochaco.com.ar port=5432',
                        'SELECT distinct (cueanexo), nom_est, nro_est, anio_creac_establec, fecha_creac_establec, region, udt, cui, cua, cuof, sector, ambito, ref_loc, calle, numero, localidad, departamento, cod_postal, categoria, estado_est, estado_loc, telefono_cod_area, telefono_nro, per_funcionamiento, email_loc FROM padron'
                    ) AS padron (
                        cueanexo varchar, nom_est varchar, nro_est varchar, anio_creac_establec varchar,
                        fecha_creac_establec varchar, region varchar, udt varchar, cui varchar, cua varchar, cuof varchar, sector varchar, ambito varchar, ref_loc varchar,
                        calle varchar, numero varchar, localidad varchar, departamento varchar, cod_postal varchar, categoria varchar, estado_est varchar, estado_loc varchar,
                        telefono_cod_area varchar, telefono_nro varchar, per_funcionamiento varchar, email_loc varchar
                    )
                ) AS p using (cueanexo)         
                WHERE 1=1 AND docentes ='Docentes en tareas pasivas'        
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
            return render(request, 'reportes/docentes_pasiva.html', {'data1': data1, 'nvista': nvista, 'nrelevamiento':nrelevamiento})
        except psycopg2.Error as e:
            # Manejar el error de conexión
            return render(request, 'error_conexion.html')


#####################################################################
#         FUNCIONES QUE YA EXISTÍAN EN EL PROYECTO ORIGINAL        #
#####################################################################

def docentes_cargos_dashboard(request):
    return render(request, 'reportes/docentes_cargos_dashboard.html')

def api_reportes_data(request):
    return JsonResponse({'data': []})

#####################################################################
#              ENDPOINTS AJAX PARA LOS NUEVOS DASHBOARDS            #
#  Estas funciones son llamadas por JavaScript y devuelven JSON     #
#####################################################################

@csrf_exempt
def cargos_ajax(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    cueanexo     = request.POST.get('Cueanexo', '').strip()
    ambito       = request.POST.get('Ambito', '').strip()
    sector       = request.POST.get('Sector', '').strip()
    region       = request.POST.get('Region', '').strip()
    departamento = request.POST.get('Departamento', '').strip()
    localidad    = request.POST.get('Localidad', '').strip()
    relevamiento = request.POST.get('Relevamiento', '').strip()
    tvista       = request.POST.get('Vista', '').strip()

    opciones_validas = [
        'visor_cargo_adulto_primaria', 'visor_cargo_adulto_secundaria',
        'visor_cargo_comun_artistica', 'visor_cargo_comun_inicial',
        'visor_cargo_comun_primaria', 'visor_cargo_comun_secundaria',
        'visor_cargo_comun_servicios_complementarios', 'visor_cargo_comun_snu',
        'visor_cargo_especial_tln', 'visor_cargos_adulto_fp',
    ]
    if tvista not in opciones_validas or not relevamiento:
        return JsonResponse({'data': [], 'error': 'Parámetros inválidos'}, status=400)

    try:
        connection = conectar_bd(request)
        if not connection:
            return JsonResponse({'data': [], 'error': 'Error de conexión'}, status=500)
        cursor = connection.cursor()

        # ── Query base: misma fuente para cargos y cabeceras ──────────────────
        # El JOIN con el Padrón trae región, sector, etc. para poder filtrar.
        # Armamos el WHERE una sola vez y lo reutilizamos en ambas consultas.
        base_from = f"""
            FROM funcion.{tvista}('{relevamiento}')
            LEFT JOIN (
                SELECT * FROM dblink (
                    'dbname=Padron user=visualizador password=Estadisticas24 host=visoreducativochaco.com.ar port=5432',
                    'SELECT distinct cueanexo, region, sector, ambito, localidad, departamento FROM padron'
                ) AS padron (
                    cueanexo varchar, region varchar, sector varchar,
                    ambito varchar, localidad varchar, departamento varchar
                )
            ) AS p using (cueanexo)
            WHERE 1=1
        """
        parameters = []
        if cueanexo:
            base_from += " AND p.cueanexo = %s"
            parameters.append(cueanexo)
        if ambito:
            base_from += " AND p.ambito = %s"
            parameters.append(ambito)
        if sector:
            base_from += " AND p.sector = %s"
            parameters.append(sector)
        if region:
            base_from += " AND p.region = %s"
            parameters.append(region)
        if departamento:
            base_from += " AND p.departamento = %s"
            parameters.append(departamento)
        if localidad:
            base_from += " AND p.localidad = %s"
            parameters.append(localidad)

        # ── Consulta 1: distribución de cargos ────────────────────────────────
        query_cargos = f"""
            SELECT cargos,
                SUM(CAST(total AS INT)) AS total,
                SUM(CAST(titular AS INT)) AS titular,
                SUM(CAST(interinos AS INT)) AS interinos,
                SUM(CAST(sin_cubrir AS INT)) AS sin_cubrir
            {base_from}
            GROUP BY cargos HAVING SUM(CAST(total AS INT)) <> 0
        """
        cursor.execute(query_cargos, parameters)
        rows = cursor.fetchall()
        data = [{'cargos': r[0], 'total': int(r[1]), 'titular': int(r[2]),
                 'interinos': int(r[3]), 'sin_cubrir': int(r[4])} for r in rows]

        # ── Consulta 2: cueanexos cabecera (mismo RA, misma modalidad, mismos filtros)
        # Un cueanexo cabecera es el que termina en '00', es decir CAST(cueanexo AS INT) % 100 = 0
        query_cabeceras = f"""
            SELECT COUNT(DISTINCT cueanexo)
            {base_from}
            AND MOD(CAST(cueanexo AS INT), 100) = 0
        """
        cursor.execute(query_cabeceras, parameters)
        row_cab = cursor.fetchone()
        total_cabeceras = int(row_cab[0]) if row_cab and row_cab[0] is not None else 0

        connection.close()
        return JsonResponse({'data': data, 'total_cabeceras': total_cabeceras})
    except psycopg2.Error as e:
        return JsonResponse({'data': [], 'error': str(e)}, status=500)




@csrf_exempt
def docentes_ajax(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    cueanexo     = request.POST.get('Cueanexo', '').strip()
    ambito       = request.POST.get('Ambito', '').strip()
    sector       = request.POST.get('Sector', '').strip()
    region       = request.POST.get('Region', '').strip()
    departamento = request.POST.get('Departamento', '').strip()
    localidad    = request.POST.get('Localidad', '').strip()
    relevamiento = request.POST.get('Relevamiento', '').strip()
    tvista       = request.POST.get('Vista', '').strip()

    opciones_validas = [
        'visor_docente_actividad_adulto_fp', 'visor_docente_actividad_adulto_primaria',
        'visor_docente_actividad_adulto_secundaria', 'visor_docente_actividad_comun_inicial',
        'visor_docente_actividad_comun_primaria', 'visor_docente_actividad_comun_secundaria',
        'visor_docente_actividad_comun_servicios_complementarios',
        'visor_docente_actividad_comun_snu', 'visor_docente_actividad_educacion_especial',
    ]
    if tvista not in opciones_validas or not relevamiento:
        return JsonResponse({'data': [], 'error': 'Parámetros inválidos'}, status=400)

    try:
        connection = conectar_bd(request)
        if not connection:
            return JsonResponse({'data': [], 'error': 'Error de conexión'}, status=500)
        cursor = connection.cursor()

        dblink_inner_sql = (
            "SELECT cueanexo, MAX(region), MAX(sector), MAX(ambito), MAX(localidad), MAX(departamento) "
            "FROM padron GROUP BY cueanexo"
        )

        query = f"""
            SELECT docentes,
                SUM(CAST(total AS INT)) AS total,
                SUM(CAST(varones AS INT)) AS varones
            FROM funcion.{tvista}('{relevamiento}')
            LEFT JOIN (
                SELECT * FROM dblink (
                    'dbname=Padron user=visualizador password=Estadisticas24 host=visoreducativochaco.com.ar port=5432',
                    '{dblink_inner_sql}'
                ) AS padron (
                    cueanexo varchar, region varchar, sector varchar,
                    ambito varchar, localidad varchar, departamento varchar
                )
            ) AS p using (cueanexo)
            WHERE 1=1
            AND docentes != 'Total docentes en actividad'
            AND docentes != 'Docentes en tareas pasivas'
        """
        parameters = []
        if cueanexo:
            query += " AND p.cueanexo = %s"
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
        cursor.execute(query, parameters)
        rows = cursor.fetchall()
        connection.close()
        data = [{'docentes': r[0], 'total': int(r[1]), 'varones': int(r[2])} for r in rows]
        return JsonResponse({'data': data})
    except psycopg2.Error as e:
        return JsonResponse({'data': [], 'error': str(e)}, status=500)


@csrf_exempt
def docentes_pasiva_ajax(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    cueanexo     = request.POST.get('Cueanexo', '').strip()
    ambito       = request.POST.get('Ambito', '').strip()
    sector       = request.POST.get('Sector', '').strip()
    region       = request.POST.get('Region', '').strip()
    departamento = request.POST.get('Departamento', '').strip()
    localidad    = request.POST.get('Localidad', '').strip()
    relevamiento = request.POST.get('Relevamiento', '').strip()
    tvista       = request.POST.get('Vista', '').strip()

    opciones_validas = [
        'visor_docente_actividad_adulto_fp', 'visor_docente_actividad_adulto_primaria',
        'visor_docente_actividad_adulto_secundaria', 'visor_docente_actividad_comun_inicial',
        'visor_docente_actividad_comun_primaria', 'visor_docente_actividad_comun_secundaria',
        'visor_docente_actividad_comun_servicios_complementarios',
        'visor_docente_actividad_comun_snu', 'visor_docente_actividad_educacion_especial',
    ]
    if tvista not in opciones_validas or not relevamiento:
        return JsonResponse({'data': [], 'error': 'Parámetros inválidos'}, status=400)

    try:
        connection = conectar_bd(request)
        if not connection:
            return JsonResponse({'data': [], 'error': 'Error de conexión'}, status=500)
        cursor = connection.cursor()

        dblink_inner_sql = (
            "SELECT cueanexo, MAX(region), MAX(sector), MAX(ambito), MAX(localidad), MAX(departamento) "
            "FROM padron GROUP BY cueanexo"
        )

        query = f"""
            SELECT docentes,
                SUM(CAST(total AS INT)) AS total,
                SUM(CAST(varones AS INT)) AS varones
            FROM funcion.{tvista}('{relevamiento}')
            LEFT JOIN (
                SELECT * FROM dblink (
                    'dbname=Padron user=visualizador password=Estadisticas24 host=visoreducativochaco.com.ar port=5432',
                    '{dblink_inner_sql}'
                ) AS padron (
                    cueanexo varchar, region varchar, sector varchar,
                    ambito varchar, localidad varchar, departamento varchar
                )
            ) AS p using (cueanexo)
            WHERE 1=1 AND docentes = 'Docentes en tareas pasivas'
        """
        parameters = []
        if cueanexo:
            query += " AND p.cueanexo = %s"
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
        
        cursor.execute(query, parameters)
        rows = cursor.fetchall()
        connection.close()
        
        data = [{'docentes': r[0], 'total': int(r[1]), 'varones': int(r[2])} for r in rows]
        return JsonResponse({'data': data})
    except psycopg2.Error as e:
        return JsonResponse({'data': [], 'error': str(e)}, status=500)

@csrf_exempt
def horas_ajax(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    cueanexo     = request.POST.get('Cueanexo', '').strip()
    ambito       = request.POST.get('Ambito', '').strip()
    sector       = request.POST.get('Sector', '').strip()
    region       = request.POST.get('Region', '').strip()
    departamento = request.POST.get('Departamento', '').strip()
    localidad    = request.POST.get('Localidad', '').strip()
    relevamiento = request.POST.get('Relevamiento', '').strip()
    tvista       = request.POST.get('Vista', '').strip()

    opciones_validas = [
        'visor_horas_adulto_fp', 'visor_horas_adulto_primaria',
        'visor_horas_adulto_secundaria', 'visor_horas_comun_inicial',
        'visor_horas_comun_primaria', 'visor_horas_comun_secundaria','visor_horas_comun_artistica',
        'visor_horas_comun_servicios_complementarios',
        'visor_horas_comun_snu', 'visor_horas_especial_temprana',
    ]
    if tvista not in opciones_validas or not relevamiento:
        return JsonResponse({'data': [], 'error': 'Parámetros inválidos'}, status=400)

    try:
        connection = conectar_bd(request) # Asumo que tu función recibe request
        if not connection:
            return JsonResponse({'data': [], 'error': 'Error de conexión'}, status=500)
        cursor = connection.cursor()

        dblink_inner_sql = (
            "SELECT cueanexo, MAX(region), MAX(sector), MAX(ambito), MAX(localidad), MAX(departamento) "
            "FROM padron GROUP BY cueanexo"
        )

        # 1. CONSULTA BLINDADA CON REGEX
        query = f"""
            SELECT cargos,
                SUM(NULLIF(REGEXP_REPLACE(total::text, '[^0-9]', '', 'g'), '')::integer) AS total,
                SUM(NULLIF(REGEXP_REPLACE(titular::text, '[^0-9]', '', 'g'), '')::integer) AS titular,
                SUM(NULLIF(REGEXP_REPLACE(interinos::text, '[^0-9]', '', 'g'), '')::integer) AS interinos,
                SUM(NULLIF(REGEXP_REPLACE(sin_cubrir::text, '[^0-9]', '', 'g'), '')::integer) AS sin_cubrir
            FROM funcion.{tvista}('{relevamiento}')
            LEFT JOIN (
                SELECT * FROM dblink (
                    'dbname=Padron user=visualizador password=Estadisticas24 host=visoreducativochaco.com.ar port=5432',
                    '{dblink_inner_sql}'
                ) AS padron (
                    cueanexo varchar, region varchar, sector varchar,
                    ambito varchar, localidad varchar, departamento varchar
                )
            ) AS p using (cueanexo)
            WHERE 1=1
        """
        parameters = []
        if cueanexo:
            query += " AND p.cueanexo = %s"
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
        
        # 2. SE CAMBIA `<> 0` por `IS NOT NULL` (para que muestre los 0)
        query += " GROUP BY cargos HAVING SUM(NULLIF(REGEXP_REPLACE(total::text, '[^0-9]', '', 'g'), '')::integer) IS NOT NULL"
        
        cursor.execute(query, parameters)
        rows = cursor.fetchall()
        connection.close()
        
        # 3. PROTECCIÓN `or 0` PARA EVITAR ERRORES SI UN DATO ES NONE
        data = [{'horas': r[0], 
                 'total': int(r[1] or 0), 
                 'titular': int(r[2] or 0),
                 'interinos': int(r[3] or 0), 
                 'sin_cubrir': int(r[4] or 0)} for r in rows]
                 
        return JsonResponse({'data': data})
        
    except psycopg2.Error as e:
        if 'connection' in locals() and connection:
            connection.close() # Buena práctica: cerrar siempre si hay error
        return JsonResponse({'data': [], 'error': str(e)}, status=500)

@csrf_exempt
def cueanexos_cabecera_ajax(request):
    """
    Cuenta establecimientos CABECERA basándose estrictamente en la vista del Relevamiento
    seleccionado (ej: funcion.visor_cargo_comun_primaria). Esto garantiza que el número
    sea exactamente el reflejo de los datos del año y modalidad que se están consultando.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    cueanexo     = request.POST.get('Cueanexo', '').strip()
    ambito       = request.POST.get('Ambito', '').strip()
    sector       = request.POST.get('Sector', '').strip()
    region       = request.POST.get('Region', '').strip()
    departamento = request.POST.get('Departamento', '').strip()
    localidad    = request.POST.get('Localidad', '').strip()
    relevamiento = request.POST.get('Relevamiento', '').strip()
    tvista       = request.POST.get('Vista', '').strip() 

    # Lista unificada de todas las vistas posibles
    opciones_validas = [
        'visor_cargo_adulto_primaria', 'visor_cargo_adulto_secundaria',
        'visor_cargo_comun_artistica', 'visor_cargo_comun_inicial',
        'visor_cargo_comun_primaria', 'visor_cargo_comun_secundaria',
        'visor_cargo_comun_servicios_complementarios', 'visor_cargo_comun_snu',
        'visor_cargo_especial_tln', 'visor_cargos_adulto_fp',
        'visor_docente_actividad_adulto_fp', 'visor_docente_actividad_adulto_primaria',
        'visor_docente_actividad_adulto_secundaria', 'visor_docente_actividad_comun_inicial',
        'visor_docente_actividad_comun_primaria', 'visor_docente_actividad_comun_secundaria',
        'visor_docente_actividad_comun_servicios_complementarios',
        'visor_docente_actividad_comun_snu', 'visor_docente_actividad_educacion_especial',
        'visor_horas_adulto_fp', 'visor_horas_adulto_primaria',
        'visor_horas_adulto_secundaria', 'visor_horas_comun_inicial',
        'visor_horas_comun_primaria', 'visor_horas_comun_secundaria',
        'visor_horas_comun_servicios_complementarios',
        'visor_horas_comun_snu', 'visor_horas_especial_temprana'
    ]

    if tvista not in opciones_validas or not relevamiento:
        return JsonResponse({'count': None, 'error': 'Parámetros inválidos'}, status=400)

    try:
        connection = conectar_bd(request)
        if not connection:
            return JsonResponse({'count': None, 'error': 'Error de conexión'}, status=500)

        cursor = connection.cursor()

        # Padrón solo usado para geografía
        dblink_inner_sql = (
            "SELECT cueanexo, MAX(region), MAX(sector), MAX(ambito), MAX(localidad), MAX(departamento) "
            "FROM padron GROUP BY cueanexo"
        )

        # Usamos CAST(cueanexo AS TEXT) para evitar que Postgres lance error si es un BIGINT
        query = f"""
            SELECT COUNT(DISTINCT cueanexo)
            FROM funcion.{tvista}('{relevamiento}')
            LEFT JOIN (
                SELECT * FROM dblink (
                    'dbname=Padron user=visualizador password=Estadisticas24 host=visoreducativochaco.com.ar port=5432',
                    '{dblink_inner_sql}'
                ) AS padron (
                    cueanexo varchar, region varchar, sector varchar,
                    ambito varchar, localidad varchar, departamento varchar
                )
            ) AS p USING (cueanexo)
            WHERE RIGHT(CAST(cueanexo AS TEXT), 2) = '00'
        """

        parameters = []
        
        if cueanexo:
            query += " AND p.cueanexo = %s"
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

        cursor.execute(query, parameters)
        row = cursor.fetchone()
        connection.close()

        count = int(row[0]) if row and row[0] is not None else 0
        return JsonResponse({'count': count})
        
    except Exception as e:
        import traceback
        print(f"[cabecera_ajax ERROR] {traceback.format_exc()}")
        return JsonResponse({'count': None, 'error': str(e)}, status=200)