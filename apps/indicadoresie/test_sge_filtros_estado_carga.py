import re
from unittest import TestCase

from django.template.loader import get_template


class FiltrosEstadoCargaSgeTests(TestCase):
    def _source(self):
        return get_template(
            'indicadoresie/seguimiento/list_sge.html'
        ).template.source

    def test_nueva_opcion_esta_en_los_dos_anios(self):
        source = self._source()
        for year in (2025, 2026):
            with self.subTest(year=year):
                select = re.search(
                    rf'<select\s+id="fAudit{year}"[^>]*>(.*?)</select>',
                    source,
                    re.DOTALL,
                )
                self.assertIsNotNone(select)
                values = re.findall(r'<option\s+value="([^"]*)"', select.group(1))
                self.assertEqual(values, ['', 'ok', 'vacio', 'diff', 'solo_insc'])
                self.assertIn(
                    '<option value="vacio">⚪ Sin Carga (Ambos)</option>',
                    select.group(1),
                )
                self.assertIn(
                    '<option value="solo_insc">⚪ Sin Carga (Solo en Inscriptos)</option>',
                    select.group(1),
                )

    def test_cada_opcion_exige_sge_y_cero_inscriptos_de_su_anio(self):
        source = self._source()
        self.assertIn('var sge25 = getNum(data[16]), insc25 = getNum(data[17]);', source)
        self.assertIn('var sge26 = getNum(data[18]), insc26 = getNum(data[19]);', source)
        for year, suffix in ((2025, '25'), (2026, '26')):
            with self.subTest(year=year):
                rule = next(
                    (line.strip() for line in source.splitlines()
                     if f"audit{year} === 'solo_insc'" in line),
                    None,
                )
                self.assertEqual(
                    rule,
                    f"if (audit{year} === 'solo_insc' && !(sge{suffix} > 0 && insc{suffix} === 0)) return false;",
                )

    def test_las_tres_condiciones_anteriores_se_conservan(self):
        source = self._source()
        for year, suffix in ((2025, '25'), (2026, '26')):
            with self.subTest(year=year):
                self.assertIn(
                    f"if (audit{year} === 'ok' && !(sge{suffix} > 0 && sge{suffix} === insc{suffix})) return false;",
                    source,
                )
                self.assertIn(
                    f"if (audit{year} === 'diff' && !((sge{suffix} > 0 || insc{suffix} > 0) && sge{suffix} !== insc{suffix})) return false;",
                    source,
                )
                self.assertIn(
                    f"if (audit{year} === 'vacio' && !(sge{suffix} === 0 && insc{suffix} === 0)) return false;",
                    source,
                )

    def test_busqueda_cueanexo_y_ayuda_se_conservan(self):
        source = self._source()
        self.assertIn('if (fCueanexo) table.column(1).search(fCueanexo).visible(true);', source)
        self.assertIn('<strong class="text-primary">Sin Carga (Solo en Inscriptos)</strong>', source)
        self.assertIn('<strong class="text-secondary">Sin Carga (Ambos)</strong>', source)

    def test_solo_inscriptos_casos_reales_de_ambos_anios(self):
        source = self._source()
        scenarios = (
            (17, 0, True),
            (73, 0, True),
            (52, 'Sin Inscripciones 2026', True),
            (0, 0, False),
            ('Sin Carga 2026', 'Sin Inscripciones 2026', False),
            ('Sin Carga 2025', 'Sin Inscripciones 2025', False),
            (0, 17, False),
            (17, 17, False),
            (17, 8, False),
        )

        def as_number(value):
            val = str(value).strip().lower()
            if val in ('', '-', '0') or 'sin' in val:
                return 0
            return int(val)

        for year, suffix in ((2025, '25'), (2026, '26')):
            rule = re.search(
                rf"if \(audit{year} === 'solo_insc' && !\(([^)]+)\)\) return false;",
                source,
            )
            self.assertIsNotNone(rule, f'Falta el predicado de {year}')
            js_expr = rule.group(1)
            self.assertRegex(js_expr, r'^[a-z0-9\s&|=!<>+()*-]+$')
            python_expr = js_expr.replace('===', '==').replace('&&', 'and').replace('||', 'or')
            for sge, insc, should_include in scenarios:
                with self.subTest(year=year, sge=sge, inscriptos=insc):
                    numbers = {
                        f'sge{suffix}': as_number(sge),
                        f'insc{suffix}': as_number(insc),
                    }
                    result = bool(eval(python_expr, {'__builtins__': {}}, numbers))
                    self.assertEqual(result, should_include)
