from django.db.models import (
    Sum,
    Avg,
)

from django.utils import timezone

from apps.sirtee.models.empresas import Empresa
from apps.sirtee.models.intervenciones import Intervencion

from apps.sirtee.reportes.pdf.documento import DocumentoPDF


class ReporteEmpresaPDF(DocumentoPDF):
    """
    Reporte institucional por empresa.

    Incluye:

    • Datos generales
    • Indicadores
    • Historial de intervenciones
    • Costos
    • Avance promedio
    • KPIs
    """

    titulo = "Reporte Institucional de Empresa"

    autor = "SIRTEE"

    asunto = "Historial de Empresa"

    def __init__(self, empresa):

        super().__init__()

        if isinstance(empresa, Empresa):

            self.empresa = empresa

        else:

            self.empresa = Empresa.objects.get(
                pk=empresa
            )

        self.intervenciones = (

            Intervencion.objects

            .filter(
                empresa=self.empresa
            )

            .select_related(
                "hallazgo",
                "hallazgo__relevamiento",
                "estado",
                "prioridad",
                "tipo",
            )

            .order_by(
                "-fecha_inicio",
                "-id",
            )

        )

    # ==========================================================
    # PDF
    # ==========================================================

    def generar(self):

        self.titulo_principal(
            "REPORTE INSTITUCIONAL DE EMPRESA"
        )

        self.texto(
            f"<b>Razón social:</b> "
            f"{self.empresa.razon_social}"
        )

        self.texto(
            f"<b>CUIT:</b> "
            f"{self.empresa.cuit or '-'}"
        )

        self.texto(
            f"<b>Tipo:</b> "
            f"{self.empresa.get_tipo_display()}"
        )

        self.texto(
            f"<b>Responsable:</b> "
            f"{self.empresa.responsable or '-'}"
        )

        self.texto(
            f"<b>Fecha del reporte:</b> "
            f"{timezone.now():%d/%m/%Y %H:%M}"
        )

        self.separador()

        self.agregar_kpis_empresa()

        self.separador()

        self.agregar_costos()

        self.separador()

        self.agregar_historial()

        self.firma()

        return self.build()

    # ==========================================================
    # KPIs
    # ==========================================================

    def agregar_kpis_empresa(self):

        total = self.intervenciones.count()

        finalizadas = self.intervenciones.filter(
            estado__codigo="FINALIZADA"
        ).count()

        ejecucion = self.intervenciones.filter(
            estado__codigo="EN_EJECUCION"
        ).count()

        pendientes = self.intervenciones.filter(
            estado__codigo="PENDIENTE"
        ).count()

        avance = (

            self.intervenciones.aggregate(
                promedio=Avg(
                    "porcentaje_avance"
                )
            )["promedio"]

            or 0

        )

        self.subtitulo("Indicadores")

        self.agregar_kpis(

            [

                (
                    "Intervenciones",
                    total
                ),

                (
                    "Finalizadas",
                    finalizadas
                ),

                (
                    "En ejecución",
                    ejecucion
                ),

                (
                    "Pendientes",
                    pendientes
                ),

                (
                    "Avance promedio",
                    f"{avance:.1f}%"
                ),

            ]

        )

    # ==========================================================
    # COSTOS
    # ==========================================================

    def agregar_costos(self):

        estimado = (

            self.intervenciones.aggregate(

                total=Sum(
                    "costo_estimado"
                )

            )["total"]

            or 0

        )

        real = (

            self.intervenciones.aggregate(

                total=Sum(
                    "costo_real"
                )

            )["total"]

            or 0

        )

        diferencia = real - estimado

        self.subtitulo("Resumen financiero")

        self.agregar_kpis(

            [

                (
                    "Costo estimado",
                    f"${estimado:,.2f}"
                ),

                (
                    "Costo real",
                    f"${real:,.2f}"
                ),

                (
                    "Diferencia",
                    f"${diferencia:,.2f}"
                ),

            ]

        )

    # ==========================================================
    # HISTORIAL
    # ==========================================================

    def agregar_historial(self):

        self.subtitulo(
            "Historial de intervenciones"
        )

        filas = []

        for intervencion in self.intervenciones:

            escuela = getattr(

                intervencion.hallazgo.relevamiento,

                "cueanexo",

                "-",

            )

            filas.append(

                [

                    escuela,

                    intervencion.titulo,

                    intervencion.tipo.nombre
                    if intervencion.tipo
                    else "-",

                    intervencion.estado.nombre
                    if intervencion.estado
                    else "-",

                    intervencion.prioridad.nombre
                    if intervencion.prioridad
                    else "-",

                    f"{intervencion.porcentaje_avance}%",

                ]

            )

        if not filas:

            filas.append(

                [

                    "-",

                    "Sin intervenciones",

                    "-",

                    "-",

                    "-",

                    "-",

                ]

            )

        self.agregar_tabla(

            [

                "Escuela",

                "Intervención",

                "Tipo",

                "Estado",

                "Prioridad",

                "Avance",

            ],

            filas,

        )