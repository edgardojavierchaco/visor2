from django.db.models import (
    Count,
    Sum,
    Avg,
)

from django.utils import timezone


from apps.sirtee.models.relevamientos import Relevamiento

from apps.sirtee.models.hallazgos import Hallazgo

from apps.sirtee.models.intervenciones import Intervencion


from apps.sirtee.reportes.pdf.documento import DocumentoPDF



class ReporteRelevamientoPDF(DocumentoPDF):
    """
    Reporte institucional de un relevamiento técnico.

    Incluye:

    • Datos generales
    • Escuela
    • Responsable
    • Estadísticas
    • Hallazgos
    • Intervenciones
    • Costos
    • Avance
    • Observaciones
    • Fotografías
    """

    titulo = "Reporte de Relevamiento Técnico"

    autor = "SIRTEE"

    asunto = "Relevamiento de Infraestructura Escolar"



    def __init__(self, relevamiento):

        super().__init__()


        if isinstance(
            relevamiento,
            Relevamiento
        ):

            self.relevamiento = relevamiento


        else:

            self.relevamiento = (

                Relevamiento.objects

                .select_related()

                .get(
                    pk=relevamiento
                )

            )



        self.hallazgos = (

            Hallazgo.objects

            .filter(
                relevamiento=self.relevamiento
            )

            .select_related(
                "categoria",
                "prioridad",
                "estado",
            )

        )



        self.intervenciones = (

            Intervencion.objects

            .filter(
                hallazgo__relevamiento=self.relevamiento
            )

            .select_related(
                "empresa",
                "estado",
                "prioridad",
            )

        )



    # =====================================================
    # GENERADOR PRINCIPAL
    # =====================================================


    def generar(self):


        self.titulo_principal(
            "REPORTE INSTITUCIONAL DE RELEVAMIENTO"
        )


        self.texto(

            f"<b>Fecha emisión:</b> "
            f"{timezone.now():%d/%m/%Y %H:%M}"

        )


        self.separador()


        self.datos_generales()


        self.separador()


        self.indicadores()


        self.separador()


        self.listado_hallazgos()


        self.separador()


        self.listado_intervenciones()


        self.separador()


        self.observaciones()


        self.separador()


        self.fotografias()


        self.firma()


        return self.build()



    # =====================================================
    # DATOS GENERALES
    # =====================================================


    def datos_generales(self):


        self.subtitulo(
            "Datos generales"
        )


        escuela = getattr(

            self.relevamiento,

            "cueanexo",

            "-"

        )


        responsable = getattr(

            self.relevamiento,

            "responsable",

            "-"

        )


        estado = getattr(

            self.relevamiento,

            "estado",

            "-"

        )


        self.agregar_tabla(

            [

                "Campo",

                "Valor",

            ],


            [

                [

                    "Escuela",

                    escuela,

                ],


                [

                    "Fecha",

                    self.relevamiento.fecha.strftime(
                        "%d/%m/%Y"
                    )
                    if self.relevamiento.fecha
                    else "-",

                ],


                [

                    "Responsable",

                    responsable,

                ],


                [

                    "Estado",

                    estado,

                ],


            ]

        )



    # =====================================================
    # INDICADORES
    # =====================================================


    def indicadores(self):


        cantidad_hallazgos = (
            self.hallazgos.count()
        )


        cantidad_intervenciones = (
            self.intervenciones.count()
        )


        finalizadas = (

            self.intervenciones

            .filter(
                estado__codigo="FINALIZADA"
            )

            .count()

        )


        avance = (

            self.intervenciones

            .aggregate(

                promedio=Avg(
                    "porcentaje_avance"
                )

            )

            ["promedio"]

            or 0

        )


        costo = (

            self.intervenciones

            .aggregate(

                total=Sum(
                    "costo_estimado"
                )

            )

            ["total"]

            or 0

        )


        self.subtitulo(
            "Indicadores del relevamiento"
        )


        self.agregar_kpis(

            [

                (

                    "Hallazgos detectados",

                    cantidad_hallazgos

                ),


                (

                    "Intervenciones generadas",

                    cantidad_intervenciones

                ),


                (

                    "Intervenciones finalizadas",

                    finalizadas

                ),


                (

                    "Avance promedio",

                    f"{avance:.1f}%"

                ),


                (

                    "Costo estimado",

                    f"${costo:,.2f}"

                ),

            ]

        )



    # =====================================================
    # HALLAZGOS
    # =====================================================


    def listado_hallazgos(self):


        self.subtitulo(
            "Hallazgos registrados"
        )


        filas = []


        for h in self.hallazgos:


            filas.append(

                [

                    h.titulo,


                    getattr(
                        h.categoria,
                        "nombre",
                        "-"
                    ),


                    getattr(
                        h.prioridad,
                        "nombre",
                        "-"
                    ),


                    getattr(
                        h.estado,
                        "nombre",
                        "-"
                    ),

                ]

            )


        if not filas:


            filas.append(

                [

                    "Sin hallazgos",

                    "-",

                    "-",

                    "-",

                ]

            )



        self.agregar_tabla(

            [

                "Hallazgo",

                "Categoría",

                "Prioridad",

                "Estado",

            ],


            filas

        )



    # =====================================================
    # INTERVENCIONES
    # =====================================================


    def listado_intervenciones(self):


        self.subtitulo(
            "Intervenciones asociadas"
        )


        filas = []


        for i in self.intervenciones:


            empresa = "-"


            if i.empresa:

                empresa = (
                    i.empresa.razon_social
                )


            filas.append(

                [

                    i.titulo,


                    empresa,


                    getattr(
                        i.estado,
                        "nombre",
                        "-"
                    ),


                    f"{i.porcentaje_avance}%",

                ]

            )



        if not filas:


            filas.append(

                [

                    "Sin intervenciones",

                    "-",

                    "-",

                    "-",

                ]

            )



        self.agregar_tabla(

            [

                "Intervención",

                "Empresa",

                "Estado",

                "Avance",

            ],


            filas

        )



    # =====================================================
    # OBSERVACIONES
    # =====================================================


    def observaciones(self):


        self.subtitulo(
            "Observaciones"
        )


        texto = getattr(

            self.relevamiento,

            "observaciones",

            None

        )


        self.texto(

            texto

            or

            "Sin observaciones registradas."

        )



    # =====================================================
    # FOTOGRAFÍAS
    # =====================================================


    def fotografias(self):


        self.subtitulo(
            "Registro fotográfico"
        )


        if hasattr(

            self.relevamiento,

            "fotografias"

        ):


            fotos = (
                self.relevamiento
                .fotografias
                .all()
            )


            if fotos.exists():

                self.texto(

                    f"Fotografías asociadas: "
                    f"{fotos.count()}"

                )

                return



        self.texto(

            "No existen fotografías asociadas."

        )