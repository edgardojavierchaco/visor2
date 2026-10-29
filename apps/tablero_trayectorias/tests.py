from unittest.mock import patch, MagicMock
from django.test import SimpleTestCase
from django.core.exceptions import PermissionDenied
from .access import resolve_scope

class AccesoTest(SimpleTestCase):
    def usuario(self, rol, categoria=''):
        u=MagicMock(); u.is_authenticated=True;u.is_active=True;u.is_superuser=False
        u.perfil.rol.nombre=rol;u.perfil.rol.categoria_acceso=categoria
        return u
    def test_provincial(self):
        for rol in ('Administrador','Ministro','Subsecretario','Director General'):
            self.assertEqual(resolve_scope(self.usuario(rol))['kind'],'all')
    def test_funcionario_no_es_provincial(self):
        with self.assertRaises(PermissionDenied):resolve_scope(self.usuario('Funcionario'))
    @patch('apps.bnhpersonas.domain.access.get_user_cueanexos',return_value=('220000200',))
    def test_director(self,_):
        self.assertEqual(resolve_scope(self.usuario('Director'))['cues'],['220000200'])
    @patch('apps.bnhpersonas.monitoring.access.supervisor_cueanexos',return_value=('220000400',))
    def test_supervisor(self,_):
        self.assertEqual(resolve_scope(self.usuario('Supervisor'))['cues'],['220000400'])
