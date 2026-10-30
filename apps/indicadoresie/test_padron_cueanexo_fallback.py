import re
from unittest import TestCase

from django.template import Context, Template
from django.template.loader import get_template

from .models import PadronRegional


class PadronCueanexoFallbackTests(TestCase):
    def _escuela(self, cueanexo, padron_cueanexo):
        return PadronRegional(
            cueanexo=cueanexo,
            padron_cueanexo=padron_cueanexo,
            nom_est='Escuela de prueba',
        )

    def test_original_cueanexo_tiene_prioridad(self):
        escuela = self._escuela('220012300', '220045600')
        self.assertEqual(escuela.cueanexo_mostrado, '220012300')
        self.assertEqual(escuela.cueanexo, '220012300')

    def test_respaldo_cubre_nulo_vacio_y_espacios(self):
        for original in (None, '', '   '):
            with self.subTest(original=original):
                escuela = self._escuela(original, ' 220045600 ')
                self.assertEqual(escuela.cueanexo_mostrado, '220045600')
                self.assertEqual(escuela.cueanexo, original)

    def test_sin_ninguno_devuelve_vacio(self):
        for respaldo in (None, '', '   '):
            with self.subTest(respaldo=respaldo):
                escuela = self._escuela('  ', respaldo)
                self.assertEqual(escuela.cueanexo_mostrado, '')

    def test_columna_y_mapa_renderizan_el_valor_resuelto(self):
        source = get_template('indicadoresie/seguimiento/padron_regionales.html').template.source
        fragments = (
            re.search(r'<td class="fw-bold text-primary">.*?</td>', source).group(),
            re.search(r'data-cueanexo="[^"]*"', source).group(),
            re.search(r'aria-label="Ver ubicación del CUE-Anexo [^"]*"', source).group(),
        )
        escuela = self._escuela('', '220045600')
        for fragment in fragments:
            with self.subTest(fragment=fragment):
                rendered = Template(fragment).render(Context({'item': escuela}))
                self.assertIn('220045600', rendered)

    def test_original_numerico_se_convierte_solo_para_mostrar(self):
        escuela = self._escuela(220012300, 220045600)
        self.assertEqual(escuela.cueanexo_mostrado, '220012300')
        self.assertEqual(escuela.cueanexo, 220012300)

    def test_respaldo_numerico_si_original_esta_vacio(self):
        for original in (None, '', '   '):
            with self.subTest(original=original):
                escuela = self._escuela(original, 220045600)
                self.assertEqual(escuela.cueanexo_mostrado, '220045600')
                self.assertEqual(escuela.cueanexo, original)
