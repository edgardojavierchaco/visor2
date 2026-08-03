from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import ensure_csrf_cookie

from .services.permission_service import get_responsable
from .services.supervisor_query_service import SupervisorQueryService
from .services.catalogo_service import CatalogoService

from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages

from apps.supervisor_registro.models import ABMSupervisores

from django.http import HttpResponse
from openpyxl import Workbook

from apps.supervisor_registro.services.permission_service import (
    get_regiones_usuario,
)

# ==========================================================
# DASHBOARD
# ==========================================================

@ensure_csrf_cookie
@login_required
def dashboard(request):

    responsable = get_responsable(request.user)

    context = CatalogoService.contexto(request.user)

    context["responsable"] = responsable

    return render(
        request,
        "supervisores/dashboard.html",
        context,
    )



# ==========================================================
# LISTADO DE SUPERVISORES
# ==========================================================

@login_required
def SupervisoresList(request):


    context = CatalogoService.contexto(
        request.user
    )


    context.update({

        "texto":
            request.GET.get("q",""),

        "region_seleccionada":
            request.GET.get("region",""),

        "situacion_seleccionada":
            request.GET.get("situacion",""),

        "nivel_seleccionado":
            request.GET.get("nivel",""),

    })


    return render(
        request,
        "supervisores/listado_supervisores.html",
        context
    )

# ==========================================================
# DETALLE SUPERVISOR
# ==========================================================

@login_required
def SupervisorDetalle(request, pk):

    supervisor = get_object_or_404(
        ABMSupervisores.objects
        .select_related(
            "usuario"
        )
        .prefetch_related(
            "situaciones",
            "asignaciones_regionales__region",
            "asignaciones_regionales__niveles__nivel",
            "asignaciones_regionales__ofertas",
        ),
        pk=pk
    )


    context = {

        "supervisor": supervisor,

    }


    return render(
        request,
        "supervisores/detalle.html",
        context
    )

# ==========================================================
# EDITAR SUPERVISOR
# ==========================================================

@login_required
def SupervisorEditar(request, pk):

    supervisor = get_object_or_404(
        ABMSupervisores,
        pk=pk
    )


    if request.method == "POST":

        # aquí irá el formulario posteriormente

        messages.success(
            request,
            "Supervisor actualizado correctamente."
        )

        return redirect(
            "supervisor_registro:detalle",
            pk=supervisor.pk
        )


    context = {

        "supervisor": supervisor,

    }


    return render(
        request,
        "supervisores/editar.html",
        context
    )


@login_required
def detalle_supervisor(request, pk):


    supervisor = get_object_or_404(
        ABMSupervisores,
        pk=pk
    )


    asignaciones = (
        supervisor
        .asignaciones_regionales
        .filter(
            activo=True
        )
        .prefetch_related(
            "ofertas",
            "niveles",
            "region"
        )
    )


    escuelas = []


    for asignacion in asignaciones:


        for oferta in asignacion.ofertas.filter(activo=True):

            escuelas.append({

                "region":
                    asignacion.region.nombre,


                "cueanexo":
                    oferta.cueanexo,


                "escuela":
                    oferta.nom_est,


                "oferta":
                    oferta.oferta,


                "acronimo":
                    oferta.acronimo,


            })



    context = {


        "supervisor":

            supervisor,


        "escuelas":

            escuelas,

    }



    return render(
        request,
        "supervisores/detalle.html",
        context
    )


@login_required
def exportar_excel(request):


    # =====================================================
    # QUERY BASE
    # =====================================================

    queryset = SupervisorQueryService.base()



    # =====================================================
    # ALCANCE DEL USUARIO
    # =====================================================

    regiones_usuario = get_regiones_usuario(
        request.user
    )


    queryset = SupervisorQueryService.por_regiones(
        queryset,
        regiones_usuario
    )



    # =====================================================
    # FILTROS
    # =====================================================

    queryset = SupervisorQueryService.filtros(

        queryset,

        q=request.GET.get(
            "q",
            ""
        ).strip(),


        region=request.GET.get(
            "region"
        ),


        situacion=request.GET.get(
            "situacion"
        ),


        nivel=request.GET.get(
            "nivel"
        )

    )



    # =====================================================
    # EXCEL
    # =====================================================

    wb = Workbook()

    ws = wb.active

    ws.title = "Supervisores"



    ws.append([

        "CUIL",

        "Apellido",

        "Nombres",

        "Regional",

        "Nivel",

        "Situación",

        "Email",

        "Telefono",

    ])




    for supervisor in queryset:



        regiones = []

        niveles = []

        situaciones = []



        for asignacion in supervisor.asignaciones_regionales.all():


            regiones.append(
                asignacion.region.nombre
            )



            for nivel in asignacion.niveles.all():

                if nivel.activo:

                    niveles.append(
                        str(nivel.nivel)
                    )



        for situacion in supervisor.situaciones.all():

            if situacion.activo:

                situaciones.append(
                    str(
                        situacion.situacion_revista
                    )
                )



        ws.append([


            supervisor.usuario.username,


            supervisor.usuario.apellido,


            supervisor.usuario.nombres,


            ", ".join(regiones),


            ", ".join(niveles),


            ", ".join(situaciones),


            supervisor.email or "",


            supervisor.telefono or "",


        ])





    # =====================================================
    # RESPUESTA
    # =====================================================

    response = HttpResponse(

        content_type=

        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    )


    response["Content-Disposition"] = (

        'attachment; filename="supervisores_filtrados.xlsx"'

    )



    wb.save(response)



    return response