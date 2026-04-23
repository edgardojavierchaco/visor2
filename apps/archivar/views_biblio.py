import calendar
import locale
from django.shortcuts import render
from django.http import JsonResponse
from django.db import connection
from apps.biblioteca.models import ServiciosMatBiblio, TipoMaterialBiblio, DestinoFondos, turno, TiposSituacionLaboral
from apps.consultasge.models_padron import CapaUnicaOfertas

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

CARGO_CHOICES = [
    ('BIBLIOTECARIO', 'BIBLIOTECARIO'),
    ('DIRECTOR BIBLIOTECA 1RA', 'DIRECTOR BIBLIOTECA 1RA'),
    ('DIRECTOR BIBLIOTECA 2DA', 'DIRECTOR BIBLIOTECA 2DA'),
    ('DIRECTOR BIBLIOTECA 3RA', 'DIRECTOR BIBLIOTECA 3RA'),
    ('DIRECTOR BIBLIOTECA CENTRAL', 'DIRECTOR BIBLIOTECA CENTRAL'),
    ('VICEDIRECTOR BIBLIOTECA', 'BICEDIRECTOR BIBLIOTECA'),
]

SIT_REVISTA_CHOICES = [
    ('TITULAR', 'TITULAR'),
    ('INTERINO', 'INTERINO'),
    ('SUPLENTE', 'SUPLENTE'),
    ('CONTRATADO', 'CONTRATADO'),
]

servicios_mb=ServiciosMatBiblio.objects.filter(cod_servicio__range=(111,114))
servicios_sr=ServiciosMatBiblio.objects.filter(cod_servicio__range=(211,212))
servicios_srv=ServiciosMatBiblio.objects.filter(cod_servicio__range=(311,313))
servicios_sp=ServiciosMatBiblio.objects.filter(cod_servicio__range=(411,414))
servicios_ip=ServiciosMatBiblio.objects.filter(cod_servicio__range=(511,527))
tipo_mat=TipoMaterialBiblio.objects.all()
fondos=DestinoFondos.objects.all()
servicios_pa=ServiciosMatBiblio.objects.filter(cod_servicio__gt=710)
escuelas_pa = (
    CapaUnicaOfertas.objects
    .filter(acronimo__startswith="BI")
    .values_list("nom_est", flat=True)
    .distinct()
    .order_by("cueanexo")
)

turnos_pa = (
    turno.objects
    .all()
    .values_list("nom_turno", flat=True)
    .distinct()
    .order_by("nom_turno")
)

sitlab_pa=(
    TiposSituacionLaboral.objects
    .all()
    .values_list("tipo_situacion", flat=True)
    .distinct()
    .order_by("tipo_situacion")
)


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
    return render(request, "biblioteca/resultados/servicio_prestamo_gestor.html", {'meses':MESES_ES, 'servicios':servicios_sp, 'regionales':REGIONES})  # Renderiza el template

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
    return render(request, "biblioteca/resultados/material_bibliografico_gestor.html", {'meses':MESES_ES, 'servicios':servicios_mb, 'regionales':REGIONES})  # Renderiza el template

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
    return render(request, "biblioteca/resultados/servicio_referencia_gestor.html", {'meses':MESES_ES, 'servicios':servicios_sr, 'regionales':REGIONES})  # Renderiza el template

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
    return render(request, "biblioteca/resultados/servicio_referencia_virtual_gestor.html", {'meses':MESES_ES, 'servicios':servicios_srv, 'regionales':REGIONES})  # Renderiza el template

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
    return render(request, "biblioteca/resultados/informe_pedagogico_gestor.html", {'meses':MESES_ES, 'servicios':servicios_ip, 'regionales':REGIONES})  # Renderiza el template

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
    return render(request, "biblioteca/resultados/asistencia_usuario_gestor.html", {'meses':MESES_ES, 'usuarios':USUARIOS_CHOICES, 'niveles': NIVELES_CHOICES,'regionales':REGIONES})  # Renderiza el template

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
    return render(request, "biblioteca/resultados/proceso_tecnico_gestor.html", {'meses':MESES_ES, 'procesos':PROCESOS_CHOICES, 'tmat': tipo_mat,'regionales':REGIONES})  # Renderiza el template

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
    return render(request, "biblioteca/resultados/destino_fondos_gestor.html", {'meses': MESES_ES, 'fondos': fondos, 'regionales': REGIONES})

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


##########################
#   PLANILLAS ANEXAS     #
##########################
def planillas_anexas_view(request):    
    return render(request, "biblioteca/resultados/planillas_anexas_gestor.html", {'meses': MESES_ES, 'servicios': servicios_pa, 'regionales': REGIONES})

def filtrar_planillas_anexas(request):
    cueanexo = request.GET.get("cueanexo", "")
    mes = request.GET.get("mes", "")
    anio = request.GET.get("anio", "")    
    servicio_id = request.GET.get("servicio", "")
    regional = request.GET.get("regional", "")
    print(cueanexo, mes, anio, servicio_id, regional)
    
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
    if servicio_id:
        condiciones.append("nom_servicio = %s")
        parametros.append(servicio_id)          
    if regional:
        condiciones.append("region_loc = %s")
        parametros.append(regional)

    sql = """
        SELECT cueanexo, mes, anio, servicio_id, nom_servicio, cantidad, region_loc, localidad
        FROM pem.v_planillas_anexas
        WHERE 1=1
    """
    
    if condiciones:
        sql += " AND " + " AND ".join(condiciones)

    sql_total = """
        SELECT COALESCE(SUM(cantidad), 0) as total_general
        FROM pem.v_planillas_anexas
        WHERE 1=1
    """

    if condiciones:
        sql_total += " AND " + " AND ".join(condiciones)

    with connection.cursor() as cursor:
        cursor.execute(sql, parametros)
        columnas = [col[0] for col in cursor.description]
        datos = [dict(zip(columnas, row)) for row in cursor.fetchall()]

        cursor.execute(sql_total, parametros)
        total_general = cursor.fetchone()
        if total_general is not None:
            total_general = total_general[0]
        else:
            total_general = 0  # Si no hay resultados, asignamos 0
        print("Total general:", total_general)
        
    return JsonResponse({"datos": datos, "total_general": total_general})


##########################
#     INSTITUCIONES      #
##########################
def instituciones_view(request):    
    return render(request, "biblioteca/resultados/instituciones_gestor.html", {'meses': MESES_ES, 'escuela': escuelas_pa, 'regionales': REGIONES})

def filtrar_instituciones(request):
    cueanexo = request.GET.get("cueanexo", "")
    mes = request.GET.get("mes", "")
    anio = request.GET.get("anio", "")    
    escuela = request.GET.get("escuela", "")
    regional = request.GET.get("regional", "")
    print(cueanexo, mes, anio, escuela, regional)
    
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
    if escuela:
        condiciones.append("nom_est = %s")
        parametros.append(escuela)          
    if regional:
        condiciones.append("region_loc = %s")
        parametros.append(regional)

    sql = """
        SELECT cueanexo, mes, anio, escuela, matricula, docentes, matricdisc, etnia, region_loc, localidad
        FROM pem.v_instituciones_servicios
        WHERE 1=1
    """
    
    if condiciones:
        sql += " AND " + " AND ".join(condiciones)

    sql_total = """
        SELECT 
            COALESCE(SUM(matricula), 0)  AS matricula,
            COALESCE(SUM(docentes), 0)   AS docentes,
            COALESCE(SUM(matricdisc), 0)  AS matricdisc,
            COALESCE(SUM(etnia), 0)      AS etnia
        FROM pem.v_instituciones_servicios
        WHERE 1=1
    """

    if condiciones:
        sql_total += " AND " + " AND ".join(condiciones)

    with connection.cursor() as cursor:
        cursor.execute(sql, parametros)
        columnas = [col[0] for col in cursor.description]
        datos = [dict(zip(columnas, row)) for row in cursor.fetchall()]

        cursor.execute(sql_total, parametros)
        row=cursor.fetchone()
        
        total_general = {
            "matricula": row[0] if row else 0,
            "docentes": row[1] if row else 0,
            "matridisc": row[2] if row else 0,
            "etnia": row[3] if row else 0,
        }
        
        
        print("Total general:", total_general)
        
    return JsonResponse({"datos": datos, "total_general": total_general})


##########################
#        AGUAPEY         #
##########################
def aguapey_view(request):    
    return render(request, "biblioteca/resultados/aguapey_gestor.html", {'meses': MESES_ES, 'regionales': REGIONES})

def filtrar_aguapey(request):
    cueanexo = request.GET.get("cueanexo", "")
    mes = request.GET.get("mes", "")
    anio = request.GET.get("anio", "")    
    regional = request.GET.get("regional", "")
    print(cueanexo, mes, anio, regional)
    
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
    if regional:
        condiciones.append("region_loc = %s")
        parametros.append(regional)

    sql = """
        SELECT cueanexo, mes, anio, total_mes, total_base, total_usuarios, porcentaje_uso, region_loc, localidad
        FROM pem.v_aguapey
        WHERE 1=1
    """
    
    if condiciones:
        sql += " AND " + " AND ".join(condiciones)

    sql_total = """
        SELECT 
            COALESCE(SUM(total_mes), 0)  AS mes,
            COALESCE(SUM(total_base), 0)   AS base,
            COALESCE(SUM(total_usuarios), 0)  AS usuarios,
            COALESCE(SUM(porcentaje_uso), 0)      AS porcentaje
        FROM pem.v_aguapey
        WHERE 1=1
    """

    if condiciones:
        sql_total += " AND " + " AND ".join(condiciones)

    with connection.cursor() as cursor:
        cursor.execute(sql, parametros)
        columnas = [col[0] for col in cursor.description]
        datos = [dict(zip(columnas, row)) for row in cursor.fetchall()]

        cursor.execute(sql_total, parametros)
        row=cursor.fetchone()
        
        total_general = {
            "meses": row[0] if row else 0,
            "base": row[1] if row else 0,
            "usuarios": row[2] if row else 0,
            "porcentaje": float(row[3]) if row else 0,
        }
        
        
        print("Total general:", total_general)
        
    return JsonResponse({"datos": datos, "total_general": total_general})



# ===========================
# BIBLIOTECARIOS
# ===========================
def bibliotecarios_view(request):    
    return render(request, "biblioteca/resultados/bibliotecarios_gestor.html", {
        'meses': MESES_ES,
        'regionales': REGIONES,
        'cargos': CARGO_CHOICES,
        'sit_revistas': SIT_REVISTA_CHOICES,
        'turnos': turnos_pa,
        'sitlab': sitlab_pa,
    })


def filtrar_bibliotecarios(request):
    cueanexo = request.GET.get("cueanexo", "")
    mes = request.GET.get("mes", "")
    anio = request.GET.get("anio", "")    
    regional = request.GET.get("regional", "")
    cargos = request.GET.get("cargos","")
    sit_revista = request.GET.get("sit_revista","")
    turnos = request.GET.get("turnos","")
    sit_lab = request.GET.get("sit_lab","")    

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

    if regional:
        condiciones.append("region_loc = %s")
        parametros.append(regional)

    if cargos:
        condiciones.append("cargo = %s")  # ✅ CORRECTO
        parametros.append(cargos)

    if sit_revista:
        condiciones.append("situaciones_revista = %s")  # ✅ CORRECTO
        parametros.append(sit_revista)

    if turnos:
        condiciones.append("turno = %s")  # ✅ CORRECTO
        parametros.append(turnos)

    if sit_lab:
        condiciones.append("situacion_laboral = %s")  # ✅ CORRECTO
        parametros.append(sit_lab)

    sql = """
        SELECT cueanexo, mes, anio, cuil, n_doc, apellidos, nombres,
               cargo, situacion_revista, turno, situacion_laboral,
               estado, antiguedad
        FROM pem.v_bibliotecarios_cue
        WHERE 1=1
    """

    if condiciones:
        sql += " AND " + " AND ".join(condiciones)

    sql_total = """
        SELECT COUNT(*) 
        FROM pem.v_bibliotecarios_cue
        WHERE 1=1
    """

    if condiciones:
        sql_total += " AND " + " AND ".join(condiciones)

    with connection.cursor() as cursor:
        cursor.execute(sql, parametros)
        columnas = [col[0] for col in cursor.description]
        datos = [dict(zip(columnas, row)) for row in cursor.fetchall()]

        cursor.execute(sql_total, parametros)
        row = cursor.fetchone()

        total_general = {
            "total": row[0] if row else 0
        }

    print("Total general:", total_general)
    
    return JsonResponse({
        "datos": datos,
        "total_general": total_general
    })