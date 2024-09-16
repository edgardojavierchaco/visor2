from django.shortcuts import render
from django.db import connection
from django.http import JsonResponse

def consulta_docentes_actividad(request):
    departamentos = []
    resultados = {}
    selected_departamento = request.GET.get('departamento')

    # Obtener los departamentos únicos
    with connection.cursor() as cursor:
        cursor.execute("SELECT DISTINCT departamento FROM v_capa_unica_ofertas")
        departamentos = [row[0] for row in cursor.fetchall()]
        
    funciones = [
        "funcion.visor_docente_actividad_adulto_fp('ra_carga2024')",
        "funcion.visor_docente_actividad_adulto_primaria('ra_carga2024')",
        "funcion.visor_docente_actividad_adulto_secundaria('ra_carga2024')",
        "funcion.visor_docente_actividad_comun_artistica('ra_carga2024')",
        "funcion.visor_docente_actividad_comun_inicial('ra_carga2024')",
        "funcion.visor_docente_actividad_comun_primaria('ra_carga2024')",
        "funcion.visor_docente_actividad_comun_secundaria('ra_carga2024')",
        "funcion.visor_docente_actividad_comun_servicios_complementarios('ra_carga2024')",
        "funcion.visor_docente_actividad_comun_snu('ra_carga2024')",
        
    ]
    
    ambitos = ['Rural Disperso','Rural Aglomerado', 'Urbano']
    sectores = ['Estatal', 'Privado', 'Gestión social/cooperativa']

    # Construir la consulta SQL iterando sobre las funciones, ámbitos y sectores
    for funcion in funciones:
        funcion_limpia = funcion.replace("funcion.visor_docente_actividad_", "").split('(')[0].upper()
        resultados[funcion_limpia] = []  # Crear un diccionario para cada función
        
        for ambito in ambitos:
            for sector in sectores:
                with connection.cursor() as cursor:
                    # Construimos la consulta SQL dinámicamente
                    query = f"""
                        SELECT SUM(total) 
                        FROM {funcion} AS fn
                        LEFT JOIN public.v_capa_unica_ofertas AS vcuo
                        ON fn.cueanexo = vcuo.cueanexo::text
                        WHERE fn.docentes = 'Total docentes en actividad'
                          AND vcuo.sector = '{sector}'
                          AND vcuo.ambito ILIKE '{ambito}'
                    """

                    # Si se ha seleccionado un departamento, agregamos el filtro
                    if selected_departamento:
                        query += f" AND vcuo.departamento = '{selected_departamento}'"

                    cursor.execute(query)
                    total = cursor.fetchone()[0]  # Obtener el resultado de la suma
                    if total is None:
                        total = 0  # Manejar valores nulos

                    # Procesar el nombre de la función para que solo quede la parte después de "funcion.visor_docente_actividad_" y en mayúsculas
                    funcion_limpia = funcion.replace("funcion.visor_docente_actividad_", "").split('(')[0].upper()

                    # Almacena los resultados en la lista
                    resultados[funcion_limpia].append({                        
                        'ambito': ambito,
                        'sector': sector,
                        'total': total
                    })
    
    # Responder con JSON si es una solicitud AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'resultados': resultados})
    
    print(resultados)
    # Renderiza los resultados en la plantilla HTML
    return render(request, 'reportes/listadoactividad.html', {'resultados': resultados, 'departamentos': departamentos})
