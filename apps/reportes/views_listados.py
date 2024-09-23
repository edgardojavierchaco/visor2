from django.shortcuts import render
from django.db import connection
from django.http import JsonResponse

def consulta_ofertas(request):
    departamentos = []
    datos = {}
    selected_departamento = request.GET.get('departamento')
    #print('seleccionado:', selected_departamento)

    # Obtener los departamentos únicos
    with connection.cursor() as cursor:
        cursor.execute("SELECT DISTINCT departamento FROM v_capa_unica_ofertas")
        departamentos = [row[0] for row in cursor.fetchall()]

    # Construir la consulta SQL sin filtro inicialmente
    query = """
        SELECT 
            COUNT(*) AS total_ofertas,
            SUM(CASE WHEN ambito = 'Urbano' THEN 1 ELSE 0 END) AS total_urbanos,
            SUM(CASE WHEN ambito = 'Rural Disperso' THEN 1 ELSE 0 END) AS total_rurales_dispersos,
            SUM(CASE WHEN ambito = 'Rural Aglomerado' THEN 1 ELSE 0 END) AS total_rurales_aglomerados,
            SUM(CASE WHEN sector = 'Estatal' THEN 1 ELSE 0 END) AS total_estatales,
            SUM(CASE WHEN sector = 'Privado' THEN 1 ELSE 0 END) AS total_privados,
            SUM(CASE WHEN sector = 'Gestión social/cooperativa' THEN 1 ELSE 0 END) AS total_soccom,
            SUM(CASE WHEN cueanexo % 100 = 0 THEN 1 ELSE 0 END) AS total_sedes,
            SUM(CASE WHEN cueanexo % 100 != 0 THEN 1 ELSE 0 END) AS total_anexos,
            SUM(CASE WHEN oferta = 'Común - Jardín maternal ' OR oferta = 'Común - Jardín de infantes ' THEN 1 ELSE 0 END) AS total_inicial,
            SUM(CASE WHEN oferta = 'Común - Primaria de 7 años ' THEN 1 ELSE 0 END) AS total_primario,
            SUM(CASE WHEN oferta = 'Adultos - Primaria ' THEN 1 ELSE 0 END) AS total_adultoprim,
            SUM(CASE WHEN oferta = 'Común - Secundaria Completa req. 7 años ' THEN 1 ELSE 0 END) AS total_secundaria,
            SUM(CASE WHEN oferta = 'Adultos - Secundaria Completa' THEN 1 ELSE 0 END) AS total_adultosec,
            SUM(CASE WHEN oferta = 'Adultos - Formación Profesional ' THEN 1 ELSE 0 END) AS total_adultofp,
            SUM(CASE WHEN oferta ILIKE 'Especial%' THEN 1 ELSE 0 END) AS total_especial,
            SUM(CASE WHEN oferta = 'Común - SNU ' THEN 1 ELSE 0 END) AS total_snu,
            SUM(CASE WHEN acronimo = 'BI ANEXO' OR acronimo = 'BI' THEN 1 ELSE 0 END) AS total_biblio,
            SUM(CASE WHEN acronimo = 'CEF' THEN 1 ELSE 0 END) AS total_cef
        FROM 
            v_capa_unica_ofertas
    """

    # Si un departamento ha sido seleccionado, agregar el WHERE
    if selected_departamento:
        query += f" WHERE departamento='{selected_departamento}'"

    # Ejecutar la consulta
    with connection.cursor() as cursor:
        cursor.execute(query)
        row = cursor.fetchone()

        # Verificar si se obtuvo un resultado
        if row and all(value is not None for value in row):
            datos = {
                'total_ofertas': row[0],
                'total_urbanos': row[1],
                'total_rurales_dispersos': row[2],
                'total_rurales_aglomerados': row[3],
                'total_estatales': row[4],
                'total_privados': row[5],
                'total_soccom': row[6],
                'total_sedes': row[7],
                'total_anexos': row[8],
                'total_inicial': row[9],
                'total_primario': row[10],
                'total_adultoprim': row[11],
                'total_secundaria': row[12],
                'total_adultosec': row[13],
                'total_adultofp': row[14],
                'total_especial': row[15],
                'total_snu': row[16],
                'total_biblio': row[17],
                'total_cef': row[18],
            }
        else:
            # Si no hay resultados, inicializa con ceros
            datos = {
                'total_ofertas': 0,
                'total_urbanos': 0,
                'total_rurales_dispersos': 0,
                'total_rurales_aglomerados': 0,
                'total_estatales': 0,
                'total_privados': 0,
                'total_soccom': 0,
                'total_sedes': 0,
                'total_anexos': 0,
                'total_inicial': 0,
                'total_primario': 0,
                'total_adultoprim': 0,
                'total_secundaria': 0,
                'total_adultosec': 0,
                'total_adultofp': 0,
                'total_especial': 0,
                'total_snu': 0,
                'total_biblio': 0,
                'total_cef': 0,
            }

    # Responder con JSON si es una solicitud AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse(datos)

    context = {
        'departamentos': departamentos,
        'datos': datos,
    }
    return render(request, 'reportes/listadosestablecimientos.html', context)


def consulta_ofertas_reg(request):
    regionales = []
    localidades=[]
    datos = {}
    selected_regionales = request.GET.get('region')
    print('seleccionado:', selected_regionales)

    # Obtener los departamentos únicos
    with connection.cursor() as cursor:
        cursor.execute("SELECT DISTINCT region_loc FROM v_capa_unica_ofertas")
        regionales = [row[0] for row in cursor.fetchall()]
    
    
    local="""SELECT DISTINCT localidad FROM v_capa_unica_ofertas"""
    
    if selected_regionales:
        local += f" WHERE region_loc='{selected_regionales}'"

    # Ejecutar la consulta
    with connection.cursor() as cursor:
        cursor.execute(local)
        localidades = cursor.fetchall()
    print('localidades:',localidades)

    # Construir la consulta SQL sin filtro inicialmente
    query = """
        SELECT 
            COUNT(*) AS total_ofertas,
            SUM(CASE WHEN ambito = 'Urbano' THEN 1 ELSE 0 END) AS total_urbanos,
            SUM(CASE WHEN ambito = 'Rural Disperso' THEN 1 ELSE 0 END) AS total_rurales_dispersos,
            SUM(CASE WHEN ambito = 'Rural Aglomerado' THEN 1 ELSE 0 END) AS total_rurales_aglomerados,
            SUM(CASE WHEN sector = 'Estatal' THEN 1 ELSE 0 END) AS total_estatales,
            SUM(CASE WHEN sector = 'Privado' THEN 1 ELSE 0 END) AS total_privados,
            SUM(CASE WHEN sector = 'Gestión social/cooperativa' THEN 1 ELSE 0 END) AS total_soccom,
            SUM(CASE WHEN cueanexo % 100 = 0 THEN 1 ELSE 0 END) AS total_sedes,
            SUM(CASE WHEN cueanexo % 100 != 0 THEN 1 ELSE 0 END) AS total_anexos,
            SUM(CASE WHEN oferta = 'Común - Jardín maternal ' OR oferta = 'Común - Jardín de infantes ' THEN 1 ELSE 0 END) AS total_inicial,
            SUM(CASE WHEN oferta = 'Común - Primaria de 7 años ' THEN 1 ELSE 0 END) AS total_primario,
            SUM(CASE WHEN oferta = 'Adultos - Primaria ' THEN 1 ELSE 0 END) AS total_adultoprim,
            SUM(CASE WHEN oferta = 'Común - Secundaria Completa req. 7 años ' THEN 1 ELSE 0 END) AS total_secundaria,
            SUM(CASE WHEN oferta = 'Adultos - Secundaria Completa' THEN 1 ELSE 0 END) AS total_adultosec,
            SUM(CASE WHEN oferta = 'Adultos - Formación Profesional ' THEN 1 ELSE 0 END) AS total_adultofp,
            SUM(CASE WHEN oferta ILIKE 'Especial%' THEN 1 ELSE 0 END) AS total_especial,
            SUM(CASE WHEN oferta = 'Común - SNU ' THEN 1 ELSE 0 END) AS total_snu,
            SUM(CASE WHEN acronimo = 'BI ANEXO' OR acronimo = 'BI' THEN 1 ELSE 0 END) AS total_biblio,
            SUM(CASE WHEN acronimo = 'CEF' THEN 1 ELSE 0 END) AS total_cef
        FROM 
            v_capa_unica_ofertas
    """

    # Si un departamento ha sido seleccionado, agregar el WHERE
    if selected_regionales:
        query += f" WHERE region_loc='{selected_regionales}'"

    # Ejecutar la consulta
    with connection.cursor() as cursor:
        cursor.execute(query)
        row = cursor.fetchone()

        # Verificar si se obtuvo un resultado
        if row and all(value is not None for value in row):
            datos = {
                'total_ofertas': row[0],
                'total_urbanos': row[1],
                'total_rurales_dispersos': row[2],
                'total_rurales_aglomerados': row[3],
                'total_estatales': row[4],
                'total_privados': row[5],
                'total_soccom': row[6],
                'total_sedes': row[7],
                'total_anexos': row[8],
                'total_inicial': row[9],
                'total_primario': row[10],
                'total_adultoprim': row[11],
                'total_secundaria': row[12],
                'total_adultosec': row[13],
                'total_adultofp': row[14],
                'total_especial': row[15],
                'total_snu': row[16],
                'total_biblio': row[17],
                'total_cef': row[18],
            }
        else:
            # Si no hay resultados, inicializa con ceros
            datos = {
                'total_ofertas': 0,
                'total_urbanos': 0,
                'total_rurales_dispersos': 0,
                'total_rurales_aglomerados': 0,
                'total_estatales': 0,
                'total_privados': 0,
                'total_soccom': 0,
                'total_sedes': 0,
                'total_anexos': 0,
                'total_inicial': 0,
                'total_primario': 0,
                'total_adultoprim': 0,
                'total_secundaria': 0,
                'total_adultosec': 0,
                'total_adultofp': 0,
                'total_especial': 0,
                'total_snu': 0,
                'total_biblio': 0,
                'total_cef': 0,
            }

    # Responder con JSON si es una solicitud AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse(datos)

    context = {
        'regionales': regionales,
        'datos': datos,
    }
    return render(request, 'reportes/listadosestablecreg.html', context)
