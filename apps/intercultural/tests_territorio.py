from django.test import SimpleTestCase
from django.urls import reverse

class RutasTerritorialesTests(SimpleTestCase):
    def test_rutas(self):
        self.assertEqual(reverse('intercultural:mapa'), '/indigena/mapa/')
        self.assertEqual(reverse('intercultural:monitoreo'), '/indigena/monitoreo/')
