from django.db import connection
from rest_framework.exceptions import ValidationError


class IndicatorService:

    FUNCTION_MAP = {
        ("PRIMARIA", "2023_2024"):
            "indicadores.get_indicadores_primario_2023_2024",

        ("PRIMARIA", "2024_2025"):
            "indicadores.get_indicadores_primario_2024_2025",

        ("SECUNDARIA", "2023_2024"):
            "indicadores.get_indicadores_secundario_2023_2024",

        ("SECUNDARIA", "2024_2025"):
            "indicadores.get_indicadores_secundario_2024_2025",

        ("TECNICA", "2023_2024"):
            "indicadores.get_indicadores_tecnica_2023_2024",

        ("TECNICA", "2024_2025"):
            "indicadores.get_indicadores_tecnica_2024_2025",
    }

    PERIODS = [
        "2023_2024",
        "2024_2025"
    ]

    def get_indicators(self, filters):

        cueanexo = filters["cueanexo"]
        nivel = filters["nivel"].upper()
        orientacion = filters.get("orientacion")

        results = []

        for period in self.PERIODS:

            function_name = self.FUNCTION_MAP.get(
                (nivel, period)
            )

            if not function_name:
                continue

            with connection.cursor() as cursor:

                # primaria
                if nivel == "PRIMARIA":

                    cursor.execute(
                        f"""
                        SELECT *
                        FROM {function_name}(%s)
                        """,
                        [cueanexo]
                    )

                # secundaria / tecnica
                else:

                    cursor.execute(
                        f"""
                        SELECT *
                        FROM {function_name}(%s,%s)
                        """,
                        [cueanexo, orientacion]
                    )

                cols = [
                    col[0]
                    for col in cursor.description
                ]

                rows = cursor.fetchall()

            period_data = [
                dict(zip(cols, row))
                for row in rows
            ]

            results.append({
                "period": period,
                "indicators": period_data
            })

        return results