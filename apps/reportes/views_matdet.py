import psycopg2
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from .db_helpers import conectar_visualizador

def conectar_bd(request):
    try:
        return conectar_visualizador()
    except psycopg2.Error:
        return None
