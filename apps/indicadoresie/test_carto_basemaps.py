from unittest import TestCase
from unittest.mock import Mock, patch

from django.template.loader import get_template

from .views_regionales import PadronRegionalListView


class PadronRegionalCartoBasemapTests(TestCase):
    def _context(self):
        escuelas = Mock()
        escuelas.exclude.return_value = escuelas
        escuelas.values_list.return_value = escuelas
        escuelas.distinct.return_value = []
        view = PadronRegionalListView()
        with patch.object(view, 'get_queryset', return_value=escuelas):
            return view.get_context_data(object_list=[])

    def test_uses_carto_basemaps_key_from_environment(self):
        with patch.dict('os.environ', {'CARTO_BASEMAPS_API_KEY': '  ficticia-test  '}):
            context = self._context()
        self.assertEqual(context['carto_basemaps_api_key'], 'ficticia-test')

    def test_missing_carto_key_is_empty_for_satellite_fallback(self):
        with patch.dict('os.environ', {'CARTO_BASEMAPS_API_KEY': ''}):
            context = self._context()
        self.assertEqual(context['carto_basemaps_api_key'], '')
    def test_template_compiles_with_carto_and_satellite(self):
        template = get_template('indicadoresie/seguimiento/padron_regionales.html')
        source = template.template.source
        self.assertIn('basemaps.cartocdn.com/rastertiles/voyager/', source)
        self.assertIn("capasBase['Satélite']", source)
        self.assertNotIn('tile.openstreetmap.org', source)
