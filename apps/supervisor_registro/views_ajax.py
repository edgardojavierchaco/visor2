from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.urls import reverse

from apps.supervisor_registro.services.permission_service import (
    get_regiones_usuario,
)

from apps.supervisor_registro.services.supervisor_query_service import (
    SupervisorQueryService,
)




@login_required
def supervisores_datatable(request):
    
    print(">>> ENTRO A supervisores_datatable")

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


    print(
        "REGIONES USUARIO:",
        regiones_usuario
    )

    print(
        "TOTAL BASE:",
        SupervisorQueryService.base().count()
    )

    print(
        "TOTAL DESPUES REGION:",
        queryset.count()
    )
    
    records_total = queryset.count()



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



    records_filtered = queryset.count()



    # =====================================================
    # PAGINACION DATATABLES
    # =====================================================

    start = int(

        request.GET.get(
            "start",
            0
        )

    )



    length = int(

        request.GET.get(
            "length",
            25
        )

    )



    queryset = queryset[start:start + length]





    # =====================================================
    # SERIALIZACION
    # =====================================================


    data = []



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

                        str(
                            nivel.nivel
                        )

                    )




        for situacion in supervisor.situaciones.all():


            if situacion.activo:

                situaciones.append(

                    str(
                        situacion.situacion_revista
                    )

                )





        data.append({



            "cuil":

                supervisor.usuario.username,



            "apellido":

                supervisor.usuario.apellido,



            "nombres":

                supervisor.usuario.nombres,



            "regiones":

                "<br>".join(
                    regiones
                )
                or "-",



            "niveles":

                "<br>".join(
                    niveles
                )
                or "-",



            "situaciones":

                "<br>".join(
                    situaciones
                )
                or "-",



            "email":

                supervisor.email
                or "-",



            "telefono":

                supervisor.telefono
                or "-",



            "acciones":



                f"""

                <a

                href="{reverse(
                    'supervisor_registro:detalle',
                    args=[supervisor.pk]
                )}"

                class="btn btn-sm btn-primary"

                title="Ver detalle">

                    <i class="fas fa-eye"></i>

                </a>



                <a

                href="{reverse(
                    'supervisor_registro:editar',
                    args=[supervisor.pk]
                )}"

                class="btn btn-sm btn-warning"

                title="Editar">

                    <i class="fas fa-edit"></i>

                </a>


                """



        })





    # =====================================================
    # RESPUESTA DATATABLES
    # =====================================================


    return JsonResponse({


        "draw":

            int(
                request.GET.get(
                    "draw",
                    1
                )
            ),



        "recordsTotal":

            records_total,



        "recordsFiltered":

            records_filtered,



        "data":

            data


    })