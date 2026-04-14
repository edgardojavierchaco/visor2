from django.http import HttpResponse
from openpyxl import Workbook
from .models import ExportarAlumnoBilingueConId
from datetime import datetime

def export_alumnos_bilingues_xlsx(request):
    wb = Workbook()
    ws = wb.active
    ws.title = "Alumnos Bilingües Pueblos Originarios"

    # Encabezados
    headers = [
        "ID", "Cueanexo", "Nombre", "Sector", "Ámbito", "Región",
        "Localidad", "Departamento", "Nivel", "Curso", "Sección", "Lengua",
        "Varones", "Mujeres"
    ]
    ws.append(headers)

    # Datos
    for alumno in ExportarAlumnoBilingueConId.objects.all():
        ws.append([
            alumno.id, alumno.cueanexo, alumno.nom_est, alumno.sector,
            alumno.ambito, alumno.region_loc, alumno.localidad,
            alumno.departamento, alumno.nivel, alumno.curso,
            alumno.seccion, alumno.lengua, alumno.varones, alumno.mujeres
        ])

    # Fecha actual para el nombre del archivo
    fecha = datetime.now().strftime('%Y-%m-%d')
    filename = f"alumnos_bilingües_pueblos_originarios_{fecha}.xlsx"

    # Preparar respuesta
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename={filename}'
    wb.save(response)
    return response