import re
from unittest import TestCase

from django.template import Context, Template
from django.template.loader import get_template

from .models import PadronRegional


class PadronRegionalOrdenCoordenadasTests(TestCase):
    def _template_source(self):
        return get_template(
            'indicadoresie/seguimiento/padron_regionales.html'
        ).template.source

    def test_prioriza_faltantes_sin_ocultar_las_coordenadas_parciales(self):
        source = self._template_source()
        celda_accion = re.search(
            r'<td class="col-accion text-center"[^>]*>', source
        )
        self.assertIsNotNone(celda_accion)
        celda = Template(celda_accion.group())

        casos = (
            (None, None, '0'),
            (None, -58.3, '1'),
            (-27.2, None, '1'),
            (0, -58.3, '1'),
            (-27.2, -58.3, '2'),
        )
        for latitud, longitud, prioridad in casos:
            with self.subTest(latitud=latitud, longitud=longitud):
                escuela = PadronRegional(
                    cueanexo='220012300',
                    nom_est='Escuela de prueba',
                    lat=latitud,
                    long=longitud,
                )
                rendered = celda.render(Context({'item': escuela}))
                self.assertIn(f'data-order="{prioridad}"', rendered)

    def test_data_tables_ordena_por_prioridad_y_luego_cueanexo(self):
        source = self._template_source()
        self.assertRegex(
            source,
            r'order:\s*\[\s*\[\s*0\s*,\s*[\'"]asc[\'"]\s*\]\s*,'
            r'\s*\[\s*1\s*,\s*[\'"]asc[\'"]\s*\]\s*\]',
        )
        self.assertRegex(
            source,
            r'targets:\s*0\s*,\s*orderable:\s*false',
        )
