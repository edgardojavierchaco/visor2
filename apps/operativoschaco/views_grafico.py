from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render
import json

def grafico_examen(request):
    cueanexo_usuario = request.user.username

    query = """
        SELECT 
            alumno.cueanexo AS cueanexo,
            categoria.nombre AS categoria,
            SUM((op->>'puntaje')::numeric) AS puntaje_total
        FROM "Respuesta" respuesta
        JOIN "Examen_Alumno_Cueanexo" examen ON examen.id = respuesta.examen_id
        JOIN "Alumno_Secundaria" alumno ON alumno.id = examen.alumno_id
        JOIN LATERAL jsonb_array_elements(respuesta.opciones_seleccionadas) op ON true
        LEFT JOIN "Opcion" opcion ON opcion.id = (op->>'opcion_id')::integer
        LEFT JOIN "Categoria" categoria ON categoria.id = opcion.categoria_id
        WHERE alumno.cueanexo = %s
        GROUP BY alumno.cueanexo, categoria.nombre
        ORDER BY alumno.cueanexo, categoria.nombre;
    """

    with connection.cursor() as cursor:
        cursor.execute(query, [cueanexo_usuario])
        resultados = cursor.fetchall()
    
    # 🟢 Depuración: Ver resultado antes de convertir
    print("Resultados sin procesar:", resultados)
    
    # Si no hay resultados, mostrar un mensaje
    if not resultados:
        return JsonResponse({'error': 'No se encontraron resultados para el cueanexo especificado'})

    # ✅ Manejar valores None
    resultados_json = json.dumps([
        {
            "cueanexo": r[0],
            "categoria": r[1] if r[1] is not None else "Sin Categoría",
            "puntaje_total": float(r[2])
        }
        for r in resultados
    ])

    return render(request, 'operativoschaco/examen_grafico.html', {
        'resultados_json': resultados_json
    })

