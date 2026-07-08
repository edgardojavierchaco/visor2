from .base import ExcelBase

from apps.sirtee.models.intervenciones import Intervencion



class IntervencionesExcel(
    ExcelBase
):


    def generar(
        self,
        queryset=None
    ):


        if queryset is None:

            queryset = (
                Intervencion.objects
                .select_related(
                    "hallazgo",
                    "empresa",
                    "estado",
                    "tipo",
                    "prioridad"
                )
            )


        wb = self.crear_workbook()

        ws = wb.active

        ws.title = "Intervenciones"



        self.titulo_hoja(
            ws,
            "Reporte de Intervenciones SIRTEE"
        )



        columnas = [

            "ID",

            "Título",

            "Escuela",

            "Empresa",

            "Tipo",

            "Estado",

            "Prioridad",

            "Avance %",

            "Costo estimado",

            "Costo real",

        ]



        self.encabezados(
            ws,
            3,
            columnas
        )



        fila = 4


        for obj in queryset:


            ws.append([

                obj.id,

                obj.titulo,

                obj.hallazgo
                .relevamiento
                .cueanexo,

                obj.empresa
                .razon_social
                if obj.empresa
                else "",


                obj.tipo.nombre,

                obj.estado.nombre,

                obj.prioridad.nombre,


                obj.porcentaje_avance,


                obj.costo_estimado,


                obj.costo_real,

            ])



        self.ajustar_columnas(
            ws
        )


        return wb