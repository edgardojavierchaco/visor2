from io import BytesIO

from django.utils import timezone

from reportlab.platypus import (
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    PageBreak,
)

from reportlab.lib.styles import (
    getSampleStyleSheet,
)

from reportlab.lib.pagesizes import A4


from django.db.models import (
    Count,
    Sum,
    Avg,
)


from apps.sirtee.models.intervenciones import (
    Intervencion,
)

from apps.sirtee.models.relevamientos import (
    Relevamiento,
)

from apps.sirtee.models.empresas import (
    Empresa,
)


from apps.sirtee.reportes.metrics import (
    obtener_kpis_generales,
)


from apps.sirtee.reportes.queries import (
    intervenciones_por_estado,
    intervenciones_por_empresa,
)



from apps.sirtee.reportes.pdf.base import (
    PDFInstitucional,
)





# =====================================================
# INFORME GENERAL SIRTEE
# =====================================================


def generar_pdf_general():


    pdf = PDFInstitucional(
        titulo=(
            "Informe Institucional "
            "SIRTEE"
        )
    )


    story = []

    styles = getSampleStyleSheet()





    # =================================================
    # PORTADA
    # =================================================


    story.append(
        Paragraph(
            "Sistema Integral de Relevamiento "
            "Técnico de Establecimientos Educativos",
            styles["Title"]
        )
    )


    story.append(
        Spacer(
            1,
            30
        )
    )


    story.append(
        Paragraph(
            "Informe Institucional Provincial",
            styles["Heading2"]
        )
    )


    story.append(
        Spacer(
            1,
            20
        )
    )


    story.append(
        Paragraph(
            f"Fecha de emisión: "
            f"{timezone.now().strftime('%d/%m/%Y')}",
            styles["Normal"]
        )
    )


    story.append(
        PageBreak()
    )






    # =================================================
    # RESUMEN PROVINCIAL
    # =================================================


    story.append(
        Paragraph(
            "1. Resumen Provincial",
            styles["Heading2"]
        )
    )


    total_escuelas = (
        Relevamiento.objects
        .values(
            "cueanexo"
        )
        .distinct()
        .count()
    )


    total_intervenciones = (
        Intervencion.objects.count()
    )


    total_empresas = (
        Empresa.objects.count()
    )


    tabla_resumen = [

        [
            "Indicador",
            "Valor"
        ],

        [
            "Escuelas relevadas",
            total_escuelas,
        ],

        [
            "Intervenciones registradas",
            total_intervenciones,
        ],

        [
            "Empresas registradas",
            total_empresas,
        ],

    ]



    tabla = Table(
        tabla_resumen,
        colWidths=[
            250,
            100,
        ]
    )


    tabla.setStyle(
        TableStyle(
            [
                (
                    "GRID",
                    (0,0),
                    (-1,-1),
                    0.5,
                    None,
                ),

            ]
        )
    )


    story.append(
        tabla
    )



    story.append(
        Spacer(
            1,
            20
        )
    )







    # =================================================
    # KPIs
    # =================================================


    story.append(
        Paragraph(
            "2. Indicadores principales",
            styles["Heading2"]
        )
    )


    kpis = obtener_kpis_generales()



    tabla_kpis = [

        [
            "Indicador",
            "Resultado"
        ],


        [
            "Avance promedio",
            f"{kpis.get('avance_promedio',0)} %",
        ],


        [
            "Costo estimado total",
            f"$ {kpis.get('costo_estimado',0)}",
        ],


        [
            "Intervenciones finalizadas",
            kpis.get(
                "finalizadas",
                0
            ),
        ],


        [
            "Intervenciones en ejecución",
            kpis.get(
                "en_ejecucion",
                0
            ),
        ],


        [
            "Intervenciones pendientes",
            kpis.get(
                "pendientes",
                0
            ),
        ],

    ]



    tabla = Table(
        tabla_kpis
    )


    tabla.setStyle(
        TableStyle(
            [
                (
                    "GRID",
                    (0,0),
                    (-1,-1),
                    0.5,
                    None,
                ),
            ]
        )
    )


    story.append(
        tabla
    )



    story.append(
        PageBreak()
    )







    # =================================================
    # ESTADOS
    # =================================================


    story.append(
        Paragraph(
            "3. Estado de intervenciones",
            styles["Heading2"]
        )
    )



    estados = (
        intervenciones_por_estado()
    )


    datos_estado = [

        [
            "Estado",
            "Cantidad"
        ]

    ]


    for e in estados:


        datos_estado.append(

            [

                e[
                    "estado__nombre"
                ],

                e[
                    "cantidad"
                ]

            ]

        )



    tabla = Table(
        datos_estado
    )


    tabla.setStyle(
        TableStyle(
            [
                (
                    "GRID",
                    (0,0),
                    (-1,-1),
                    0.5,
                    None
                )
            ]
        )
    )


    story.append(
        tabla
    )








    # =================================================
    # RANKING EMPRESAS
    # =================================================


    story.append(
        Spacer(
            1,
            20
        )
    )


    story.append(
        Paragraph(
            "4. Ranking de empresas ejecutoras",
            styles["Heading2"]
        )
    )



    empresas = (
        intervenciones_por_empresa()
    )



    datos_empresa = [

        [
            "Empresa",
            "Intervenciones"
        ]

    ]



    for empresa in empresas[:10]:


        datos_empresa.append(

            [

                empresa.razon_social,

                empresa.cantidad,

            ]

        )



    tabla = Table(
        datos_empresa
    )


    tabla.setStyle(
        TableStyle(
            [
                (
                    "GRID",
                    (0,0),
                    (-1,-1),
                    0.5,
                    None
                )
            ]
        )
    )



    story.append(
        tabla
    )






    # =================================================
    # RANKING ESCUELAS
    # =================================================


    story.append(
        Spacer(
            1,
            20
        )
    )


    story.append(
        Paragraph(
            "5. Escuelas con mayor cantidad "
            "de intervenciones",
            styles["Heading2"]
        )
    )



    escuelas = (

        Intervencion.objects

        .values(
            "hallazgo__relevamiento__cueanexo"
        )

        .annotate(
            cantidad=Count("id")
        )

        .order_by(
            "-cantidad"
        )

    )



    datos_escuelas = [

        [
            "CUE Anexo",
            "Intervenciones"
        ]

    ]



    for escuela in escuelas[:10]:


        datos_escuelas.append(

            [

                escuela[
                    "hallazgo__relevamiento__cueanexo"
                ],

                escuela[
                    "cantidad"
                ]

            ]

        )



    tabla = Table(
        datos_escuelas
    )


    tabla.setStyle(
        TableStyle(
            [
                (
                    "GRID",
                    (0,0),
                    (-1,-1),
                    0.5,
                    None
                )
            ]
        )
    )


    story.append(
        tabla
    )





    # =================================================
    # FINANCIAMIENTO
    # =================================================


    story.append(
        PageBreak()
    )


    story.append(
        Paragraph(
            "6. Resumen financiero",
            styles["Heading2"]
        )
    )


    financiero = (

        Intervencion.objects

        .aggregate(

            estimado=Sum(
                "costo_estimado"
            ),

            ejecutado=Sum(
                "costo_real"
            )

        )

    )


    tabla_finanzas = [

        [
            "Concepto",
            "Monto"
        ],


        [
            "Costo estimado",
            f"$ {financiero['estimado'] or 0}",
        ],


        [
            "Costo ejecutado",
            f"$ {financiero['ejecutado'] or 0}",
        ],


    ]


    tabla = Table(
        tabla_finanzas
    )


    tabla.setStyle(
        TableStyle(
            [
                (
                    "GRID",
                    (0,0),
                    (-1,-1),
                    0.5,
                    None
                )
            ]
        )
    )


    story.append(
        tabla
    )







    # =================================================
    # GENERACIÓN
    # =================================================


    return pdf.render(
        story
    )