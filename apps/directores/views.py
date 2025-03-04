import json
import os
import dotenv
import psycopg2
import asyncpg # type: ignore
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required


#####################################################################
#           PARA MOSTRAR DATOS INSTITUCIONALES DEL USUARIO          #
#####################################################################
@login_required
def filtrar_tablas_view_directores(request):
    """
    Muestra los datos institucionales del usuario autenticado.

    Esta vista se encarga de obtener y mostrar información relacionada
    con el usuario logueado, incluyendo datos institucionales, planes de
    estudio, anexos y ofertas. Se conecta a la base de datos 'Padron' para
    realizar las consultas necesarias.

    Args:
        request: El objeto HttpRequest que contiene información sobre la
                 solicitud del usuario.

    Returns:
        HttpResponse: Renderiza la plantilla 'directores/institucional.html'
                      con los resultados obtenidos de la base de datos.
    """
    # Obtener el username del usuario logueado
    cueanexo = request.user.username    

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

    # Consultas SQL
    institucional = """
        SELECT nom_est, categoria, jornada, oferta, id_establecimiento, ref_loc, calle, numero, anexo, apellido_resp, nombre_resp, resploc_telefono, resploc_email,
            sup_tecnico, email_suptecnico, tel_suptecnico
        FROM padron_ofertas        
        WHERE cueanexo = %s 
    """ 
    planes = """
        SELECT titulo, orientacion
        FROM v_planes_estudio
        WHERE CONCAT(cue, anexo) = %s AND estado_ofertalocal = 'Activo'
    """
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
        SELECT anexo, calle, numero, cueanexo, oferta, est_oferta,acronimo_oferta, sector
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
    
    print('institucional:', resultados) 
    print('planes:', resultados1)
    print('anexos:', resultados2)
    print('ofertas:', resultados3)
    
    # Verificamos si "Bibliotecas" está en las ofertas
    tiene_bibliotecas = any(oferta['acronimo_oferta'].startswith('BI%') for oferta in resultados3)
    
    # Verificamos si "Privado" está en las ofertas
    privado = any(oferta['sector'] == 'Privado' for oferta in resultados3)
    
    context = {
        'institucional': resultados,
        'planes': resultados1,
        'anexos': resultados2,
        'ofertas': resultados3,
        'tiene_bibliotecas': tiene_bibliotecas,
        'privado': privado,
    }
    
    return render(request, 'directores/institucional.html', {'resultados': resultados, 'resultados1': resultados1, 'resultados2': resultados2, 'resultados3': resultados3, 'tiene_bibliotecas': tiene_bibliotecas, 'privado': privado})


@login_required
def filter_matricula_views_directores(request):
    """
    Filtra y muestra la matrícula de acuerdo a la oferta educativa.

    Esta vista se encarga de obtener la matrícula de los estudiantes
    en función de la oferta educativa activa asociada al usuario logueado.
    Se conecta a la base de datos 'visualizador' para realizar las consultas
    necesarias y luego renderiza la plantilla correspondiente con los resultados.

    Args:
        request: El objeto HttpRequest que contiene información sobre la
                 solicitud del usuario.

    Returns:
        HttpResponse: Renderiza la plantilla 'directores/matricula.html'
                      con los detalles de matrícula obtenidos de la base de datos.
    """
    cueanexo = request.user.username
    
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
    
    ofertascue="""SELECT cueanexo, oferta, nom_est
                    FROM padron_ofertas
                    WHERE est_oferta='Activo' AND cueanexo=%s"""
    
      
    paramcue=(cueanexo,)        

    cursor.execute(idest,paramcue)
    resulidest=cursor.fetchall()
    print('id_est:',resulidest)
    
    cursor.execute(establecimiento,resulidest)
    resulestab=cursor.fetchall()
    print('est:',resulestab)
    
    cursor.execute(ofertascue,paramcue)
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
                            FROM funcion.visor_matric_adulto_primaria('ra_carga2023')
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
                        FROM funcion.visor_matric_adulto_secundaria('ra_carga2023')
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
                        FROM funcion.visor_matric_comun_inicial('ra_carga2023')
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
                        FROM funcion.visor_matric_comun_primaria('ra_carga2023')
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
                        FROM funcion.visor_matric_comun_secundaria('ra_carga2023')
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
    return render(request, 'directores/matricula.html', {'resultados_detalle':resultados_detalle})


    