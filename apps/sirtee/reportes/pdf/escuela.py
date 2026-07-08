from django.db import models
from django.utils import timezone

from apps.sirtee.models.relevamientos import Relevamiento
from apps.sirtee.models.hallazgos import Hallazgo
from apps.sirtee.models.intervenciones import Intervencion

from apps.sirtee.reportes.pdf.documento import DocumentoPDF


class ReporteEscuelaPDF(DocumentoPDF):
    """
    Reporte institucional completo de una escuela.

    Incluye:

    • Datos generales
    • Relevamientos
    • Hallazgos
    • Intervenciones
    • Estadísticas
    • Fotografías (si existen)
    """

    titulo = "Reporte Institucional de Escuela"

    autor = "SIRTEE"

    asunto = "Infraestructura Escolar"

    def __init__(self, cueanexo):

        super().__init__()

        self.cueanexo = cueanexo

        self.relevamientos = (
            Relevamiento.objects
            .filter(cueanexo=cueanexo)
            .prefetch_related(
                "hallazgos",
                "hallazgos__intervenciones",
            )
            .order_by("-fecha")
        )

    # ------------------------------------------------------

    def generar(self):

        self.titulo_principal(
            "REPORTE INSTITUCIONAL DE ESCUELA"
        )

        self.texto(
            f"<b>CUE/Anexo:</b> {self.cueanexo}"
        )

        self.texto(
            f"<b>Fecha de emisión:</b> "
            f"{timezone.now():%d/%m/%Y %H:%M}"
        )

        self.separador()

        self.agregar_estadisticas()

        self.separador()

        self.agregar_relevamientos()

        self.separador()

        self.agregar_hallazgos()

        self.separador()

        self.agregar_intervenciones()

        self.separador()

        self.agregar_fotografias()

        self.firma()

        return self.build()

    # ------------------------------------------------------

    def agregar_estadisticas(self):

        hallazgos = Hallazgo.objects.filter(
            relevamiento__cueanexo=self.cueanexo
        )

        intervenciones = Intervencion.objects.filter(
            hallazgo__relevamiento__cueanexo=self.cueanexo
        )

        finalizadas = intervenciones.filter(
            estado__codigo="FINALIZADA"
        ).count()

        pendientes = intervenciones.exclude(
            estado__codigo="FINALIZADA"
        ).count()

        costo = (
            intervenciones.aggregate(
                total=models.Sum("costo_estimado")
            )["total"] or 0
        )

        self.subtitulo("Indicadores")

        self.agregar_kpis(

            [

                (
                    "Relevamientos",
                    self.relevamientos.count()
                ),

                (
                    "Hallazgos",
                    hallazgos.count()
                ),

                (
                    "Intervenciones",
                    intervenciones.count()
                ),

                (
                    "Finalizadas",
                    finalizadas
                ),

                (
                    "Pendientes",
                    pendientes
                ),

                (
                    "Costo estimado",
                    f"${costo:,.2f}"
                ),

            ]

        )

    # ------------------------------------------------------

    def agregar_relevamientos(self):

        self.subtitulo("Relevamientos")

        filas = []

        for r in self.relevamientos:

            filas.append([

                r.fecha.strftime("%d/%m/%Y")
                if r.fecha else "-",

                getattr(
                    r,
                    "inspector",
                    "-"
                ),

                getattr(
                    r,
                    "estado",
                    "-"
                ),

            ])

        if not filas:

            filas.append(
                ["-", "-", "-"]
            )

        self.agregar_tabla(

            [

                "Fecha",
                "Inspector",
                "Estado",

            ],

            filas,

            widths=[4 * 72 / 2.54,
                    7 * 72 / 2.54,
                    6 * 72 / 2.54]

        )

    # ------------------------------------------------------

    def agregar_hallazgos(self):

        self.subtitulo("Hallazgos")

        filas = []

        hallazgos = Hallazgo.objects.filter(
            relevamiento__cueanexo=self.cueanexo
        )

        for h in hallazgos:

            filas.append([

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

            ])

        if not filas:

            filas.append(
                ["Sin registros", "-", "-", "-"]
            )

        self.agregar_tabla(

            [

                "Hallazgo",
                "Categoría",
                "Prioridad",
                "Estado",

            ],

            filas,

        )

    # ------------------------------------------------------

    def agregar_intervenciones(self):

        self.subtitulo("Intervenciones")

        filas = []

        intervenciones = (
            Intervencion.objects
            .filter(
                hallazgo__relevamiento__cueanexo=self.cueanexo
            )
            .select_related(
                "empresa",
                "estado",
            )
        )

        for i in intervenciones:

            filas.append([

                i.titulo,

                (
                    i.empresa.razon_social
                    if i.empresa
                    else "-"
                ),

                getattr(
                    i.estado,
                    "nombre",
                    "-"
                ),

                f"{i.porcentaje_avance}%",

            ])

        if not filas:

            filas.append(
                ["Sin registros", "-", "-", "-"]
            )

        self.agregar_tabla(

            [

                "Intervención",
                "Empresa",
                "Estado",
                "Avance",

            ],

            filas,

        )

    # ------------------------------------------------------

    def agregar_fotografias(self):

        self.subtitulo("Registro fotográfico")

        fotos = []

        for relevamiento in self.relevamientos:

            if hasattr(
                relevamiento,
                "fotografias"
            ):

                fotos.extend(
                    relevamiento.fotografias.all()
                )

        if not fotos:

            self.texto(
                "No existen fotografías asociadas."
            )
            return

        self.texto(
            f"Fotografías registradas: {len(fotos)}"
        )

        self.texto(
            "La incorporación automática de imágenes "
            "se realizará utilizando Image + ReportLab "
            "en la siguiente entrega."
        )