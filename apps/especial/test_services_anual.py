from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from .services.previsualizacion_anual import prevalidar_generacion_anual


class PrevisualizacionAnualEspecialTests(SimpleTestCase):
    def test_cuenta_entidades_activas_sin_escrituras(self):
        ciclo = SimpleNamespace(pk=1, anio=2026, actual=True, cerrado=False)

        ciclo_manager = MagicMock()
        ciclo_manager.filter.return_value.exists.return_value = False

        def manager_with_count(value):
            manager = MagicMock()
            queryset = MagicMock()
            queryset.count.return_value = value
            manager.filter.return_value = queryset
            return manager

        with patch("apps.especial.services.previsualizacion_anual.EspecialCiclo.objects", ciclo_manager), patch(
            "apps.especial.services.previsualizacion_anual.SeccionEspecial.objects",
            manager_with_count(2),
        ), patch(
            "apps.especial.services.previsualizacion_anual.EspecialAlumnoBanco.objects",
            manager_with_count(3),
        ), patch(
            "apps.especial.services.previsualizacion_anual.EspecialDocenteBanco.objects",
            manager_with_count(1),
        ), patch(
            "apps.especial.services.previsualizacion_anual.AlumnoSeccion.objects",
            manager_with_count(4),
        ), patch(
            "apps.especial.services.previsualizacion_anual.DocenteSeccion.objects",
            manager_with_count(2),
        ):
            resultado = prevalidar_generacion_anual(ciclo, "123456789")

        self.assertEqual(resultado["secciones"], 2)
        self.assertEqual(resultado["alumnos"], 3)
        self.assertEqual(resultado["docentes"], 1)
        self.assertEqual(resultado["inscripciones"], 4)
        self.assertEqual(resultado["asignaciones"], 2)
        self.assertEqual(resultado["total_registros"], 12)
        self.assertFalse(resultado["errores"])
        self.assertFalse(resultado["bloqueado"])

