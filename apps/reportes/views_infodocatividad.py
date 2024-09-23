from django.shortcuts import render
from django.db import connection
from django.http import JsonResponse

def consulta_docentes_actividad(request):
    departamentos = []
    resultados = {}
    total_general = 0
    selected_departamento = request.GET.get('departamento')

    # Obtener los departamentos únicos
    with connection.cursor() as cursor:
        cursor.execute("SELECT DISTINCT departamento FROM v_capa_unica_ofertas")
        departamentos = [row[0] for row in cursor.fetchall()]

    # Consulta SQL dependiendo del departamento seleccionado
    with connection.cursor() as cursor:        
        query = """
                SELECT funcion, ambito, sector, departamento, total
                FROM public.resultados_docentes
                WHERE departamento = %s
            """
        cursor.execute(query, [selected_departamento])

        filas = cursor.fetchall()
        print("Filas obtenidas:", filas)

        # Recorrer las filas y guardar los resultados
        for fila in filas:
            if len(fila) == 4:  # Para el caso de todos los departamentos
                funcion, ambito, sector, total = fila
                departamento = '-- Todos los departamentos --'  # Asigna un valor genérico para el departamento
            elif len(fila) == 5:  # Para el caso de un departamento específico
                funcion, ambito, sector, departamento, total = fila
            else:
                raise ValueError("Unexpected number of columns in the result")

            if funcion not in resultados:
                resultados[funcion] = []
            resultados[funcion].append({
                'ambito': ambito,
                'sector': sector,
                'departamento': departamento,
                'total': total
            })

            # Calcular la suma total general
            total_general += total

    # Definir la lista de colores en la vista
    colores = ['#3498db', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b6']
    
    # Responder con JSON si es una solicitud AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'resultados': resultados})
    
    print(resultados, departamentos, total_general)
    
    # Renderiza los resultados en la plantilla HTML
    return render(request, 'reportes/listadoactividad.html', {
        'resultados': resultados, 
        'departamentos': departamentos,
        'colores': colores,
        'total_general': total_general
    })
