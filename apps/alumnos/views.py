from django.shortcuts import render

# Create your views here.

import requests
from bs4 import BeautifulSoup
from django.http import JsonResponse

def obtener_nombre_cuit_view(request):
    # Obtener el CUIT desde los parámetros de la URL
    cuit = request.GET.get("cuit")
    
    if not cuit:
        return JsonResponse({"error": "Falta el CUIT en la solicitud"}, status=400)

    nombre = obtener_nombre_cuit(cuit)
    
    if nombre == "Nombre no encontrado":
        return JsonResponse({"error": "No se encontró el nombre para este CUIT"}, status=404)
    
    return JsonResponse({"cuit": cuit, "nombre": nombre})

def obtener_nombre_cuit(cuit):
    url = f"https://www.cuitonline.com/search.php?q={cuit}"
    headers = {"User-Agent": "Mozilla/5.0"}

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")

        # Buscar el nombre en la etiqueta <h2> con clase 'denominacion'
        nombre = soup.find("h2", class_="denominacion")

        if nombre:
            return nombre.text.strip()  # Devuelve el texto del nombre encontrado
        else:
            return "Nombre no encontrado"

    return f"Error en la solicitud: {response.status_code}"
