from .base import ExcelBase

from apps.sirtee.models.empresas import Empresa



class EmpresasExcel(
    ExcelBase
):


    def generar(self):


        wb = self.crear_workbook()

        ws = wb.active

        ws.title = "Empresas"



        self.titulo_hoja(
            ws,
            "Empresas registradas SIRTEE"
        )



        self.encabezados(
            ws,
            3,
            [

                "Razón Social",

                "CUIT",

                "Tipo",

                "Teléfono",

                "Email",

                "Localidad",

                "Estado",

            ]
        )



        for e in Empresa.objects.all():


            ws.append([

                e.razon_social,

                e.cuit,

                e.tipo,

                e.telefono,

                e.email,

                e.localidad,

                "Activa"
                if e.activa
                else "Inactiva",

            ])



        self.ajustar_columnas(ws)


        return wb