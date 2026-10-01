from django.test import SimpleTestCase

from .selectors import general_summary, regional_load_summary


class ReporteEstadoCargaTests(SimpleTestCase):
    def setUp(self):
        self.rows = [
            {
                "region": "REGIÓN 1",
                "estado_carga": "SIN_CARGA",
                "personas": 0,
                "cargos": 0,
                "docentes": 0,
                "no_docentes": 0,
                "borradores": 0,
                "observados": 0,
                "validados": 0,
            },
            {
                "region": "REGIÓN 1",
                "estado_carga": "VALIDADO",
                "personas": 5,
                "cargos": 7,
                "docentes": 6,
                "no_docentes": 1,
                "borradores": 0,
                "observados": 0,
                "validados": 7,
            },
        ]

    def test_resumen_general(self):
        data = general_summary(self.rows)
        self.assertEqual(data["instituciones"], 2)
        self.assertEqual(data["con_carga"], 1)
        self.assertEqual(data["validado"], 1)
        self.assertEqual(data["porcentaje_con_carga"], 50.0)

    def test_resumen_regional(self):
        data = regional_load_summary(self.rows)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["region"], "REGIÓN 1")
        self.assertEqual(data[0]["sin_carga"], 1)
        self.assertEqual(data[0]["validado"], 1)
