import calendar
import locale
from django.shortcuts import render
from django.http import JsonResponse
from django.db import connection
from .models import ServiciosMatBiblio, TipoMaterialBiblio, DestinoFondos

MESES_ES = [
    (1, "ENERO"), (2, "FEBRERO"), (3, "MARZO"), (4, "ABRIL"), (5, "MAYO"), (6, "JUNIO"),
    (7, "JULIO"), (8, "AGOSTO"), (9, "SEPTIEMBRE"), (10, "OCTUBRE"), (11, "NOVIEMBRE"), (12, "DICIEMBRE")
]

NIVELES_CHOICES=[
    ('INICIAL', 'INICIAL'),
    ('PRIMARIO', 'PRIMARIO'),
    ('SECUNDARIO', 'SECUNDARIO'),
    ('PRIMARIO ADULTO', 'PRIMARIO ADULTO'),
    ('SECUNDARIO ADULTO', 'SECUNDARIO ADULTO'),
    ('SUPERIOR NO UNIVERSITARIO', 'SUPERIOR NO UNIVERSITARIO'),
    ('UNIVERSITARIO', 'UNIVERSITARIO'),
    ('OTROS', 'OTROS'),        
]

USUARIOS_CHOICES=[
    ('ALUMNOS', 'ALUMNOS'),
    ('DOCENTES', 'DOCENTES'),
    ('OTROS', 'OTROS'),        
]

PROCESOS_CHOICES=[
    ('SELLADOS', 'SELLADOS'),
    ('INVENTARIADOS', 'INVENTARIADOS'),
    ('CLASIFICADOS', 'CLASIFICADOS'),     
    ('CATALOGADOS', 'CATALOGADOS'),   
    ('RESTAURADOS', 'RESTAURADOS'),
    ('RESTAURADOS', 'RESTAURADOS'),
    ('BAJAS', 'BAJAS'),
]

servicios_mb=ServiciosMatBiblio.objects.filter(cod_servicio__range=(111,114))
servicios_sr=ServiciosMatBiblio.objects.filter(cod_servicio__range=(211,212))
servicios_srv=ServiciosMatBiblio.objects.filter(cod_servicio__range=(311,313))
servicios_sp=ServiciosMatBiblio.objects.filter(cod_servicio__range=(411,414))
servicios_ip=ServiciosMatBiblio.objects.filter(cod_servicio__range=(511,527))
tipo_mat=TipoMaterialBiblio.objects.all()
fondos=DestinoFondos.objects.all()


""" SERVICIOS_SP = [
    (9, "EQUIPAMIENTO (Computadora, Pendrive, televisor, otros)"),(10,"MATERIAL DIDACTICO Y JUEGOS (Prestados a Sala y Aula)"),
    (11,"ALMACENAMIENTO DE INFORMACION EN DISPOSITIVOS EXTRAIBLES"),(12,"REPROGRAFIA")] """

REGIONES =[
    ("R.E. 1", 'R.E. 1'),
    ("SUB. R.E. 1-A", 'SUB. R.E. 1-A'),
    ("SUB. R.E. 1-B", 'SUB. R.E. 1-B'),
    ("R.E. 2", 'R.E. 2'),
    ("SUB. R.E. 2", 'SUB. R.E. 2'),
    ("R.E. 3", 'R.E. 3'),
    ("SUB. R.E. 3", 'SUB. R.E. 3'),
    ("R.E. 4-A", 'R.E. 4-A'),
    ("R.E. 4-B", 'R.E. 4-B'),
    ("R.E. 5", 'R.E. 5'),
    ("SUB. R.E. 5", 'SUB. R.E. 5'),
    ("R.E. 6", 'R.E. 6'),
    ("R.E. 7", 'R.E. 7'),
    ("R.E. 8-A", 'R.E. 8-A'),
    ("R.E. 8-B", 'R.E. 8-B'),
    ("R.E. 9", 'R.E. 9'),
    ("R.E. 10-A", 'R.E. 10-A'),
    ("R.E. 10-B", 'R.E. 10-B'),
    ("R.E. 10-C", 'R.E. 10-C'),
]

###########################
#   SERVICIOS PRESTAMOS   #
###########################
def servicio_prestamo_view(request):    
    return render(request, "biblioteca/resultados/servicio_prestamo.html", {'meses':MESES_ES, 'servicios':servicios_sp, 'regionales':REGIONES})  # Renderiza el template

def filtrar_servicio_prestamo(request):
    cueanexo = request.GET.get("cueanexo", "")
    mes = request.GET.get("mes", "")
    anio = request.GET.get("anio", "")
    turnos_id = request.GET.get("turnos_id", "")
    servicios_id = request.GET.get("servicio", "")
    regional=request.GET.get("regional","")

    # Armamos la condición para cada filtro y pasamos valores según corresponda
    condiciones = []
    parametros = []

    if cueanexo:
        condiciones.append("cueanexo = %s")
        parametros.append(cueanexo)
    if mes:
        condiciones.append("mes = %s")
        parametros.append(mes)
    if anio:
        condiciones.append("anio = %s")
        parametros.append(anio)
    if turnos_id:
        condiciones.append("turnos_id = %s")
        parametros.append(turnos_id)
    if servicios_id:
        condiciones.append("nom_servicio = %s")
        parametros.append(servicios_id)
    
    if regional:
        condiciones.append("region_loc = %s")
        parametros.append(regional)


    # Construcción dinámica de la parte de la consulta
    sql = """
        SELECT cueanexo, mes, anio, nom_turno, nom_servicio, servicio_id, region_loc, total
        FROM pem.v_servicio_prestamo
        WHERE 1=1
    """

    if condiciones:
        sql += " AND " + " AND ".join(condiciones)

    sql_total = """
        SELECT COALESCE(SUM(total), 0) as total_general
        FROM pem.v_servicio_prestamo
        WHERE 1=1
    """

    if condiciones:
        sql_total += " AND " + " AND ".join(condiciones)

    with connection.cursor() as cursor:
        # Obtener datos filtrados
        cursor.execute(sql, parametros)
        columnas = [col[0] for col in cursor.description]
        datos = [dict(zip(columnas, row)) for row in cursor.fetchall()]

        # Obtener la suma total
        cursor.execute(sql_total, parametros)
        total_general = cursor.fetchone()[0]

    return JsonResponse({"datos": datos, "total_general": total_general})


########################################
#   SERVICIOS MATERIAL BIBLIOGRAFICO   #
########################################
def servicio_matbiblio_view(request):    
    return render(request, "biblioteca/resultados/material_bibliografico.html", {'meses':MESES_ES, 'servicios':servicios_mb, 'regionales':REGIONES})  # Renderiza el template

def filtrar_mat_biblio(request):
    cueanexo = request.GET.get("cueanexo", "")
    mes = request.GET.get("mes", "")
    anio = request.GET.get("anio", "")
    turnos_id = request.GET.get("turnos_id", "")
    servicios_id = request.GET.get("servicio", "")
    regional=request.GET.get("regional","")

    # Armamos la condición para cada filtro y pasamos valores según corresponda
    condiciones = []
    parametros = []

    if cueanexo:
        condiciones.append("cueanexo = %s")
        parametros.append(cueanexo)
    if mes:
        condiciones.append("mes = %s")
        parametros.append(mes)
    if anio:
        condiciones.append("anio = %s")
        parametros.append(anio)
    if turnos_id:
        condiciones.append("turnos_id = %s")
        parametros.append(turnos_id)
    if servicios_id:
        condiciones.append("nom_servicio = %s")
        parametros.append(servicios_id)
    
    if regional:
        condiciones.append("region_loc = %s")
        parametros.append(regional)


    # Construcción dinámica de la parte de la consulta
    sql = """
        SELECT cueanexo, mes, anio, cantidad, servicio_id,nom_servicio,t_material_id, nom_material,turnos_id, nom_turno, region_loc, localidad
        FROM pem.v_material_biblio
        WHERE 1=1
    """

    if condiciones:
        sql += " AND " + " AND ".join(condiciones)

    sql_total = """
        SELECT COALESCE(SUM(cantidad), 0) as total_general
        FROM pem.v_material_biblio
        WHERE 1=1
    """

    if condiciones:
        sql_total += " AND " + " AND ".join(condiciones)

    with connection.cursor() as cursor:
        # Obtener datos filtrados
        cursor.execute(sql, parametros)
        columnas = [col[0] for col in cursor.description]
        datos = [dict(zip(columnas, row)) for row in cursor.fetchall()]

        # Obtener la suma total
        cursor.execute(sql_total, parametros)
        total_general = cursor.fetchone()[0]

    return JsonResponse({"datos": datos, "total_general": total_general})



############################
#   SERVICIOS REFERENCIA   #
############################
def servicio_referencia_view(request):    
    return render(request, "biblioteca/resultados/servicio_referencia.html", {'meses':MESES_ES, 'servicios':servicios_sr, 'regionales':REGIONES})  # Renderiza el template

def filtrar_servicio_referencia(request):
    cueanexo = request.GET.get("cueanexo", "")
    mes = request.GET.get("mes", "")
    anio = request.GET.get("anio", "")
    turnos_id = request.GET.get("turnos_id", "")
    servicios_id = request.GET.get("servicio", "")
    regional=request.GET.get("regional","")

    # Armamos la condición para cada filtro y pasamos valores según corresponda
    condiciones = []
    parametros = []

    if cueanexo:
        condiciones.append("cueanexo = %s")
        parametros.append(cueanexo)
    if mes:
        condiciones.append("mes = %s")
        parametros.append(mes)
    if anio:
        condiciones.append("anio = %s")
        parametros.append(anio)
    if turnos_id:
        condiciones.append("turnos_id = %s")
        parametros.append(turnos_id)
    if servicios_id:
        condiciones.append("nom_servicio = %s")
        parametros.append(servicios_id)
    
    if regional:
        condiciones.append("region_loc = %s")
        parametros.append(regional)


    # Construcción dinámica de la parte de la consulta
    sql = """
        SELECT cueanexo, mes, anio, varones, total, turnos_id,nom_turno, servicio_id, nom_servicio, region_loc, localidad
        FROM pem.v_servicio_referencia
        WHERE 1=1
    """

    if condiciones:
        sql += " AND " + " AND ".join(condiciones)

    sql_total = """
        SELECT 
            COALESCE(SUM(total), 0) as total_general,
            COALESCE(SUM(varones), 0) as total_varones
        FROM pem.v_servicio_referencia
        WHERE 1=1
    """

    if condiciones:
        sql_total += " AND " + " AND ".join(condiciones)

    with connection.cursor() as cursor:
        # Obtener datos filtrados
        cursor.execute(sql, parametros)
        columnas = [col[0] for col in cursor.description]
        datos = [dict(zip(columnas, row)) for row in cursor.fetchall()]

        # Obtener la suma total
        cursor.execute(sql_total, parametros)
        total_general, total_varones = cursor.fetchone()

    return JsonResponse({"datos": datos, "total_general": total_general, "total_varones":total_varones})


###################################
#   SERVICIOS REFERENCIA VIRTUAL  #
###################################
def servicio_referencia_virtual_view(request):    
    return render(request, "biblioteca/resultados/servicio_referencia_virtual.html", {'meses':MESES_ES, 'servicios':servicios_srv, 'regionales':REGIONES})  # Renderiza el template

def filtrar_servicio_referencia_virtual(request):
    cueanexo = request.GET.get("cueanexo", "")
    mes = request.GET.get("mes", "")
    anio = request.GET.get("anio", "")
    turnos_id = request.GET.get("turnos_id", "")
    servicios_id = request.GET.get("servicio", "")
    regional=request.GET.get("regional","")

    # Armamos la condición para cada filtro y pasamos valores según corresponda
    condiciones = []
    parametros = []

    if cueanexo:
        condiciones.append("cueanexo = %s")
        parametros.append(cueanexo)
    if mes:
        condiciones.append("mes = %s")
        parametros.append(mes)
    if anio:
        condiciones.append("anio = %s")
        parametros.append(anio)
    if turnos_id:
        condiciones.append("turnos_id = %s")
        parametros.append(turnos_id)
    if servicios_id:
        condiciones.append("nom_servicio = %s")
        parametros.append(servicios_id)
    
    if regional:
        condiciones.append("region_loc = %s")
        parametros.append(regional)


    # Construcción dinámica de la parte de la consulta
    sql = """
        SELECT cueanexo, mes, anio, varones, total, turnos_id,nom_turno, servicio_id, nom_servicio, region_loc, localidad
        FROM pem.v_servicio_referencia_virtual
        WHERE 1=1
    """

    if condiciones:
        sql += " AND " + " AND ".join(condiciones)

    sql_total = """
        SELECT 
            COALESCE(SUM(total), 0) as total_general,
            COALESCE(SUM(varones), 0) as total_varones
        FROM pem.v_servicio_referencia_virtual
        WHERE 1=1
    """

    if condiciones:
        sql_total += " AND " + " AND ".join(condiciones)

    with connection.cursor() as cursor:
        # Obtener datos filtrados
        cursor.execute(sql, parametros)
        columnas = [col[0] for col in cursor.description]
        datos = [dict(zip(columnas, row)) for row in cursor.fetchall()]

        # Obtener la suma total
        cursor.execute(sql_total, parametros)
        total_general, total_varones = cursor.fetchone()
        

    return JsonResponse({"datos": datos, "total_general": total_general, "total_varones":total_varones})



##########################
#   INFORME PEDAGÓGICO   #
##########################
def informe_pedagogico_view(request):    
    return render(request, "biblioteca/resultados/informe_pedagogico.html", {'meses':MESES_ES, 'servicios':servicios_ip, 'regionales':REGIONES})  # Renderiza el template

def filtrar_informe_pedagogico(request):
    cueanexo = request.GET.get("cueanexo", "")
    mes = request.GET.get("mes", "")
    anio = request.GET.get("anio", "")    
    servicios_id = request.GET.get("servicio", "")
    regional=request.GET.get("regional","")

    # Armamos la condición para cada filtro y pasamos valores según corresponda
    condiciones = []
    parametros = []

    if cueanexo:
        condiciones.append("cueanexo = %s")
        parametros.append(cueanexo)
    if mes:
        condiciones.append("mes = %s")
        parametros.append(mes)
    if anio:
        condiciones.append("anio = %s")
        parametros.append(anio)
    
    if servicios_id:
        condiciones.append("nom_servicio = %s")
        parametros.append(servicios_id)
    
    if regional:
        condiciones.append("region_loc = %s")
        parametros.append(regional)


    # Construcción dinámica de la parte de la consulta
    sql = """
        SELECT cueanexo, mes, anio, varones, total, servicio_id, nom_servicio, region_loc, localidad
        FROM pem.v_informe_pedagogico
        WHERE 1=1
    """

    if condiciones:
        sql += " AND " + " AND ".join(condiciones)

    sql_total = """
        SELECT 
            COALESCE(SUM(total), 0) as total_general,
            COALESCE(SUM(varones), 0) as total_varones
        FROM pem.v_informe_pedagogico
        WHERE 1=1
    """

    if condiciones:
        sql_total += " AND " + " AND ".join(condiciones)

    with connection.cursor() as cursor:
        # Obtener datos filtrados
        cursor.execute(sql, parametros)
        columnas = [col[0] for col in cursor.description]
        datos = [dict(zip(columnas, row)) for row in cursor.fetchall()]

        # Obtener la suma total
        cursor.execute(sql_total, parametros)
        total_general, total_varones = cursor.fetchone()
        

    return JsonResponse({"datos": datos, "total_general": total_general, "total_varones":total_varones})



##########################
#   ASISTENCIA USUARIO   #
##########################
def asistencia_usuario_view(request):    
    return render(request, "biblioteca/resultados/asistencia_usuario.html", {'meses':MESES_ES, 'usuarios':USUARIOS_CHOICES, 'niveles': NIVELES_CHOICES,'regionales':REGIONES})  # Renderiza el template

def filtrar_asistencia_usuario(request):
    cueanexo = request.GET.get("cueanexo", "")
    mes = request.GET.get("mes", "")
    anio = request.GET.get("anio", "")    
    nivel_id = request.GET.get("nivel","")
    usuario_id = request.GET.get("usuario", "")
    regional=request.GET.get("regional","")

    # Armamos la condición para cada filtro y pasamos valores según corresponda
    condiciones = []
    parametros = []

    if cueanexo:
        condiciones.append("cueanexo = %s")
        parametros.append(cueanexo)
    if mes:
        condiciones.append("mes = %s")
        parametros.append(mes)
    if anio:
        condiciones.append("anio = %s")
        parametros.append(anio)       
    if nivel_id:
        condiciones.append("nivel = %s")
        parametros.append(nivel_id)        
    if usuario_id:
        condiciones.append("usuario = %s")
        parametros.append(usuario_id)    
    if regional:
        condiciones.append("region_loc = %s")
        parametros.append(regional)


    # Construcción dinámica de la parte de la consulta
    sql = """
        SELECT cueanexo, mes, anio, nivel, usuario, varones, total, region_loc, localidad
        FROM pem.v_asistencia_usuario
        WHERE 1=1
    """

    if condiciones:
        sql += " AND " + " AND ".join(condiciones)

    sql_total = """
        SELECT 
            COALESCE(SUM(total), 0) as total_general,
            COALESCE(SUM(varones), 0) as total_varones
        FROM pem.v_asistencia_usuario
        WHERE 1=1
    """

    if condiciones:
        sql_total += " AND " + " AND ".join(condiciones)

    with connection.cursor() as cursor:
        # Obtener datos filtrados
        cursor.execute(sql, parametros)
        columnas = [col[0] for col in cursor.description]
        datos = [dict(zip(columnas, row)) for row in cursor.fetchall()]

        # Obtener la suma total
        cursor.execute(sql_total, parametros)
        total_general, total_varones = cursor.fetchone()
        

    return JsonResponse({"datos": datos, "total_general": total_general, "total_varones":total_varones})


##########################
#     PROCESO TÉCNICO    #
##########################
def proceso_tecnico_view(request):    
    return render(request, "biblioteca/resultados/proceso_tecnico.html", {'meses':MESES_ES, 'procesos':PROCESOS_CHOICES, 'tmat': tipo_mat,'regionales':REGIONES})  # Renderiza el template

def filtrar_proceso_tecnico(request):
    cueanexo = request.GET.get("cueanexo", "")
    mes = request.GET.get("mes", "")
    anio = request.GET.get("anio", "")    
    procesos_id = request.GET.get("procesos","")
    material_id = request.GET.get("materiales", "")
    regional=request.GET.get("regional","")

    # Armamos la condición para cada filtro y pasamos valores según corresponda
    condiciones = []
    parametros = []

    if cueanexo:
        condiciones.append("cueanexo = %s")
        parametros.append(cueanexo)
    if mes:
        condiciones.append("mes = %s")
        parametros.append(mes)
    if anio:
        condiciones.append("anio = %s")
        parametros.append(anio)       
    if procesos_id:
        condiciones.append("procesos = %s")
        parametros.append(procesos_id)        
    if material_id:
        condiciones.append("material_id = %s")
        parametros.append(material_id)    
    if regional:
        condiciones.append("region_loc = %s")
        parametros.append(regional)


    # Construcción dinámica de la parte de la consulta
    sql = """
        SELECT cueanexo, mes, anio, procesos, total, material_id, region_loc, localidad
        FROM pem.v_proceso_tecnico
        WHERE 1=1
    """

    if condiciones:
        sql += " AND " + " AND ".join(condiciones)

    sql_total = """
        SELECT 
            COALESCE(SUM(total), 0) as total_general
        FROM pem.v_proceso_tecnico
        WHERE 1=1
    """

    if condiciones:
        sql_total += " AND " + " AND ".join(condiciones)

    with connection.cursor() as cursor:
        # Obtener datos filtrados
        cursor.execute(sql, parametros)
        columnas = [col[0] for col in cursor.description]
        datos = [dict(zip(columnas, row)) for row in cursor.fetchall()]

        # Obtener la suma total
        cursor.execute(sql_total, parametros)
        total_general = cursor.fetchone()[0]
        

    return JsonResponse({"datos": datos, "total_general": total_general})


##########################
#   DESTINO DE FONDOS    #
##########################
def destino_fondos_view(request):    
    return render(request, "biblioteca/resultados/destino_fondos.html", {'meses': MESES_ES, 'fondos': fondos, 'regionales': REGIONES})

def filtrar_destino_fondos(request):
    cueanexo = request.GET.get("cueanexo", "")
    mes = request.GET.get("mes", "")
    anio = request.GET.get("anio", "")    
    destino = request.GET.get("destino", "")
    regional = request.GET.get("regional", "")

    condiciones = []
    parametros = []

    if cueanexo:
        condiciones.append("cueanexo = %s")
        parametros.append(cueanexo)
    if mes:
        condiciones.append("mes = %s")
        parametros.append(mes)
    if anio:
        condiciones.append("anio = %s")
        parametros.append(anio)       
    if destino:
        condiciones.append("nom_fondo = %s")
        parametros.append(destino)          
    if regional:
        condiciones.append("region_loc = %s")
        parametros.append(regional)

    sql = """
        SELECT cueanexo, mes, anio, descripcion, destino_id, nom_fondo, region_loc, localidad
        FROM pem.v_registro_destino_fondos
        WHERE 1=1
    """
    
    if condiciones:
        sql += " AND " + " AND ".join(condiciones)

    sql_total = """
        SELECT COALESCE(COUNT(DISTINCT(cueanexo)), 0) as total_cueanexos
        FROM pem.v_registro_destino_fondos
        WHERE 1=1
    """

    if condiciones:
        sql_total += " AND " + " AND ".join(condiciones)

    with connection.cursor() as cursor:
        cursor.execute(sql, parametros)
        columnas = [col[0] for col in cursor.description]
        datos = [dict(zip(columnas, row)) for row in cursor.fetchall()]

        cursor.execute(sql_total, parametros)
        total_cueanexos = cursor.fetchone()
        if total_cueanexos is not None:
            total_cueanexos = total_cueanexos[0]
        else:
            total_cueanexos = 0  # Si no hay resultados, asignamos 0
        print("Total Cueanexos:", total_cueanexos)
        
    return JsonResponse({"datos": datos, "total_general": total_cueanexos})