from django.shortcuts import render
from django.db import connection
from django.http import JsonResponse

def consulta_ofertas(request):
    """
    Consulta las ofertas educativas por departamento.
    Devuelve JSON si es AJAX y renderiza dashboard si no.
    """

    selected_departamento = request.GET.get('departamento')
    departamentos = []

    # Obtener departamentos únicos
    with connection.cursor() as cursor:
        cursor.execute("SELECT DISTINCT departamento FROM v_capa_unica_ofertas")
        departamentos = [row[0] for row in cursor.fetchall()]

    # Consulta principal
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
            SUM(CASE WHEN oferta ILIKE 'Común - Jardín%' THEN 1 ELSE 0 END) AS total_inicial,
            SUM(CASE WHEN oferta ILIKE 'Común - Primaria%' THEN 1 ELSE 0 END) AS total_primario,
            SUM(CASE WHEN oferta ILIKE 'Adultos - Primaria%' THEN 1 ELSE 0 END) AS total_adultoprim,
            SUM(CASE WHEN oferta ILIKE 'Común - Secundaria%' THEN 1 ELSE 0 END) AS total_secundaria,
            SUM(CASE WHEN oferta ILIKE 'Adultos - Secundaria%' THEN 1 ELSE 0 END) AS total_adultosec,
            SUM(CASE WHEN oferta ILIKE 'Adultos - Formación Profesional%' THEN 1 ELSE 0 END) AS total_adultofp,
            SUM(CASE WHEN oferta ILIKE 'Especial%' THEN 1 ELSE 0 END) AS total_especial,
            SUM(CASE WHEN oferta ILIKE 'Común - SNU%' THEN 1 ELSE 0 END) AS total_snu,
            SUM(CASE WHEN acronimo ILIKE 'BI%' THEN 1 ELSE 0 END) AS total_biblio,
            SUM(CASE WHEN acronimo ILIKE 'CEF%' THEN 1 ELSE 0 END) AS total_cef
        FROM v_capa_unica_ofertas
    """
    if selected_departamento:
        query += f" WHERE departamento='{selected_departamento}'"

    with connection.cursor() as cursor:
        cursor.execute(query)
        row = cursor.fetchone()

    keys = ['total_ofertas','total_urbanos','total_rurales_dispersos','total_rurales_aglomerados',
            'total_estatales','total_privados','total_soccom','total_sedes','total_anexos',
            'total_inicial','total_primario','total_adultoprim','total_secundaria',
            'total_adultosec','total_adultofp','total_especial','total_snu','total_biblio','total_cef']

    datos = dict(zip(keys, row if row else [0]*len(keys)))

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse(datos)

    return render(request, 'reportes/listadosestablecimientos.html', {'departamentos': departamentos, 'datos': datos})


def consulta_ofertas_reg(request):
    """
    Consulta las ofertas educativas por región y devuelve JSON si es AJAX.
    """
    selected_region = request.GET.get('region')

    # Obtener regiones únicas
    with connection.cursor() as cursor:
        cursor.execute("SELECT DISTINCT region_loc FROM v_capa_unica_ofertas")
        regionales = [row[0] for row in cursor.fetchall()]

    # Consulta principal
    query = """
        SELECT 
            COUNT(*) AS total_ofertas,
            SUM(CASE WHEN ambito='Urbano' THEN 1 ELSE 0 END) AS total_urbanos,
            SUM(CASE WHEN ambito='Rural Disperso' THEN 1 ELSE 0 END) AS total_rurales_dispersos,
            SUM(CASE WHEN ambito='Rural Aglomerado' THEN 1 ELSE 0 END) AS total_rurales_aglomerados,
            SUM(CASE WHEN sector='Estatal' THEN 1 ELSE 0 END) AS total_estatales,
            SUM(CASE WHEN sector='Privado' THEN 1 ELSE 0 END) AS total_privados,
            SUM(CASE WHEN sector='Gestión social/cooperativa' THEN 1 ELSE 0 END) AS total_soccom,
            SUM(CASE WHEN oferta ILIKE 'Común - Jardín%' THEN 1 ELSE 0 END) AS total_inicial,
            SUM(CASE WHEN oferta ILIKE 'Común - Primaria%' THEN 1 ELSE 0 END) AS total_primario,
            SUM(CASE WHEN oferta ILIKE 'Común - Secundaria%' THEN 1 ELSE 0 END) AS total_secundaria,
            SUM(CASE WHEN oferta ILIKE 'Adultos - Primaria%' THEN 1 ELSE 0 END) AS total_adultoprim,
            SUM(CASE WHEN oferta ILIKE 'Adultos - Secundaria%' THEN 1 ELSE 0 END) AS total_adultosec,
            SUM(CASE WHEN oferta ILIKE 'Adultos - Formación Profesional%' THEN 1 ELSE 0 END) AS total_adultofp,
            SUM(CASE WHEN oferta ILIKE 'Especial%' THEN 1 ELSE 0 END) AS total_especial,
            SUM(CASE WHEN acronimo ILIKE 'BI%' THEN 1 ELSE 0 END) AS total_biblio,
            SUM(CASE WHEN acronimo ILIKE 'CEF%' THEN 1 ELSE 0 END) AS total_cef
        FROM v_capa_unica_ofertas
    """
    if selected_region:
        query += f" WHERE region_loc='{selected_region}'"

    with connection.cursor() as cursor:
        cursor.execute(query)
        row = cursor.fetchone()

    keys = ['total_ofertas','total_urbanos','total_rurales_dispersos','total_rurales_aglomerados',
            'total_estatales','total_privados','total_soccom','total_inicial','total_primario',
            'total_secundaria','total_adultoprim','total_adultosec','total_adultofp','total_especial',
            'total_biblio','total_cef']

    datos = dict(zip(keys, row if row else [0]*len(keys)))

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse(datos)

    return render(request, 'reportes/listadosestablecreg.html', {'regionales': regionales, 'datos': datos})