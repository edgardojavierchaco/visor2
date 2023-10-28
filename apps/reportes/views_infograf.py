import psycopg2
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

# Función para conectar a la base de datos
def conectar_bd(relevamiento):
    try:
        connection = psycopg2.connect(
            host='relevamientoanual.com.ar',
            user='visualizador',
            password='Estadisticas23',
            database=relevamiento
        )
        return connection
    except psycopg2.Error as e:
        # Manejar el error de conexión
        return None

# Vista para mostrar el formulario de filtrado de infografía
def filtrado_infografia(request):
    return render(request, 'reportes/filter_infografia.html')

#####################################################################
#                    PARA REPORTE DE INFOGRAFÍA                     #
#####################################################################

# Vista para procesar los datos del formulario de filtrado de la infografía
@csrf_exempt
def filter_data_infografia(request):
    if request.method == 'POST':
        cueanexo = request.POST.get('Cueanexo')
        ambito = request.POST.get('Ambito')
        sector = request.POST.get('Sector')
        region = request.POST.get('Region')
        departamento = request.POST.get('Departamento')
        localidad = request.POST.get('Localidad')
        relevamiento = request.POST.get('Relevamiento')

        # Asignar un valor descriptivo a la opción de relevamiento seleccionado
        opciones_relevamiento={
            'ra_carga2011':'Relevamiento 2011',
            'ra_carga2012':'Relevamiento 2012',
            'ra_carga2013':'Relevamiento 2013',
            'ra_carga2014':'Relevamiento 2014',
            'ra_carga2015':'Relevamiento 2015',
            'ra_carga2016':'Relevamiento 2016',
            'ra_carga2017':'Relevamiento 2017',
            'ra_carga2018':'Relevamiento 2018',
            'ra_carga2019':'Relevamiento 2019',
            'ra_carga2020':'Relevamiento 2020',
            'ra_carga2021':'Relevamiento 2021',
            'ra_carga2022':'Relevamiento 2022',
            'ra_carga2023':'Relevamiento 2023',
        }
        nrelevamiento=opciones_relevamiento.get(relevamiento,'Relevamiento 2022')
        
        # Conectarse a la base de datos
        connection = conectar_bd(relevamiento)
        if not connection:
            return render(request, 'error_conexion.html')

        cursor = connection.cursor()
 