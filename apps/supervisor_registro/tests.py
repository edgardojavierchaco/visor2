"""Pruebas de seguridad de alcance sin consultas a la base de datos."""
from types import SimpleNamespace
from unittest.mock import patch
from django.test import SimpleTestCase
from .services.permission_service import puede_ver_supervisores, get_regiones_usuario

class SeguridadAlcanceTests(SimpleTestCase):
    def usuario(self, role, *, authenticated=True, superuser=False):
        return SimpleNamespace(is_authenticated=authenticated, is_superuser=superuser,
                               nivelacceso=role)

    def test_anonimo_sin_acceso(self):
        u = self.usuario('funcionario', authenticated=False)
        self.assertFalse(puede_ver_supervisores(u))
        self.assertEqual(get_regiones_usuario(u), [])

    def test_rol_desconocido_no_obtiene_acceso_provincial(self):
        u = self.usuario('otro-rol')
        self.assertFalse(puede_ver_supervisores(u))
        self.assertEqual(get_regiones_usuario(u), [])

    def test_funcionario_solo_lectura_global(self):
        u = self.usuario('funcionario')
        self.assertTrue(puede_ver_supervisores(u))
        self.assertIsNone(get_regiones_usuario(u))

    def test_regional_sin_asignaciones_no_ve_informacion(self):
        u = self.usuario('regional')
        with patch('apps.supervisor_registro.services.permission_service.get_ids_regiones_responsable', return_value=[]):
            self.assertEqual(get_regiones_usuario(u), [])

    def test_refestadistica_usa_alcance_regional(self):
        u = self.usuario('refestadistica')
        with patch('apps.supervisor_registro.services.permission_service.get_ids_regiones_responsable', return_value=[2, 4]):
            self.assertTrue(puede_ver_supervisores(u))
            self.assertEqual(get_regiones_usuario(u), [2, 4])
