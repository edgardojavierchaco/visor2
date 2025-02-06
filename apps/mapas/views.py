import json
import os
import dotenv

import psycopg2
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.db import connection
from django.contrib.auth.decorators import login_required

"""
Este módulo maneja la lógica de filtrado y consultas de datos en un mapa interactivo utilizando Django y PostgreSQL.

Funciones:
    filtrado(request):
        Renderiza la página inicial para filtrar los datos de las ofertas educativas.

    filtrado_list(request):
        Renderiza la página que muestra el listado de resultados filtrados.

    operaciones_comunes(request, template_name='publico/basecriterios.html'):
        Realiza consultas SQL para obtener datos filtrados según los parámetros enviados en la solicitud POST.
        Filtra las ofertas educativas según criterios como cueanexo, ambito, sector, localidad, entre otros.
        Devuelve un contexto con los datos filtrados para ser utilizado en diferentes plantillas HTML.

    filter_data(request):
        Llama a 'operaciones_comunes' y renderiza los resultados en la plantilla 'mapa/ofertasmark.html'.

    filter_listado_map(request):
        Llama a 'operaciones_comunes' y renderiza los resultados en la plantilla 'publico/listadomap.html'.

    filtrar_tablas_view(request):
        Filtra y consulta los datos detallados de un establecimiento educativo seleccionado.
        Realiza múltiples consultas SQL a las tablas institucionales, de planes de estudio, anexos y ofertas.
        Maneja casos específicos de ofertas educativas y ajusta la consulta SQL según la oferta seleccionada.
        Devuelve los resultados detallados de la oferta seleccionada en función del cueanexo.
"""


def filtrado(request):    
    return render(request, 'mapa/filter.html')

def filtrado_list(request):
    return render(request,'mapa/filter_listadomap.html')

@csrf_exempt
def operaciones_comunes(request, template_name='publico/basecriterios.html'):   
    if request.method == 'POST':
        cueanexo = request.POST.get('Cueanexo')
        ambito = request.POST.get('Ambito')
        sector = request.POST.get('Sector')
        region = request.POST.get('Region')
        departamento = request.POST.get('Departamento')
        localidad = request.POST.get('Localidad')
        oferta = request.POST.get('Oferta')
        nom_est=request.POST.get('nomest')
        cui=request.POST.get('Cui')

        print("Parámetros de la solicitud:", ambito, sector, localidad, oferta, nom_est, cui)

        
        # Realizar la consulta en la base de datos
        cursor = connection.cursor()
        query = "SELECT cueanexo, lat, long, nom_est, oferta, ambito, sector, region_loc, calle, numero, localidad, cui_loc, cuof_loc FROM v_capa_unica_ofertas_cui_cuof WHERE 1=1 "
        parameters = []
        if cueanexo:
            query += "AND cueanexo = %s"
            parameters.append(cueanexo)
        if ambito:
            query += " AND ambito = %s"
            parameters.append(ambito)
        if sector:
            query += " AND sector = %s"
            parameters.append(sector)
        if region:
            query += " AND region_loc = %s"
            parameters.append(region)
        if departamento:
            query += " AND departamento = %s"
            parameters.append(departamento)
        if localidad:
            query += "AND localidad = %s"
            parameters.append(localidad)
        if cui:
            query += " AND cui_loc = %s"
            parameters.append(cui)
        if oferta:
            query += "AND oferta LIKE %s"
            parameters.append(oferta+'%')
        if nom_est:
            query += " AND nom_est ILIKE %s"
            parameters.append('%' + nom_est + '%')

        cursor.execute(query, parameters)
        rows = cursor.fetchall()

        # Filtrar los marcadores con latitud y longitud distintas de 0 o vacías
        filtered_rows = [(cueanexo, lat, lng, nom_est, oferta, ambito, sector, region_loc, calle, numero, localidad, cui_loc, cuof_loc) 
                         for cueanexo, lat, lng, nom_est, oferta, ambito, sector, region_loc, calle, numero, localidad,cui_loc, cuof_loc in rows 
                         if lat != 0 and lng != '' and lng != 0 and lat != '']

        # Obtener los nombres de las columnas
        column_names = [desc[0] for desc in cursor.description] # type: ignore
        filtered_rows = [row for row in rows if row[1] != 0 and row[2] != 0]

        # Cerrar la conexión a la base de datos
        cursor.close()
        connection.close()

        context = {
            'title': 'Mapa',
            'data_json': json.dumps(filtered_rows),
            'column_names_json': json.dumps(column_names)
        }

        print("Contexto en operaciones_comunes:", context)

        if template_name == 'publico/basecriterios.html':
            return context
        elif template_name == 'publico/listadomap.html':
            return context
        else:
            return context
        
def filter_data(request):
    context = operaciones_comunes(request, template_name='publico/basecriterios.html')
    print("Contexto en filter_data:", context)
    return render(request, 'mapa/ofertasmark.html', context)

def filter_listado_map(request):
    context = operaciones_comunes(request, template_name='publico/listadomap.html')
    print("Contexto en filter_listado_map:", context)
    return render(request, 'publico/listadomap.html', context)


    
#####################################################################
#      PARA MOSTRAR DATOS MARCADOR SELLECIONADO EN EL MAPA          #
#####################################################################
def filtrar_tablas_view(request):
    cueanexo = request.GET.get('cueanexo')
    ofertarec=request.GET.get('oferta')

    # Validar y sanitizar el valor de cueanexo
    if cueanexo is None:
        # Manejar el caso si no se proporciona cueanexo
        return render(request, 'error.html', {'mensaje': 'No se proporcionó el parámetro cueanexo'})

    # Establecer la conexión a la base de datos Padrón
    try:
        connection = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST'),
            user=os.getenv('POSTGRES_USER'),
            password=os.getenv('POSTGRES_PASSWORD'),
            database=os.getenv('DB_NAME1')
        )
        cursor = connection.cursor()
    except psycopg2.Error as e:
        # Manejar el error de conexión
        return render(request, 'error.html', {'mensaje': 'Error al conectar a la base de datos'})

    # Construir y ejecutar la consulta SQL para obtener los datos de las dos tablas
    
    institucional = """
        SELECT categoria, jornada, oferta, id_establecimiento, ref_loc, calle, numero, anexo,apellido_resp, nombre_resp, resploc_telefono,resploc_email,
            sup_tecnico, email_suptecnico, tel_suptecnico, cui_loc, cuof_loc
        FROM public.padron_ofertas        
        WHERE cueanexo = %s 
    """ 
    planes="""
        SELECT titulo, orientacion
        FROM v_planes_estudio
        WHERE CONCAT(cue,anexo)=%s AND estado_ofertalocal='Activo'
    """

    # Construir y ejecutar la consulta SQL para obtener los datos de las dos tablas
    anexos = """
        SELECT DISTINCT po.anexo, po.calle, po.numero, po.estado_loc
        FROM padron_ofertas po
        WHERE po.id_establecimiento IN (
            SELECT id_establecimiento
            FROM padron_ofertas
            WHERE cueanexo = %s 
        ) AND po.estado_loc = %s
    """
    ofertas = """
        SELECT anexo, calle, numero, cueanexo, oferta, est_oferta
        FROM padron_ofertas
        WHERE cueanexo = %s AND est_oferta = %s        
    """
    params = (cueanexo,)
    params2 = (cueanexo, 'Activo')

    try:
        cursor.execute(institucional, params)
        resultados = [dict(zip([column[0] for column in cursor.description], row)) for row in cursor.fetchall()]
        
        cursor.execute(planes, params)
        resultados1 = [dict(zip([column[0] for column in cursor.description], row)) for row in cursor.fetchall()]
       
        cursor.execute(anexos, params2)
        resultados2 = [dict(zip([column[0] for column in cursor.description], row)) for row in cursor.fetchall()]
        
        cursor.execute(ofertas, params2)
        resultados3 = [dict(zip([column[0] for column in cursor.description], row)) for row in cursor.fetchall()]
        
    except psycopg2.Error as e:
        # Manejar el error de consulta
        connection.close()
        return render(request, 'error.html', {'mensaje': 'Error al ejecutar la consulta'})

    # Cerrar la conexión a la base de datos
    connection.close()    
    print('institucional:',resultados) 
    print('planes:',resultados1)
    print('anexos:',resultados2)
    print('ofertas:',resultados3)
    
    # Cerrar la conexión a la base de datos
    connection.close()  
    
    
    cueanexo = request.GET.get('cueanexo')

    # Validar y sanitizar el valor de cueanexo
    if cueanexo is None:
        # Manejar el caso si no se proporciona cueanexo
        return render(request, 'error.html', {'mensaje': 'No se proporcionó el parámetro cueanexo'})
    # Establecer la conexión a la base de datos Padrón
    try:
        connection = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST'),
            user=os.getenv('POSTGRES_USER'),
            password=os.getenv('POSTGRES_PASSWORD'),
            database=os.getenv('POSTGRES_DB')
        )
        cursor = connection.cursor()
    except psycopg2.Error as e:
        # Manejar el error de conexión
        return render(request, 'error.html', {'mensaje': 'Error al conectar a la base de datos'})
  
    idest="""select distinct id_establecimiento
            FROM public.padron_ofertas
            WHERE cueanexo=%s AND est_oferta='Activo'
    """
    
    establecimiento="""select distinct cueanexo
            FROM public.padron_ofertas
            WHERE id_establecimiento=%s AND est_oferta='Activo'
    """
    
    ofertascue="""SELECT cueanexo, oferta
                    FROM padron_ofertas
                    WHERE est_oferta='Activo' AND cueanexo=%s AND oferta=%s
    """
    
    if ofertarec=='Común - Jardín de Infantes':
        ofertarec='Común - Jardín de Infantes '
    elif ofertarec=='Común - Jardín maternal':
        ofertarec='Común - Jardín maternal '
    elif ofertarec=='Común - Primaria de 7 años':
        ofertarec='Común - Primaria de 7 años '
    elif ofertarec=='Común - Secundaria Completa req. 7 años':
        ofertarec='Común - Secundaria Completa req. 7 años '
    elif ofertarec=='Común - SNU':
        ofertarec='Común - SNU '
    elif ofertarec=='Adultos - Primaria':
        ofertarec='Adultos - Primaria '
    elif ofertarec=='Adultos - Secundaria Completa':
        ofertarec='Adultos - Secundaria Completa '
    

    
    paramcue=(cueanexo,)    
    paramcueofer=(cueanexo,ofertarec)

    cursor.execute(idest,paramcue)
    resulidest=cursor.fetchall()
    print('id_est:',resulidest)
    
    cursor.execute(establecimiento,resulidest)
    resulestab=cursor.fetchall()
    print('est:',resulestab)
    
    cursor.execute(ofertascue,paramcueofer)
    resuloferta=cursor.fetchall()
    print('resultoferta:',resuloferta)
    
    parametros_str = ','.join([f"'{str(res[0])}'" for res in resulestab])
    print('parametros_str:',parametros_str)
    #parametros_tupla = tuple(parametros_str)
    
    resultados_detalle=[]
    
    try:
        for row in resuloferta:
            ofertascue=row[1]
            resultados_por_oferta = {'encabezados': [], 'valores': []}
            
            if ofertascue=='Adultos - Primaria ':        
                adultoprim= """SELECT cueanexo, turno, tipo_secc AS tipo, nom_secc as seccion, grado AS Ciclo, total, edad_menos_13 AS "Edad menor 13", 
                                SUM(edad_13 + edad_14 + edad_15 + edad_16 + edad_17 + edad_18) AS "Edad 13-18",
                                sum(edad_19+edad_20_a_24+edad_25_a_29) as "Edad 19-29",
                                sum(edad_30_a_34+edad_35_a_39) as "Edad 30-39",
                                sum(edad_40_a_44+edad_45_a_49) as "Edad 40-49",
                                sum(edad_50_a_54+edad_55_mas) as "Edad 50 o más"
                            FROM funcion.visor_matric_adulto_primaria('ra_carga2024')
                            WHERE cueanexo = %s
                            GROUP BY cueanexo, turno, tipo_secc, nom_secc, grado, total, edad_menos_13
                            ORDER BY cueanexo, grado;"""
                cursor.execute(adultoprim,paramcue)
                resultados_por_oferta['encabezados'] = [desc[0] for desc in cursor.description]
                resultados_por_oferta['valores'] = cursor.fetchall()      
                
            elif ofertascue=='Adultos - Secundaria Completa':            
                adultosec="""SELECT cueanexo, turno, grado as Año, tipo_div AS tipo, nom_secc as seccion, total, 
                            sum(edad_14+edad_15+edad_16+edad_17) AS "Edad 14-17", 	
                            sum(edad_18+edad_19+edad_20+edad_21+edad_22+edad_23+edad_24+edad_25_a_29) as "Edad 18-29",
                            sum(edad_30_a_34+edad_35_a_39) as "Edad 30-39",
                            sum(edad_40_a_44+edad_45_a_49) as "Edad 40-49",
                            sum(edad_50_a_54+edad_50_y_mas) as "Edad 50 o más"
                        FROM funcion.visor_matric_adulto_secundaria('ra_carga2024')
                        WHERE cueanexo =%s
                        GROUP BY cueanexo, turno, tipo_div, nom_secc, grado, total
                        ORDER BY cueanexo, grado;
                """
                cursor.execute(adultosec,paramcue)
                resultados_por_oferta['encabezados'] = [desc[0] for desc in cursor.description]
                resultados_por_oferta['valores'] = cursor.fetchall()
                
            elif ofertascue=='Común - Jardín de infantes ' or ofertascue=='Común - Jardín maternal ':
                comuninicial="""SELECT cueanexo, turno, grado as sala, tipo_secc AS tipo, nom_secc as seccion, total,
                            menos_1_año as "Menos 1 año", un_año as "1 año", dos_años as "2 años", tres_años as "3 años",
                            cuatro_años as "4 Años", cinco_años as "5 años", seis_años as "6 años", total_disc as "Discapacitados"
                        FROM funcion.visor_matric_comun_inicial('ra_carga2024')
                        WHERE cueanexo =%s
                        GROUP BY cueanexo, turno, grado, tipo_secc, nom_secc, total, menos_1_año, un_año, dos_años, tres_años, cuatro_años, cinco_años, seis_años, total_disc
                        ORDER BY cueanexo, grado;    
                """
                cursor.execute(comuninicial,paramcue)
                resultados_por_oferta['encabezados'] = [desc[0] for desc in cursor.description]
                resultados_por_oferta['valores'] = cursor.fetchall()
                
            elif ofertascue=='Común - Primaria de 7 años ':
                comunprim="""SELECT cueanexo, turno, grado, tipo_secc AS tipo, nom_secc as seccion, total,
                            edad_5 as "5 años", edad_6 as "6 años", edad_7 as "7 años", edad_8 as "8 años",
                            edad_9 as "9 Años", edad_10 as "10 años", edad_11 as "11 años", edad_12 as "12 años",
                            sum(edad_13+edad_14+edad_15+edad_16+edad_17+edad_18_y_mas) as "13 o más años",
                            tot_discapacidad as "Discapacitados"
                        FROM funcion.visor_matric_comun_primaria('ra_carga2024')
                        WHERE cueanexo =%s
                        GROUP BY cueanexo, turno, grado, tipo_secc, nom_secc, total, edad_5, edad_6, edad_7, edad_8, edad_9, edad_10, edad_11, edad_12, tot_discapacidad
                        ORDER BY cueanexo, grado;   
                """
                cursor.execute(comunprim,paramcue)
                resultados_por_oferta['encabezados'] = [desc[0] for desc in cursor.description]
                resultados_por_oferta['valores'] = cursor.fetchall()
                
            elif ofertascue=='Común - Secundaria Completa req. 7 años ':
                comunsec="""SELECT cueanexo, turno, grado as año, tipo_div AS tipo, nom_secc as seccion, total,
                            edad_12 as "12 años", edad_13 as "13 años", edad_14 as "14 años", edad_15 as "15 años",
                            edad_16 as "16 Años", edad_17 as "17 años", edad_18 as "18 años", edad_19 as "19 años",
                            sum(edad_20_24+edad_25_y_mas) as "20 a más",
                            total_disc as "Discapacitados"
                        FROM funcion.visor_matric_comun_secundaria('ra_carga2024')
                        WHERE cueanexo =%s
                        GROUP BY cueanexo, turno, grado, tipo_div, nom_secc, total, edad_12, edad_13, edad_14, edad_15, edad_16, edad_17, edad_18, edad_19, total_disc
                        ORDER BY cueanexo, grado;   
                """
                cursor.execute(comunsec,paramcue)
                resultados_por_oferta['encabezados'] = [desc[0] for desc in cursor.description]
                resultados_por_oferta['valores'] = cursor.fetchall()      

            # Añadir los resultados de esta oferta a la lista de resultados
            resultados_detalle.append(resultados_por_oferta)
            print('resultados:', resultados_detalle)
            
    except psycopg2.Error as e:
        # Manejar el error de consulta
        connection.close()
        return render(request, 'error.html', {'mensaje': 'Error al ejecutar la consulta'})
    
    # Transformar los resultados en una respuesta renderizada
    return render(request, 'mapa/otro_template.html', {'resultados': resultados, 'resultados1': resultados1, 'resultados2': resultados2, 'resultados3': resultados3, 'resultados_detalle':resultados_detalle})

