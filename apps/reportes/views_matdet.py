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

