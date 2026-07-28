import json
import logging
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from .db_helpers import conectar_visualizador


# Configuración básica de logging
logger = logging.getLogger(__name__)

def obtener_tablas(request):
    try:
        logger.info("Iniciando conexión a la base de datos...")

        connection = conectar_visualizador()
        cursor = connection.cursor()
        
        # Ejecuta la consulta para obtener las tablas del esquema 'public'
        logger.info("Ejecutando consulta para obtener tablas...")
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema='public';
        """)
        
        # Obtiene los resultados de la consulta
        tablas = [row[0] for row in cursor.fetchall()]
        logger.info(f"Tablas obtenidas: {tablas}")
        
        if tablas:
            logger.info("Tablas encontradas, enviando respuesta...")
            return JsonResponse({'tablas': tablas})
        else:
            logger.warning("No se encontraron tablas.")
            return JsonResponse({'tablas': []})

    except Exception as e:
        logger.error(f"Error al obtener las tablas: {e}")
        return JsonResponse({'error': 'Hubo un error al obtener las tablas'}, status=500)
    
    finally:
        try:
            if cursor:
                cursor.close()
                logger.info("Cursor cerrado.")
            if connection:
                connection.close()
                logger.info("Conexión cerrada.")
        except Exception as close_error:
            logger.error(f"Error al cerrar recursos: {close_error}")

def sql_builder(request):
    return render(request, 'reportes/blockly_interface.html')


@csrf_exempt
def ejecutar_sql(request):
    if request.method == 'GET':
        try:
            body = json.loads(request.body)
            query = body.get('query')

            connection = conectar_visualizador()
            cursor = connection.cursor()

            # Ejecutar la consulta SQL generada
            cursor.execute(query)
            resultado = cursor.fetchall()

            # Devolver los resultados
            return JsonResponse({"resultado": resultado})
        except Exception as e:
            logger.error(f"Error al ejecutar la consulta SQL: {str(e)}")
            return JsonResponse({"error": "Error al ejecutar la consulta SQL"}, status=500)
