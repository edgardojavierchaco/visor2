from django.shortcuts import render
from .models import Pregunta, Opcion

def cargar_examen(request):
    # Obtener todas las preguntas con sus opciones
    preguntas = Pregunta.objects.all()
    
    # Crear un diccionario para almacenar las preguntas con sus opciones
    preguntas_con_opciones = {}
    
    for pregunta in preguntas:
        # Obtener las opciones asociadas a cada pregunta
        opciones = Opcion.objects.filter(pregunta=pregunta)
        
        # Almacenar las opciones de cada pregunta en el diccionario
        preguntas_con_opciones[pregunta] = opciones
    
    # Pasar las preguntas con sus opciones al template
    return render(request, 'operachaco/examen.html', {'preguntas_con_opciones': preguntas_con_opciones})
