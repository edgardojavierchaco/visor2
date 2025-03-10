import openpyxl
from django.http import HttpResponse
from django.db import connection
from django.utils.timezone import now

def export_supervisores_excel(request):
    
    # Obtener usuario y fecha actual
    username = request.user.username  # Usuario autenticado
    fecha_actual = now().strftime("%Y%m%d")  # Fecha en formato YYYYMMDD
    filename = f"Supervisores-{username}-{fecha_actual}.xlsx"
    
    # Ejecutar la consulta SQL
    query = """
        SELECT se.*, det.cueanexo, det.nom_est, det.region, det.oferta
        FROM cenpe.supervisores_escuelas AS se
        LEFT JOIN (
            SELECT da.asignacion_id, da.escuela_id, es.cueanexo, es.nom_est, es.region, es.oferta 
            FROM cenpe."Detalle_Asignacion" AS da
            LEFT JOIN cenpe.escuelas_supervisadas AS es
                ON da.escuela_id = es.id
        ) AS det
        ON se.id = det.asignacion_id;
    """
    
    with connection.cursor() as cursor:
        cursor.execute(query)
        columns = [col[0] for col in cursor.description]  # Obtener nombres de columnas
        rows = cursor.fetchall()  # Obtener los datos

    # Crear archivo Excel
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Supervisores"

    # Escribir encabezados
    ws.append(columns)

    # Escribir datos
    for row in rows:
        ws.append(row)

    # Configurar respuesta HTTP para descarga
    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    wb.save(response)
    
    return response
