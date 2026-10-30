import re
from unittest import TestCase

from django.template.loader import get_template


class PadronRegionalFiltrosTests(TestCase):
    def _source(self):
        return get_template(
            'indicadoresie/seguimiento/padron_regionales.html'
        ).template.source

    def test_panel_conserva_desplegables_y_solo_dos_buscadores_de_coordenadas(self):
        source = self._source()
        panel = source.split('<div class="filter-grid">', 1)[1].split(
            '<div id="advertencia-region"', 1
        )[0]

        selects = re.findall(r'<select\b[^>]*\bid="([^"]+)"', panel)
        inputs = re.findall(
            r'<input\b[^>]*\btype="text"[^>]*\bid="([^"]+)"', panel
        )
        self.assertEqual(
            selects,
            [
                'fRegion', 'fDepartamento', 'fLocalidad',
                'fSector', 'fAmbito', 'fOferta',
            ],
        )
        self.assertEqual(inputs, ['fLatitud', 'fLongitud'])

    def test_no_quedan_referencias_a_busquedas_duplicadas(self):
        source = self._source()
        for control in (
            'fCueanexo', 'fEstablecimiento', 'fDireccion',
            'fDirectivo', 'fTelefono', 'fCorreo',
        ):
            with self.subTest(control=control):
                self.assertNotIn(control, source)

    def test_buscador_general_sigue_busqueda_total_y_por_columna(self):
        source = self._source()
        self.assertIn('id="searchScope"', source)
        self.assertIn('id="customSearch"', source)
        self.assertIn('table.search(texto, false, false, true)', source)
        self.assertIn('table.column(indice).search(texto, false, false, true)', source)
        self.assertIn(
            "aplicarBusquedaTexto($('#customSearch').val(), $('#searchScope').val() || 'all')",
            source,
        )
        self.assertIn('order: [[0, \'asc\'], [1, \'asc\']]', source)

    def test_ayuda_distingue_coordenadas_y_buscador_general(self):
        source = self._source()
        self.assertIn('<strong>Latitud y Longitud</strong>', source)
        self.assertIn('<strong>Buscador Inteligente:', source)

    def test_latitud_y_longitud_iguales_en_fila_final(self):
        source = self._source()
        self.assertRegex(
            source,
            r'(?s)<div class="filter-coordinates">\s*'
            r'<div class="filter-item">.*?id="fLatitud".*?</div>\s*'
            r'<div class="filter-item">.*?id="fLongitud".*?</div>\s*'
            r'</div>',
        )
        self.assertRegex(
            source,
            r'\.filter-coordinates\s*\{\s*grid-column:\s*1\s*/\s*-1;'
            r'\s*display:\s*grid;\s*grid-template-columns:\s*'
            r'repeat\(2,\s*minmax\(0,\s*1fr\)\);',
        )
        self.assertNotIn('.filter-item:last-child', source)
        self.assertRegex(
            source,
            r'@media \(max-width: 768px\)\s*\{\s*'
            r'\.filter-grid\s*\{[^}]*\}\s*'
            r'\.filter-coordinates\s*\{[^}]*'
            r'grid-template-columns:\s*1fr;[^}]*\}',
        )

    def test_buscadores_textuales_comparten_motor_y_limpieza(self):
        source = self._source()

        # La normalización se aplica tanto a los filtros como al buscador general.
        self.assertRegex(
            source,
            r'function normalizarTextoBusqueda\(valor\)\s*\{[^}]*'
            r'String\(valor\s*\|\|\s*\x27\x27\)\.trim\(\)\.replace\('
            r'/\\s\+/g,\s*\x27 \x27\)',
        )
        self.assertIn('function aplicarBusquedaTexto(valor, columna)', source)
        self.assertIn('const texto = normalizarTextoBusqueda(valor);', source)
        self.assertIn('table.search(texto, false, false, true)', source)
        self.assertIn('table.column(indice).search(texto, false, false, true)', source)

        self.assertIn("aplicarBusquedaTexto($('#fLatitud').val(), 2)", source)
        self.assertIn("aplicarBusquedaTexto($('#fLongitud').val(), 3)", source)
        self.assertIn(
            "aplicarBusquedaTexto($('#customSearch').val(), $('#searchScope').val() || 'all')",
            source,
        )
        self.assertNotIn('escapeRegex(latVal)', source)
        self.assertNotIn('escapeRegex(longVal)', source)

    def test_texto_de_coordenadas_para_chips_y_excel_se_normaliza(self):
        source = self._source()
        # Espacios al principio/final o repetidos no crean un filtro distinto.
        self.assertGreaterEqual(
            source.count('val = normalizarTextoBusqueda(val);'),
            2,
        )
        self.assertIn("id === 'fLatitud' || id === 'fLongitud'", source)

    def test_paginacion_tamano_inicial_y_opciones(self):
        source = self._source()
        selector = re.search(
            r'<select id="dtLengthSelect"[^>]*>(.*?)</select>',
            source,
            re.DOTALL,
        )
        self.assertIsNotNone(selector)
        self.assertEqual(
            re.findall(r'<option value="(\d+)"( selected)?>(\d+)</option>', selector.group(1)),
            [('5', ' selected', '5'), ('10', '', '10'),
             ('25', '', '25'), ('50', '', '50')],
        )
        self.assertIn('pageLength: 5,', source)
        self.assertIn("$('#dtLengthSelect').on('change'", source)
        self.assertIn('table.page.len(parseInt(this.value', source)

    def test_selector_y_paginacion_tienen_estilo_y_etiqueta(self):
        source = self._source()
        self.assertIn('<label for="dtLengthSelect"', source)
        self.assertIn('class="page-size-control"', source)
        self.assertIn('class="page-size-select"', source)
        self.assertIn('aria-label="Cantidad de filas por página"', source)
        self.assertIn('.page-size-control {', source)
        self.assertIn('.page-size-select select {', source)
        self.assertIn('#dtPaginate .page-link {', source)
        self.assertIn('#dtPaginate .page-item.active .page-link {', source)

    def test_paginacion_se_muestra_al_abrir_y_no_activa_controles_deshabilitados(self):
        source = self._source()
        self.assertRegex(
            source,
            r"table\.on\('draw',\s*function\(\)\s*\{\s*updateFooter\(\);\s*\}\);"
            r"\s*updateFooter\(\);",
        )
        self.assertIn("$(this).closest('.page-item').hasClass('disabled')", source)
