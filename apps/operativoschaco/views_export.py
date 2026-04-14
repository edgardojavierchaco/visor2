import openpyxl
from django.http import HttpResponse
from .models import ExamenAlumnoCueanexoL, Categoria, Respuesta, Opcion

def exportar_excel(request):
    # Crear el libro de Excel y la hoja de trabajo
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Resultados de Examen"

    # Definir las columnas
    columnas = ["DNI", "Apellidos", "Nombres"]  # Datos del alumno
    
    # Obtener las categorías excluyendo 'M1' a 'M14'
    categorias = Categoria.objects.exclude(nombre__in=[
        'M1', 'M2', 'M3', 'M4', 'M5', 'M6', 'M7', 'M8',
        'M9', 'M10', 'M11', 'M12', 'M13', 'M14'
    ])
    
    nombres_categorias = [cat.nombre for cat in categorias]
    columnas.extend(nombres_categorias)  # Agregar categorías como columnas
    columnas.append("Total Sin Categoría")

    # Escribir la primera fila con los nombres de las columnas
    sheet.append(columnas)

    # Obtener los exámenes del usuario actual
    director = request.user.username
    examenes = ExamenAlumnoCueanexoL.objects.filter(alumno__cueanexo=director)

    for examen in examenes:
        respuestas = Respuesta.objects.filter(examen=examen)
        totales_por_categoria = {cat.nombre: 0 for cat in categorias}
        total_sin_categoria = 0

        for respuesta in respuestas:
            opciones_seleccionadas = respuesta.opciones_seleccionadas
            if not opciones_seleccionadas:
                continue

            for opcion in opciones_seleccionadas:
                opcion_id = opcion.get('opcion_id')
                if not opcion_id:
                    continue

                try:
                    opcion_obj = Opcion.objects.get(id=opcion_id)
                    if opcion_obj.categoria:
                        totales_por_categoria[opcion_obj.categoria.nombre] += opcion_obj.puntaje
                    else:
                        total_sin_categoria += opcion_obj.puntaje
                except Opcion.DoesNotExist:
                    continue

        # Crear la fila de datos para cada alumno
        fila = [
            examen.alumno.dni,
            examen.alumno.apellidos,
            examen.alumno.nombres
        ]

        # Agregar puntajes de cada categoría
        for categoria in nombres_categorias:
            fila.append(totales_por_categoria.get(categoria, 0))

        # Agregar el total sin categoría
        fila.append(total_sin_categoria)

        # Escribir la fila en la hoja
        sheet.append(fila)

    # Configurar la respuesta HTTP para descargar el archivo
    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    username = request.user.username
    response["Content-Disposition"] = f'attachment; filename="resultados_examen_lengua_{username}.xlsx"'

    workbook.save(response)

    return response
