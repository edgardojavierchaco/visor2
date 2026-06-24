from datetime import timedelta
import json
import csv

from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from apps.login.models_session import SesionUsuario



@login_required
def dashboard_accesos(request):


    # ==============================
    # 📅 FILTROS FECHA
    # ==============================

    desde = request.GET.get("desde","")
    hasta = request.GET.get("hasta","")


    rapido = request.GET.get("rapido")


    hoy = timezone.localdate()



    if rapido == "hoy":

        desde = str(hoy)
        hasta = str(hoy)



    elif rapido == "7":

        desde = str(
            hoy - timedelta(days=7)
        )

        hasta = str(hoy)



    elif rapido == "30":

        desde = str(
            hoy - timedelta(days=30)
        )

        hasta = str(hoy)



    if "T" in desde:
        desde = desde.split("T")[0]


    if "T" in hasta:
        hasta = hasta.split("T")[0]




    sesiones = (
        SesionUsuario.objects
        .select_related(
            "usuario",
            "usuario__nivelacceso"
        )
    )



    if desde:

        sesiones = sesiones.filter(
            creada__date__gte=desde
        )



    if hasta:

        sesiones = sesiones.filter(
            creada__date__lte=hasta
        )




    # ==============================
    # 🟢 CONECTADOS
    # ==============================


    conectados = (
        sesiones
        .filter(activa=True)
        .order_by("-ultima_actividad")
    )




    # ==============================
    # 📌 ULTIMOS ACCESOS
    # ==============================


    ultimos = (
        sesiones
        .order_by("-creada")
        [:200]
    )




    # ==============================
    # ⚠️ SOSPECHOSOS
    # ==============================


    sospechosos=[]


    historial={}


    for s in sesiones.order_by(
        "usuario_id",
        "creada"
    ):


        anterior = historial.get(
            s.usuario_id
        )


        if anterior:

            if anterior.ip != s.ip:


                sospechosos.append({

                    "usuario":
                    s.usuario.username,

                    "motivo":
                    "Cambio de IP",

                    "anterior":
                    anterior.ip,

                    "actual":
                    s.ip

                })


        historial[s.usuario_id]=s




    # ==============================
    # 🗺️ DATOS MAPA
    # ==============================


    puntos=[]


    provincias={}

    dias={}



    for s in ultimos:


        ubicacion=s.ubicacion



        if isinstance(
            ubicacion,
            str
        ):

            try:

                ubicacion=json.loads(
                    ubicacion
                )

            except:

                continue



        if not isinstance(
            ubicacion,
            dict
        ):

            continue



        lat=ubicacion.get("lat")
        lon=ubicacion.get("lon")



        if not lat or not lon:

            continue


        usuario = s.usuario
        
        # ==============================
        # 🔥 DATOS DEL USUARIO
        # ==============================
        
        rol = ""

        if usuario.nivelacceso:

            rol = usuario.nivelacceso.tacceso



        nombre_completo = (
            f"{usuario.apellido}, {usuario.nombres}"
        )


        provincia=ubicacion.get(
            "provincia",
            "Desconocido"
        )



        provincias[provincia]=(
            provincias.get(provincia,0)
            +1
        )



        dia=s.creada.strftime(
            "%d/%m"
        )


        dias[dia]=(
            dias.get(dia,0)
            +1
        )



        puntos.append({

            "username":
            usuario.username,
            
            "nombre":
            nombre_completo,
            
            "rol":
            rol,

            "fecha":
            s.creada.strftime(
                "%d/%m/%Y %H:%M"
            ),


            "ip":
            s.ip,


            "ciudad":
            ubicacion.get(
                "ciudad",
                ""
            ),


            "provincia":
            provincia,


            "lat":
            float(lat),


            "lon":
            float(lon)

        })





    return render(
        request,
        "monitoreo/dashboard.html",
        {

        "desde":desde,

        "hasta":hasta,


        "conectados":
        conectados,


        "ultimos":
        ultimos,


        "sospechosos":
        sospechosos,


        "puntos":
        json.dumps(puntos),


        "grafico_dias":
        json.dumps(dias),


        "grafico_provincias":
        json.dumps(provincias),

        }
    )






@login_required
def exportar_csv(request):


    response=HttpResponse(
        content_type="text/csv"
    )


    response[
        "Content-Disposition"
    ]='attachment; filename="accesos_visoreducativo.csv"'



    writer=csv.writer(response)


    writer.writerow([

        "Usuario",
        "Nombre",
        "Rol",
        "IP",
        "Fecha"

    ])




    for s in SesionUsuario.objects.select_related(
        "usuario",
        "usuario__nivelacceso"
    ):


        writer.writerow([

            s.usuario.username,
            
            f"{s.usuario.apellido}, {s.usuario.nombres}",
            
            s.usuario.nivelacceso.tacceso
            if s.usuario.nivelacceso
            else "",

            s.ip,

            s.creada

        ])




    return response