from django.test import TestCase

from apps.Dm.models import CanalMensaje, CanalUsuario, Canal
from django.contrib.auth import get_user_model

User=get_user_model()

class CanalTestCase(TestCase):
    def setUp(self):
        self.usuario_a=User.objects.create(username='jorgitocode',password='1234')
        self.usuario_b=User.objects.create(username='dosusuario',password='1234')
        self.usuario_c=User.objects.create(username='otrousuario',password='1234')

    def test_usuario_count(self):
        qs=User.objects.all()
        self.assertEqual(qs.count(),3)
        
    def test_cada_usuario_canal(self):
        qs=User.objects.all()
        
        for usuario in qs:
            canal_obj=Canal.objects.create()
            canal_obj.usuarios.add(usuario)
            
            canal_qs=Canal.objects.all()
            self.assertEqual(canal_qs.count(),3)
            
            canal_qs1=canal_qs.solo_uno()
            self.assertEqual(canal_qs1.count(),canal_qs.count())