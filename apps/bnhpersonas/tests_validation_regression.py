"""Pruebas de regresión para la validación de actividades existentes."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from .services.crud import _activity_form_data_from_instance


class ActivityFormDataRegressionTests(SimpleTestCase):
    def test_auxiliary_form_fields_are_reconstructed_without_model_get_field(self):
        concrete = [
            SimpleNamespace(name="cueanexo", attname="cueanexo"),
            SimpleNamespace(name="multiplan", attname="multiplan"),
            SimpleNamespace(name="titulacion", attname="titulacion"),
            SimpleNamespace(name="grado_anio", attname="grado_anio_id"),
            SimpleNamespace(name="secciones", attname="secciones_id"),
            SimpleNamespace(name="turno", attname="turno"),
        ]
        obj = SimpleNamespace(
            cueanexo="220000100",
            multiplan=True,
            titulacion=10,
            grado_anio_id=1,
            secciones_id=2,
            turno="MAÑANA",
            _meta=SimpleNamespace(concrete_fields=concrete),
        )

        titles_qs = MagicMock()
        titles_qs.order_by.return_value.values_list.return_value = [10, 11]
        obj.titulaciones_curriculares = titles_qs

        loc_qs = MagicMock()
        loc_qs.order_by.return_value.values.return_value = [
            {"grado_anio_id": 1, "seccion_id": 2, "turno": "MAÑANA"},
            {"grado_anio_id": 1, "seccion_id": 3, "turno": "TARDE"},
        ]
        obj.ubicaciones_curriculares = loc_qs

        fake_meta = [
            "cueanexo",
            "multiplan",
            "titulacion",
            "titulaciones_multiplan",
            "grado_anio",
            "turno",
            "secciones",
            "ubicaciones_json",
        ]

        with patch(
            "apps.bnhpersonas.forms.ActividadDirectorForm.Meta.fields",
            fake_meta,
        ):
            data = _activity_form_data_from_instance(obj)

        self.assertEqual(data["titulaciones_multiplan"], ["10", "11"])
        self.assertIn('"grado": 1', data["ubicaciones_json"])
        self.assertIn('"seccion": 3', data["ubicaciones_json"])
