import psycopg2
import os
import dotenv
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

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

