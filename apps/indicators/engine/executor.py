from django.db import connection
from .registry import IndicatorRegistry
from .sql_builder import SQLBuilder
from .aggregator import Aggregator


class IndicatorExecutor:

    def __init__(self):
        self.builder = SQLBuilder()
        self.aggregator = Aggregator()

    def run(self, code, filters=None):
        filters = filters or {}

        indicator = IndicatorRegistry.get(code)

        query = self.builder.build_indicator_query(indicator)

        # DERIVED (TAI)
        if query is None:
            return self._run_derived(indicator, filters)

        return self._run_sql(query)

    def _run_sql(self, query):
        with connection.cursor() as cursor:
            cursor.execute(query)
            cols = [col[0] for col in cursor.description]
            return [
                dict(zip(cols, row))
                for row in cursor.fetchall()
            ]

    def _run_derived(self, indicator, filters):
        # ejemplo TAI depende de TPE y TR
        if indicator.code == "TAI":

            tpe = self.run("TPE", filters)
            tr = self.run("TR", filters)

            return self.aggregator.compute_tai(tpe, tr)

        return []