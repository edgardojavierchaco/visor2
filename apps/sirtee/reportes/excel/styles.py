from openpyxl.styles import Font, PatternFill, Alignment, Border, Side



class ExcelStyles:


    TITULO = Font(
        bold=True,
        size=18
    )


    SUBTITULO = Font(
        bold=True,
        size=12
    )


    ENCABEZADO = Font(
        bold=True
    )


    CENTRAR = Alignment(
        horizontal="center",
        vertical="center"
    )


    BORDE = Border(
        bottom=Side(
            style="thin"
        )
    )



    @staticmethod
    def encabezado(cell):

        cell.font = ExcelStyles.ENCABEZADO

        cell.fill = PatternFill(
            "solid",
            fgColor="D9EAD3"
        )

        cell.alignment = (
            ExcelStyles.CENTRAR
        )