import openpyxl
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from .models import ExamenAlumnoCueanexoM
from .views_listmatem import ExamenAlumnoCueanexoMatListView

@login_required
def exportar_excel_matematica_lista(request):
    # Filtrar exámenes del usuario logueado
    director = request.user.username
    examenes = ExamenAlumnoCueanexoM.objects.filter(alumno__cueanexo=director)

    # Calcular los totales usando la lógica ya hecha
    lista_view = ExamenAlumnoCueanexoMatListView()
    lista_view.request = request  # Necesario para que use `request.user`
    alumnos_totales = lista_view.calcular_totales(examenes)

    # Crear archivo Excel
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Listado Examen Matemática"

    # Encabezados
    sheet.append(["DNI", "Apellidos", "Nombres", "Aritmética", "Geometría", "Estadística", "Total General"])

    for alumno in alumnos_totales:
        datos = alumno['alumno']
        fila = [
            datos["dni"],
            datos["apellidos"],
            datos["nombres"],
            alumno['subtotales']['Aritmética'],
            alumno['subtotales']['Geometría'],
            alumno['subtotales']['Estadística'],
            alumno['total_general']
        ]
        sheet.append(fila)

    # Preparar respuesta HTTP
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = f'attachment; filename="listado_matematica_{director}.xlsx"'
    workbook.save(response)
    return response
