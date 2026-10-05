import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import ConstanciaServicio, Personas
from .services.constancia_verificacion import calcular_hash_contenido


class ConstanciaPublicaTests(TestCase):
    """Pruebas mínimas del endpoint público. Ajustar fixtures si el modelo Persona exige catálogos externos."""

    def test_token_desconocido_devuelve_404(self):
        url = reverse('bnhpersonas:verificar_constancia', kwargs={'token': uuid.uuid4()})
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_hash_es_determinista(self):
        a = {'b': 2, 'a': 1}
        b = {'a': 1, 'b': 2}
        self.assertEqual(calcular_hash_contenido(a), calcular_hash_contenido(b))
