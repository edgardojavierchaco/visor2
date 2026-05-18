class SQLBuilder:

    def build_base_query(self, filters):
        """
        Construye query base según filtros
        """
        where = []

        if filters.get("cueanexo"):
            where.append(f"cueanexo = '{filters['cueanexo']}'")

        if filters.get("orientacion"):
            where.append(f"orientacion = '{filters['orientacion']}'")

        where_sql = " AND ".join(where) if where else "1=1"

        return f"""
            SELECT *
            FROM fact_education
            WHERE {where_sql}
        """

    def build_indicator_query(self, indicator, base_table="fact_education"):
        """
        Traduce JSON formula → SQL
        """

        f = indicator.formula

        # SIMPLE FORMULA (TPE/TR)
        if f.get("type") == "formula":

            num = f["numerator"]["expr"]
            den = f["denominator"]["expr"]

            group_by = ",".join(f.get("group_by", ["cueanexo"]))

            return f"""
                SELECT
                    {group_by},
                    SUM({num})::float / NULLIF(SUM({den}),0) * 100 AS value
                FROM {base_table}
                GROUP BY {group_by}
            """

        # DERIVED (TAI)
        if f.get("type") == "derived":
            # se resuelve en aggregator
            return None