"""Pruebas unitarias sin acceder a base de datos."""
from django.test import SimpleTestCase
from .services.permission_service import puede_administrar_supervisores

class CentralPermissionTests(SimpleTestCase):
    def test_anonymous_denied(self):
        class Anonymous:
            is_authenticated=False
        self.assertFalse(puede_administrar_supervisores(Anonymous()))

    def test_superuser_allowed(self):
        class Superuser:
            is_authenticated=True
            is_superuser=True
        self.assertTrue(puede_administrar_supervisores(Superuser()))
